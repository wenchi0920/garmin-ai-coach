import sys
import os
import csv
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from fitparse import FitFile

def get_location_str(lat, lon):
    if lat is None or lon is None:
        return "Unknown"
    return f"{lat:.6f}, {lon:.6f}"

def format_pace(seconds_per_km):
    if seconds_per_km <= 0 or np.isinf(seconds_per_km) or np.isnan(seconds_per_km):
        return "0'00\"/km"
    m, s = divmod(int(seconds_per_km), 60)
    return f"{m}'{s:02d}\"/km"

def parse_person_md():
    person_data = {
        "z2_pace": (421, 471), # 7:01-7:51 in seconds
        "z3_pace": (383, 421), # 6:23-7:01
        "max_hr": 180
    }
    try:
        with open('PERSON.md', 'r', encoding='utf-8') as f:
            content = f.read()
            # Simplistic parsing
            if "7:01 - 7:51" in content:
                person_data["z2_pace"] = (421, 471)
            if "6:23 - 7:01" in content:
                person_data["z3_pace"] = (383, 421)
    except:
        pass
    return person_data

def analyze_performance(summary, person_data):
    pace_sec = summary['time'] / summary['distance'] if summary['distance'] > 0 else 0
    advice = ""
    if person_data['z2_pace'][0] <= pace_sec <= person_data['z2_pace'][1]:
        advice = "這次訓練配速完美落在 E/Zone 2 區間，這對於建立您的馬拉松基礎耐力非常有幫助。您的心率控制也相當穩定。"
    elif pace_sec < person_data['z2_pace'][0]:
        advice = "配速稍微超出了 E 區間。如果您今天的目的是輕鬆跑，建議稍放慢腳步，以確保肌肉能充分修補並維持低心率訓練的效果。"
    else:
        advice = "今天的配速較慢。這可能是因為身體疲勞或恢復跑的性質。請注意步頻是否能維持在 175+ spm 以上，以保持跑步經濟性。"
    
    recom = "建議在接下來的長跑日中，嘗試將目標配速維持在 6:23/km (M 區間) 演練 20 分鐘以上。同時，注意補給演練，以應對雪梨馬賽道前半段的起伏。若感到心率異常偏高，請立即降階為輕鬆跑。"
    return advice, recom

