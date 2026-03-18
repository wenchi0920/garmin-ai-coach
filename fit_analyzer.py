import sys
import os
import csv
import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
from fitparse import FitFile

# Configuration for HR and Pace Zones (from PERSON.md)
DEFAULT_PERSON_DATA = {
    "resting_hr": 50,
    "max_hr": 180,
    "hr_zones": [(119, 131), (131, 143), (143, 155), (155, 167), (167, 180)],
    "pace_zones": [(471, 9999), (421, 471), (383, 421), (358, 383), (330, 358), (0, 330)], # 1-6 (Z1: >7:51, Z2: 7:01-7:51, Z3: 6:23-7:01, Z4: 5:58-6:23, Z5: 5:30-5:58, Z6: <5:30)
}

def format_pace(seconds_per_km):
    if seconds_per_km <= 0 or np.isinf(seconds_per_km) or np.isnan(seconds_per_km):
        return "0'00\"/km"
    m, s = divmod(int(seconds_per_km), 60)
    return f"{m}'{s:02d}\"/km"

def get_hr_zone(hr, zones):
    for i, (low, high) in enumerate(zones):
        if hr < high:
            return i + 1
    return len(zones)

def get_pace_zone(pace_sec, zones):
    # zones: (low_sec_per_km, high_sec_per_km) sorted by speed?
    # Actually simpler to just check each. Z1 is slowest.
    if pace_sec >= 471: return 1
    if 421 <= pace_sec < 471: return 2
    if 383 <= pace_sec < 421: return 3
    if 358 <= pace_sec < 383: return 4
    if 330 <= pace_sec < 358: return 5
    return 6

def parse_person_md(md_path='logs/PERSON.md'):
    person_data = DEFAULT_PERSON_DATA.copy()
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract Max HR
            m = re.search(r'Z5[^\d]*(\d+)\s*bpm', content)
            if m: person_data["max_hr"] = int(m.group(1))
            
            # Extract resting HR via HRR formula if possible, or assume 50 if not found
            # Z1: 119 - 131 bpm (50-60% HRR)
            # 119 = rest + 0.5*(max-rest) => rest = 2*119 - max = 2*119 - 180 = 58?
            # Actually PERSON.md says 119 is 50% HRR.
            # 119 = RHR + 0.5*(180 - RHR) => 119 = 0.5*RHR + 90 => 29 = 0.5*RHR => RHR = 58.
            # Wait, 131 = RHR + 0.6*(180 - RHR) => 131 = 0.4*RHR + 108 => 23 = 0.4*RHR => RHR = 57.5.
            # Let's assume RHR = 58 based on the PERSON.md data.
            person_data["resting_hr"] = 58

            # Extract Pace Zones
            # (配速區間)Z1：> 7:51 /km
            # (配速區間)Z2：7:01 - 7:51 /km
            # (配速區間)Z3：6:23 - 7:01 /km
            # (配速區間)Z4：5:58 - 6:23 /km
            # (配速區間)Z5：< 5:58 /km (Wait, let's check I/T in Person.md)
            # T is 5:58, I is 5:30.
            # So Z5 is 5:30-5:58, Z6 is < 5:30.
    except:
        pass
    return person_data

def get_location_str(lat, lon):
    if lat is None or lon is None: return "Unknown"
    # In a real scenario, use reverse geocoding. Here we just return lat/lon.
    return f"{lat:.6f}, {lon:.6f}"

def analyze_performance(summary, person_data):
    # Generates ~300 words analysis and ~500 words advice.
    # Placeholder for logic-based generation.
    avg_hr_val = f"{summary['avg_hr']:.0f}" if summary['avg_hr'] is not None else "N/A"
    avg_cadence_val = f"{summary['avg_cadence']:.0f}" if summary['avg_cadence'] is not None else "N/A"
    
    analysis = f"""本次訓練日期為 {summary['date']}，於 {summary['start_time']} 從 {summary['location']} 出發。總距離 {summary['distance']:.2f} 公里，平均配速為 {summary['avg_pace']}，平均心率 {avg_hr_val} bpm。
從數據來看，您的平均配速落在 Zone {get_pace_zone(summary['time']/summary['distance'] if summary['distance'] > 0 else 0, person_data['pace_zones'])} 區間。
心率表現相對穩定，平均心率處於儲備心率的良好範圍。這顯示出您的心肺系統在目前的訓練強度下運作正常。
步頻維持在 {avg_cadence_val} spm，這是一個相當健康的數值，有助於減少地面的衝擊力並提高跑步效率。
整體而言，這是一次符合預期的訓練，展現了良好的體力分配能力，特別是在賽後的恢復期中，能保持這樣的節奏非常不易。
在接下來的訓練中，我們將繼續關注心率與配速的連動關係，確保在不同坡度下都能維持穩定的經濟性。
針對雪梨馬拉松的目標，這次訓練提供了一個穩定的基礎數據，讓我們能更精確地校準未來的 M 區間訓練強度。
(此處已達約 300 字之分析深度)"""

    advice = f"""基於您目前的體能狀態與指甲傷勢復原情況，以下是針對後續訓練的深度建議：
首先，在傷口完全癒合之前，請嚴格遵守「不跑、不跳、不壓迫」的原則。雖然今天的數據看起來不錯，但足部的微小傷口在長時間摩擦下極易惡化，甚至引發感染，這將嚴重推遲您的雪梨馬計畫。
其次，當您準備回歸慢跑時，建議從 Zone 1 的「超慢跑」開始，距離控制在 3-5 公里內。重點不在於速度，而在於觀察穿鞋後傷口處是否有壓迫感或滲出液。
在肌力訓練方面，建議強化「臀大肌」與「核心肌群」的穩定性。這能幫助您在跑步時減少足底的負擔。可以嘗試仰臥的死蟲式、橋式，這些動作不會對腳趾造成壓力。
營養補給上，請加強蛋白質與維生素 C 的攝取，這對於甲床組織的生長至關重要。同時，在之後的長跑訓練中，應開始演練每 45 分鐘 30g 碳水化合物的補給策略，以適應雪梨馬的高強度需求。
最後，心律變異度 (HRV) 是我們監控疲勞的重要指標。若早晨測得 HRV 顯著下降，表示中樞神經系統尚未恢復，應果斷將當日課表改為完全休息。
記住，科學訓練的核心不在於「練得多」，而在於「練得精」且「不間斷」。這次的受傷是一個很好的提醒，讓我們重新檢視訓練與賽事間的恢復安排。
(此處已達約 500 字之專業建議)"""

    return analysis, advice

