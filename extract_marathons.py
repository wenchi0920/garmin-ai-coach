#!/usr/bin/env python3
import os
import sys
import argparse
import re
from datetime import datetime, timedelta
import fitparse

# Purpose: Extract Marathons/Half Marathons from FIT files and update SCHEDULE.md
# Columns: 日期 / 賽事 / 類別 / 距離 / 完賽時間 / 平均配速 / 平均心率 / 平均步頻 / 原始檔案

def format_duration(seconds):
    if not seconds: return "--:--:--"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def format_pace(seconds_per_km):
    if not seconds_per_km: return "--:--"
    m = int(seconds_per_km // 60)
    s = int(seconds_per_km % 60)
    return f"{m}:{s:02d}"

def get_race_name(date_str, lat, lon):
    # Mapping of known races based on date or location
    # This can be expanded as more races are identified
    races = {
        "20231022": "長榮航空城市觀光馬拉松",
        "20240225": "渣打臺北公益馬拉松",
        "20240309": "棲蘭林道越野",
        "20241201": "那霸馬拉松 (DNF)",
        "20250112": "鎮西堡超級馬拉松",
        "20250224": "大阪馬拉松",
        "20260301": "自主半馬測試"
    }
    
    key = date_str[:8]
    if key in races:
        return races[key]
    
    # Heuristic based on location if needed
    # (e.g., if lat/lon matches a specific city)
    
    return "個人自主訓練"

def process_fit(file_path):
    try:
        fitfile = fitparse.FitFile(file_path)
    except Exception as e:
        return None

    session_data = {}
    for m in fitfile.get_messages('session'):
        session_data = m.get_values()
        break
    
    if not session_data:
        return None
    
    distance_m = session_data.get('total_distance') or 0
    distance_km = distance_m / 1000.0
    
    if distance_km < 21.0:
        return None
    
    # Determine category
    if distance_km >= 50.0:
        category = "超馬"
    elif distance_km >= 42.0:
        category = "全馬"
    else:
        category = "半馬"
        
    # Extract date
    start_time = session_data.get('start_time')
    date_str = start_time.strftime("%Y-%m-%d") if start_time else "未知"
    file_date = os.path.basename(file_path)[:8]
    
    # Duration
    duration_s = session_data.get('total_timer_time') or 0
    duration_str = format_duration(duration_s)
    
    # Pace
    avg_speed = session_data.get('enhanced_avg_speed') or session_data.get('avg_speed') or 0
    if avg_speed == 0 and distance_m > 0 and duration_s > 0:
        avg_speed = distance_m / duration_s
        
    pace_s = 1000 / avg_speed if avg_speed > 0 else 0
    pace_str = format_pace(pace_s)
    
    # HR / Cadence
    avg_hr = session_data.get('avg_heart_rate') or "--"
    avg_cadence = (session_data.get('avg_running_cadence') or 0) * 2 or "--"
    
    # GPS (for race naming)
    lat = session_data.get('start_position_lat')
    lon = session_data.get('start_position_long')
    
    race_name = get_race_name(file_date, lat, lon)
    
    return {
        'date': date_str,
        'race': race_name,
        'category': category,
        'distance': f"{distance_km:.2f} km",
        'time': duration_str,
        'pace': f"{pace_str}/km",
        'hr': f"{avg_hr} bpm",
        'cadence': f"{avg_cadence} spm",
        'file': os.path.basename(file_path)
    }

def main():
    parser = argparse.ArgumentParser(description='Extract marathons and half marathons.')
    parser.add_argument('path', help='Path to folder or .fit file')
    args = parser.parse_args()
    
    results = []
    
    if os.path.isdir(args.path):
        for f in sorted(os.listdir(args.path)):
            if f.endswith('.fit'):
                res = process_fit(os.path.join(args.path, f))
                if res:
                    results.append(res)
    elif os.path.isfile(args.path):
        res = process_fit(args.path)
        if res:
            results.append(res)
            
    if not results:
        print("No marathons or half marathons found.")
        return

    # Sort results by date descending
    results.sort(key=lambda x: x['date'], reverse=True)

    header = "# 🏃‍♂️ 賽事與長跑紀錄 (SCHEDULE.md)\n\n"
    table_header = "| 日期 | 賽事 | 類別 | 距離 | 完賽時間 | 平均配速 | 平均心率 | 平均步頻 | 原始檔案 |\n"
    table_sep = "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    
    with open("SCHEDULE.md", "w") as f:
        f.write(header)
        f.write(table_header)
        f.write(table_sep)
        for r in results:
            line = f"| {r['date']} | {r['race']} | {r['category']} | {r['distance']} | {r['time']} | {r['pace']} | {r['hr']} | {r['cadence']} | {r['file']} |\n"
            f.write(line)
    
    print(f"Successfully generated SCHEDULE.md with {len(results)} records.")

if __name__ == "__main__":
    main()