def parse_fit(file_path):
    print(f"Analyzing {file_path}...")
    fitfile = FitFile(file_path)
    records = []
    
    for record in fitfile.get_messages('record'):
        data = record.get_values()
        r = {}
        r['timestamp'] = data.get('timestamp')
        r['distance'] = data.get('distance', 0)
        r['timer_time'] = data.get('timestamp') # Will calc later
        r['heart_rate'] = data.get('heart_rate')
        r['cadence'] = data.get('cadence', 0)
        r['altitude'] = data.get('enhanced_altitude', data.get('altitude'))
        r['speed'] = data.get('enhanced_speed', data.get('speed', 0)) # m/s
        r['power'] = data.get('power', 0)
        r['vertical_oscillation'] = data.get('vertical_oscillation', 0)
        r['stance_time'] = data.get('stance_time', 0)
        r['step_length'] = data.get('step_length', 0)
        
        # GPS
        lat = data.get('position_lat')
        lon = data.get('position_long')
        if lat is not None and lon is not None:
            r['lat'] = lat * (180.0 / 2**31)
            r['lon'] = lon * (180.0 / 2**31)
        else:
            r['lat'] = None
            r['lon'] = None
            
        records.append(r)

    if not records:
        print("No records found.")
        return

    df = pd.DataFrame(records)
    df = df.sort_values('timestamp')
    
    # Calculate elapsed time from first record
    start_time = df['timestamp'].iloc[0]
    df['elapsed_time'] = (df['timestamp'] - start_time).dt.total_seconds()
    
    # Get session summary
    sessions = list(fitfile.get_messages('session'))
    session = sessions[0].get_values() if sessions else {}
    
    total_dist_km = session.get('total_distance', df['distance'].max()) / 1000.0
    total_time_sec = session.get('total_timer_time', df['elapsed_time'].max())
    
    summary = {
        "date": session.get('start_time', start_time).strftime('%Y-%m-%d'),
        "start_time": session.get('start_time', start_time).strftime('%H:%M:%S'),
        "distance": total_dist_km,
        "time": total_time_sec,
        "avg_pace": format_pace(total_time_sec / total_dist_km) if total_dist_km > 0 else "0'00\"",
        "avg_hr": session.get('avg_heart_rate', df['heart_rate'].mean()),
        "max_hr": session.get('max_heart_rate', df['heart_rate'].max()),
        "avg_cadence": session.get('avg_cadence', df['cadence'].mean()),
        "location": "Unknown"
    }

    # Location from first non-None record
    first_gps = df[df['lat'].notnull()]
    if not first_gps.empty:
        summary['location'] = get_location_str(first_gps['lat'].iloc[0], first_gps['lon'].iloc[0])

    # KM Stats
    km_stats = []
    df['km_bin'] = (df['distance'] // 1000).astype(int)
    for km, group in df.groupby('km_bin'):
        if group.empty: continue
        km_dist = group['distance'].max() / 1000.0
        km_time = group['elapsed_time'].max() - group['elapsed_time'].min()
        if km_time == 0: continue
        
        km_stats.append({
            "距離": km_dist,
            "累計時間": group['elapsed_time'].max(),
            "配速": format_pace(km_time / ( (group['distance'].max() - group['distance'].min())/1000.0 ) if group['distance'].max() > group['distance'].min() else 0),
            "最快配速": format_pace(1.0 / (group['speed'].max() * 3.6 / 3.6 / 1000.0 * 3600) if group['speed'].max() > 0 else 0),
            "心率": group['heart_rate'].mean(),
            "儲備心率%": ((group['heart_rate'].mean() - 50) / (180-50)) * 100 if group['heart_rate'].mean() else 0, # Placeholder
            "最大心率": group['heart_rate'].max(),
            "步頻": group['cadence'].mean(),
            "最大步頻": group['cadence'].max(),
            "步幅(公尺)": group['step_length'].mean() / 1000.0 if 'step_length' in group else 0,
            "觸地時間": group['stance_time'].mean(),
            "垂直振幅": group['vertical_oscillation'].mean(),
            "功率": group['power'].mean(),
            "最大功率": group['power'].max(),
            "跑步效能": 0, # Needs specific formula
            "海拔高度變化": group['altitude'].max() - group['altitude'].min() if group['altitude'].notnull().any() else 0
        })
    
    km_csv_path = file_path.replace('.fit', '_km.csv')
    pd.DataFrame(km_stats).to_csv(km_csv_path, index=False)

    # MIN Stats
    min_stats = []
    df['min_bin'] = (df['elapsed_time'] // 60).astype(int)
    for minute, group in df.groupby('min_bin'):
        if group.empty: continue
        min_stats.append({
            "距離": group['distance'].max() / 1000.0,
            "累計時間": group['elapsed_time'].max(),
            "心率": group['heart_rate'].mean(),
            "步頻": group['cadence'].mean(),
            "海拔高度變化": group['altitude'].max() - group['altitude'].min() if group['altitude'].notnull().any() else 0
        })
    min_csv_path = file_path.replace('.fit', '_min.csv')
    pd.DataFrame(min_stats).to_csv(min_csv_path, index=False)

    # MD Report
    person_data = parse_person_md()
    advice, recom = analyze_performance(summary, person_data)
    
    md_path = file_path.replace('.fit', '.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# 訓練分析報告: {summary['date']}-{summary['start_time'].replace(':','-')}\n\n")
        f.write("## 📊 核心數據\n")
        f.write(f"* **日期**：{summary['date']}\n")
        f.write(f"* **起跑時間**：{summary['start_time']}\n")
        f.write(f"* **起跑地點**：{summary['location']}\n")
        f.write(f"* **距離**：{summary['distance']:.2f} km\n")
        f.write(f"* **時間**：{int(summary['time'] // 3600):02d}:{int((summary['time'] % 3600) // 60):02d}:{int(summary['time'] % 60):02d}\n")
        f.write(f"* **平均配速**：{summary['avg_pace']}\n")
        f.write(f"* **平均心率**：{summary['avg_hr']:.0f} bpm\n")
        f.write(f"* **最大心率**：{summary['max_hr']:.0f} bpm\n")
        f.write(f"* **平均步頻**：{summary['avg_cadence']:.0f} spm\n\n")
        f.write("## 💡 教練建議與成效分析\n")
        f.write(f"{advice}\n\n")
        f.write("**改進建議：**\n")
        f.write(f"{recom}\n")

    print(f"Analysis complete. Outputs: {md_path}, {km_csv_path}, {min_csv_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        parse_fit(sys.argv[1])
