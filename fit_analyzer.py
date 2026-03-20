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
    "pace_zones": [(471, 9999), (421, 471), (383, 421), (358, 383), (330, 358), (0, 330)],
}

def format_pace(seconds_per_km):
    if seconds_per_km <= 0 or np.isinf(seconds_per_km) or np.isnan(seconds_per_km):
        return ""
    m, s = divmod(int(seconds_per_km), 60)
    return f"{m}'{s:02d}\"/km"

def parse_person_md(md_path='logs/PERSON.md'):
    person_data = DEFAULT_PERSON_DATA.copy()
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            m = re.search(r'Z5[^\d]*(\d+)\s*bpm', content)
            if m: person_data["max_hr"] = int(m.group(1))
            person_data["resting_hr"] = 58
    except:
        pass
    return person_data

def get_location_str(lat, lon):
    if lat is None or lon is None: return ""
    return f"{lat:.6f}, {lon:.6f}"

def parse_fit(file_path):
    if not file_path.lower().endswith('.fit'):
        print(f"Error: {file_path} is not a .fit file.")
        return

    print(f"Analyzing {file_path}...")
    try:
        fitfile = FitFile(file_path)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return
    
    person_data = parse_person_md()
    records = []
    hrv_data = []
    laps_data = []
    
    # Extract HRV
    for message in fitfile.get_messages('hrv'):
        hrv_vals = message.get_values().get('time')
        if hrv_vals:
            if isinstance(hrv_vals, tuple): hrv_data.extend(hrv_vals)
            else: hrv_data.append(hrv_vals)

    # Extract Laps with full metrics
    for i, lap in enumerate(fitfile.get_messages('lap')):
        data = lap.get_values()
        
        lap_dist = data.get('total_distance', 0) / 1000.0
        lap_time = data.get('total_timer_time', 0)
        avg_speed = data.get('avg_speed')
        max_speed = data.get('max_speed')
        avg_hr = data.get('avg_heart_rate')
        avg_power = data.get('avg_power')
        
        hrr_pct = ''
        if avg_hr and person_data['max_hr'] and person_data['resting_hr']:
            hrr_pct = f"{((avg_hr - person_data['resting_hr']) / (person_data['max_hr'] - person_data['resting_hr'])) * 100:.1f}%"
        
        efficiency = ''
        if avg_power is not None and avg_speed and avg_speed > 0:
            efficiency = f"{avg_power / (avg_speed * 60):.2f}"
            
        laps_data.append({
            "分段": i + 1,
            "距離": f"{lap_dist:.2f}",
            "累計時間": f"{int(lap_time // 3600):02d}:{int((lap_time % 3600) // 60):02d}:{int(lap_time % 60):02d}",
            "配速": format_pace(1.0 / avg_speed if avg_speed and avg_speed > 0 else 0),
            "最快配速": format_pace(1.0 / max_speed if max_speed and max_speed > 0 else 0),
            "心率": f"{avg_hr:.0f}" if avg_hr else '',
            "儲備心率%": hrr_pct,
            "最大心率": f"{data.get('max_heart_rate'):.0f}" if data.get('max_heart_rate') else '',
            "步頻": f"{data.get('avg_cadence'):.0f}" if data.get('avg_cadence') else '',
            "最大步頻": f"{data.get('max_cadence'):.0f}" if data.get('max_cadence') else '',
            "步幅(公尺)": f"{data.get('avg_step_length') / 1000.0:.2f}" if data.get('avg_step_length') else '',
            "觸地時間": f"{data.get('avg_stance_time'):.1f}" if data.get('avg_stance_time') else '',
            "垂直振幅": f"{data.get('avg_vertical_oscillation'):.1f}" if data.get('avg_vertical_oscillation') else '',
            "功率": f"{avg_power:.0f}" if avg_power is not None else '',
            "最大功率": f"{data.get('max_power'):.0f}" if data.get('max_power') else '',
            "跑步效能": efficiency,
            "海拔高度變化": f"{data.get('total_ascent', 0) - data.get('total_descent', 0):.0f}" if data.get('total_ascent') is not None else ''
        })

    # Extract Records for Summary
    for record in fitfile.get_messages('record'):
        data = record.get_values()
        r = {k: data.get(k) for k in ['timestamp', 'distance', 'heart_rate', 'cadence', 'speed']}
        lat, lon = data.get('position_lat'), data.get('position_long')
        if lat is not None and lon is not None:
            r['lat'], r['lon'] = lat * (180.0 / 2**31), lon * (180.0 / 2**31)
        else: r['lat'] = r['lon'] = None
        records.append(r)

    if not records: return
    df = pd.DataFrame(records).sort_values('timestamp')
    
    # Session handling
    sessions = list(fitfile.get_messages('session'))
    session = next((s.get_values() for s in sessions if s.get_values().get('sport') == 'running'), sessions[0].get_values() if sessions else {})
    
    summary = {
        "date": session.get('start_time', df['timestamp'].iloc[0]).strftime('%Y-%m-%d'),
        "start_time": session.get('start_time', df['timestamp'].iloc[0]).strftime('%H:%M:%S'),
        "distance": session.get('total_distance', 0) / 1000.0,
        "time": session.get('total_timer_time', 0),
        "avg_pace": format_pace(session.get('total_timer_time', 0) / (session.get('total_distance', 1) / 1000.0)),
        "avg_hr": session.get('avg_heart_rate', df['heart_rate'].mean()),
        "max_hr": session.get('max_heart_rate', df['heart_rate'].max()),
        "avg_cadence": session.get('avg_cadence', df['cadence'].mean()),
        "avg_hrv": np.mean(hrv_data) if hrv_data else 0,
        "location": get_location_str(df['lat'].dropna().iloc[0], df['lon'].dropna().iloc[0]) if df['lat'].notnull().any() else ""
    }

    # Save Laps CSV
    if laps_data:
        pd.DataFrame(laps_data).to_csv(file_path.replace('.fit', '_laps.csv'), index=False, encoding='utf-8-sig')

    # Write MD Report
    md_path = file_path.replace('.fit', '.md')
    avg_hr_str = f"{summary['avg_hr']:.0f} bpm" if summary['avg_hr'] else ""
    max_hr_str = f"{summary['max_hr']:.0f} bpm" if summary['max_hr'] else ""
    cad_str = f"{summary['avg_cadence']:.0f} spm" if summary['avg_cadence'] else ""

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# 訓練分析報告: {summary['date']}-{summary['start_time'].replace(':','-')}\n\n")
        f.write("## 📊 核心數據\n")
        f.write(f"* **日期**：{summary['date']}\n* **起跑時間**：{summary['start_time']}\n* **起跑地點**：{summary['location']}\n")
        f.write(f"* **距離**：{summary['distance']:.2f} km\n* **時間**：{int(summary['time'] // 3600):02d}:{int((summary['time'] % 3600) // 60):02d}:{int(summary['time'] % 60):02d}\n")
        f.write(f"* **平均配速**：{summary['avg_pace']}\n")
        f.write(f"* **平均心率**：{avg_hr_str}\n")
        f.write(f"* **最大心率**：{max_hr_str}\n")
        f.write(f"* **平均步頻**：{cad_str}\n")
        if summary['avg_hrv'] > 0: f.write(f"* **平均 HRV**：{summary['avg_hrv']:.1f} ms\n")
        
        if laps_data:
            f.write("\n## ⏱️ 分段紀錄 (Laps)\n")
            f.write("| 分段 | 距離 | 累計時間 | 配速 | 最快配速 | 心率 | 儲備心率% | 最大心率 | 步頻 | 最大步頻 | 步幅 | 觸地時間 | 垂直振幅 | 功率 | 最大功率 | 效能 | 海拔變化 |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for l in laps_data:
                f.write(f"| {l['分段']} | {l['距離']} | {l['累計時間']} | {l['配速']} | {l['最快配速']} | {l['心率']} | {l['儲備心率%']} | {l['最大心率']} | {l['步頻']} | {l['最大步頻']} | {l['步幅(公尺)']} | {l['觸地時間']} | {l['垂直振幅']} | {l['功率']} | {l['最大功率']} | {l['跑步效能']} | {l['海拔高度變化']} |\n")

        f.write("\n## 💡 教練建議與成效分析(事後分析)\n")
        f.write("(提供 300 字 內文分析)\n\n")
        f.write("**改進建議：**\n")
        f.write("(提供 500 字 內文分析)\n")

    print(f"Analysis complete. Outputs: {md_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if os.path.exists(arg): parse_fit(arg)