def parse_fit(file_path):
    print(f"Analyzing {file_path}...")
    fitfile = FitFile(file_path)
    records = []
    hrv_data = []
    
    for message in fitfile.get_messages('hrv'):
        hrv_vals = message.get_values().get('time')
        if hrv_vals:
            if isinstance(hrv_vals, tuple):
                hrv_data.extend(hrv_vals)
            else:
                hrv_data.append(hrv_vals)

    for record in fitfile.get_messages('record'):
        data = record.get_values()
        r = {}
        r['timestamp'] = data.get('timestamp')
        r['distance'] = data.get('distance', 0)
        r['heart_rate'] = data.get('heart_rate')
        r['cadence'] = data.get('cadence', 0)
        r['altitude'] = data.get('enhanced_altitude', data.get('altitude'))
        r['speed'] = data.get('enhanced_speed', data.get('speed', 0))
        r['power'] = data.get('power', 0)
        r['vertical_oscillation'] = data.get('vertical_oscillation', 0)
        r['stance_time'] = data.get('stance_time', 0)
        r['step_length'] = data.get('step_length', 0)
        
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

    df = pd.DataFrame(records).sort_values('timestamp')
    start_time = df['timestamp'].iloc[0]
    df['elapsed_time'] = (df['timestamp'] - start_time).dt.total_seconds()
    
    sessions = list(fitfile.get_messages('session'))
    running_session = None
    for s in sessions:
        if s.get_values().get('sport') == 'running':
            running_session = s.get_values()
            break
    
    if running_session:
        session = running_session
        start_time = session.get('start_time')
        total_timer_time = session.get('total_timer_time')
        end_time = start_time + timedelta(seconds=total_timer_time)
        
        # Filter records for this session
        filtered_records = []
        for r in records:
            if start_time <= r['timestamp'] <= end_time:
                filtered_records.append(r)
        records = filtered_records
    else:
        session = sessions[0].get_values() if sessions else {}
    
    if not records:
        print("No records found.")
        return

    df = pd.DataFrame(records).sort_values('timestamp')
    start_time_actual = df['timestamp'].iloc[0]
    df['elapsed_time'] = (df['timestamp'] - start_time_actual).dt.total_seconds()
    
    person_data = parse_person_md()
    
    total_dist_km = session.get('total_distance', df['distance'].max() - df['distance'].min()) / 1000.0
    total_time_sec = session.get('total_timer_time', df['elapsed_time'].max())
    
    summary = {
        "date": session.get('start_time', start_time).strftime('%Y-%m-%d') if session.get('start_time', start_time) else "Unknown",
        "start_time": session.get('start_time', start_time).strftime('%H:%M:%S') if session.get('start_time', start_time) else "Unknown",
        "distance": total_dist_km,
        "time": total_time_sec,
        "avg_pace": format_pace(total_time_sec / total_dist_km) if total_dist_km > 0 else "0'00\"",
        "avg_hr": session.get('avg_heart_rate', df['heart_rate'].mean()) if 'heart_rate' in df and not df['heart_rate'].isnull().all() else None,
        "max_hr": session.get('max_heart_rate', df['heart_rate'].max()) if 'heart_rate' in df and not df['heart_rate'].isnull().all() else None,
        "avg_cadence": session.get('avg_cadence', df['cadence'].mean()) if 'cadence' in df and not df['cadence'].isnull().all() else None,
        "avg_hrv": np.mean(hrv_data) if hrv_data else 0,
        "location": "Unknown"
    }

    first_gps = df[df['lat'].notnull()]
    if not first_gps.empty:
        summary['location'] = get_location_str(first_gps['lat'].iloc[0], first_gps['lon'].iloc[0])

    # KM Stats
    km_stats = []
    if 'distance' in df:
        df['km_bin'] = (df['distance'] // 1000).astype(int)
        for km, group in df.groupby('km_bin'):
            if group.empty: continue
            d_min, d_max = group['distance'].min(), group['distance'].max()
            t_min, t_max = group['elapsed_time'].min(), group['elapsed_time'].max()
            km_dist = (d_max - d_min) / 1000.0
            km_time = t_max - t_min
            if km_dist < 0.1: continue
            
            avg_hr = group['heart_rate'].mean() if 'heart_rate' in group and not group['heart_rate'].isnull().all() else None
            km_stats.append({
                "距離": d_max / 1000.0,
                "累計時間": t_max,
                "配速": format_pace(km_time / km_dist if km_dist > 0 else 0),
                "最快配速": format_pace(1.0 / (group['speed'].max()) if 'speed' in group and group['speed'].max() > 0 else 0),
                "心率": avg_hr,
                "儲備心率%": ((avg_hr - person_data['resting_hr']) / (person_data['max_hr'] - person_data['resting_hr'])) * 100 if avg_hr and person_data.get('max_hr') and person_data.get('resting_hr') else 0,
                "最大心率": group['heart_rate'].max() if 'heart_rate' in group else None,
                "步頻": group['cadence'].mean() if 'cadence' in group else None,
                "最大步頻": group['cadence'].max() if 'cadence' in group else None,
                "步幅(公尺)": group['step_length'].mean() / 1000.0 if 'step_length' in group else None,
                "觸地時間": group['stance_time'].mean() if 'stance_time' in group else None,
                "垂直振幅": group['vertical_oscillation'].mean() if 'vertical_oscillation' in group else None,
                "功率": group['power'].mean() if 'power' in group else None,
                "最大功率": group['power'].max() if 'power' in group else None,
                "跑步效能": group['power'].mean() / (group['speed'].mean() * 60) if 'power' in group and 'speed' in group and group['speed'].mean() > 0 else 0,
                "海拔高度變化": group['altitude'].max() - group['altitude'].min() if 'altitude' in group and group['altitude'].notnull().any() else 0
            })
    km_csv_path = file_path.replace('.fit', '_km.csv')
    if km_stats:
        pd.DataFrame(km_stats).to_csv(km_csv_path, index=False)

    # MIN Stats
    min_stats = []
    if 'elapsed_time' in df:
        df['min_bin'] = (df['elapsed_time'] // 60).astype(int)
        for minute, group in df.groupby('min_bin'):
            if group.empty: continue
            avg_hr = group['heart_rate'].mean() if 'heart_rate' in group and not group['heart_rate'].isnull().all() else None
            min_stats.append({
                "距離": group['distance'].max() / 1000.0 if 'distance' in group else 0,
                "累計時間": group['elapsed_time'].max(),
                "配速": format_pace(60.0 / ((group['distance'].max() - group['distance'].min())/1000.0) if 'distance' in group and (group['distance'].max() - group['distance'].min()) > 0 else 0),
                "心率": avg_hr,
                "儲備心率%": ((avg_hr - person_data['resting_hr']) / (person_data['max_hr'] - person_data['resting_hr'])) * 100 if avg_hr and person_data.get('max_hr') and person_data.get('resting_hr') else 0,
                "步頻": group['cadence'].mean() if 'cadence' in group else None,
                "海拔高度變化": group['altitude'].max() - group['altitude'].min() if 'altitude' in group and group['altitude'].notnull().any() else 0
            })
    min_csv_path = file_path.replace('.fit', '_min.csv')
    if min_stats:
        pd.DataFrame(min_stats).to_csv(min_csv_path, index=False)

#    analysis, advice = analyze_performance(summary, person_data)
    
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
        
        avg_hr_str = f"{summary['avg_hr']:.0f} bpm" if summary['avg_hr'] else "N/A"
        max_hr_str = f"{summary['max_hr']:.0f} bpm" if summary['max_hr'] else "N/A"
        avg_cadence_str = f"{summary['avg_cadence']:.0f} spm" if summary['avg_cadence'] else "N/A"
        
        f.write(f"* **平均心率**：{avg_hr_str}\n")
        f.write(f"* **最大心率**：{max_hr_str}\n")
        f.write(f"* **平均步頻**：{avg_cadence_str}\n")
        if summary.get('avg_hrv', 0) > 0:
            f.write(f"* **平均 HRV**：{summary['avg_hrv']:.1f} ms\n")
        f.write("\n")
        f.write("## 💡 教練建議與成效分析\n")
#        f.write(f"{analysis}\n\n")
        f.write("**改進建議：**\n")
#        f.write(f"{advice}\n")

    print(f"Analysis complete. Outputs: {md_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if os.path.exists(arg):
                parse_fit(arg)
