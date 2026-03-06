#!/usr/bin/env python3
import os
import sys
import argparse
import csv
import math
import re
from datetime import datetime, timedelta
import fitparse

# Purpose: Analyze FIT files and generate per-km/per-min CSVs and summary MDs.
# Mandatory indicators for GEMINI.md:
# distance, duration, pace, max pace, hr, hrr%, max hr, cadence, max cadence, 
# stride length, gct, vertical oscillation, power, max power, RE, altitude change.

def get_pace(m_per_s):
    if m_per_s <= 0:
        return 0
    pace_s_per_km = 1000 / m_per_s
    return pace_s_per_km

def format_pace(s_per_km):
    if s_per_km <= 0 or s_per_km > 3600:
        return "--:--"
    m = int(s_per_km // 60)
    s = int(s_per_km % 60)
    return f"{m}:{s:02d}"

def generate_md(file_path, session_data):
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    with open(f"{base_name}.md", 'w') as f:
        f.write(f"# 訓練分析報告: {base_name}\n\n")
        f.write("## 📊 核心數據\n")
        f.write(f"* **距離**：{(session_data.get('total_distance') or 0)/1000:.2f} km\n")
        duration = session_data.get('total_timer_time') or 0
        f.write(f"* **時間**：{int(duration//3600):02d}:{int((duration%3600)//60):02d}:{int(duration%60):02d}\n")
        avg_speed = (session_data.get('enhanced_avg_speed') or session_data.get('avg_speed')) or 0
        f.write(f"* **平均配速**：{format_pace(get_pace(avg_speed))}/km\n")
        f.write(f"* **平均心率**：{session_data.get('avg_heart_rate', 0)} bpm\n")
        f.write(f"* **最大心率**：{session_data.get('max_heart_rate', 0)} bpm\n")
        f.write(f"* **平均步頻**：{(session_data.get('avg_running_cadence') or 0)*2} spm\n\n")
        f.write("## 💡 教練建議與成效分析\n")
        f.write("(系統自動分析中...)\n\n")
        f.write("**改進建議：**\n")
        f.write("(系統自動分析中...)\n")

def analyze_fit(file_path, person_info=None):
    if person_info is None:
        person_info = {
            'max_hr': 189,
            'resting_hr': 58,
            'weight': 72.0
        }
    
    max_hr = person_info['max_hr']
    resting_hr = person_info['resting_hr']
    weight = person_info['weight']
    hrr = max_hr - resting_hr
    
    try:
        fitfile = fitparse.FitFile(file_path)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return
    
    records = []
    
    # Extract records
    for m in fitfile.get_messages('record'):
        data = m.get_values()
        if 'timestamp' in data and 'distance' in data:
            record = {
                'timestamp': data.get('timestamp'),
                'distance': data.get('distance') or 0,
                'speed': data.get('enhanced_speed') or data.get('speed') or 0,
                'heart_rate': data.get('heart_rate') or 0,
                'cadence': (data.get('cadence') or 0) * 2, # SPM
                'stance_time': data.get('stance_time') or 0,
                'vertical_oscillation': data.get('vertical_oscillation') or 0,
                'step_length': (data.get('step_length') or 0) / 1000, # meters
                'power': data.get('power') or 0,
                'altitude': data.get('enhanced_altitude') or data.get('altitude') or 0,
            }
            records.append(record)
            
    # session summary
    session_data = {}
    for m in fitfile.get_messages('session'):
        session_data = m.get_values()
        break
        
    if not records:
        print(f"No distance records in {file_path}, skipping CSVs but generating MD.")
        generate_md(file_path, session_data)
        return
        
    # Process per km
    km_data = []
    current_km = 1
    km_start_idx = 0
    for i, r in enumerate(records):
        if r['distance'] >= current_km * 1000:
            subset = records[km_start_idx:i+1]
            dist_delta = subset[-1]['distance'] - subset[0]['distance']
            time_delta = (subset[-1]['timestamp'] - subset[0]['timestamp']).total_seconds()
            
            if dist_delta > 0:
                avg_speed = dist_delta / time_delta
                avg_hr = sum(x['heart_rate'] for x in subset) / len(subset)
                avg_cadence = sum(x['cadence'] for x in subset) / len(subset)
                avg_power = sum(x['power'] for x in subset) / len(subset)
                re = avg_speed / (avg_power / weight) if avg_power > 0 else 0
                
                km_data.append({
                    'distance': f"{subset[-1]['distance']/1000:.2f}",
                    'cumulative_time': f"{(subset[-1]['timestamp'] - records[0]['timestamp']).total_seconds():.0f}",
                    'pace': format_pace(get_pace(avg_speed)),
                    'max_pace': format_pace(get_pace(max(x['speed'] for x in subset))),
                    'heart_rate': f"{avg_hr:.0f}",
                    'hrr_percent': f"{(avg_hr - resting_hr) / hrr * 100:.1f}%" if hrr > 0 else "0%",
                    'max_heart_rate': f"{max(x['heart_rate'] for x in subset):.0f}",
                    'cadence': f"{avg_cadence:.0f}",
                    'max_cadence': f"{max(x['cadence'] for x in subset):.0f}",
                    'stride_length': f"{sum(x['step_length'] for x in subset) / len(subset):.2f}",
                    'gct': f"{sum(x['stance_time'] for x in subset) / len(subset):.1f}",
                    'vertical_oscillation': f"{sum(x['vertical_oscillation'] for x in subset) / len(subset):.1f}",
                    'power': f"{avg_power:.0f}",
                    'max_power': f"{max(x['power'] for x in subset):.0f}",
                    'running_effectiveness': f"{re:.3f}",
                    'altitude_change': f"{subset[-1]['altitude'] - subset[0]['altitude']:.1f}"
                })
            km_start_idx = i
            current_km += 1

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    if km_data:
        with open(f"{base_name}_km.csv", 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=km_data[0].keys())
            writer.writeheader()
            writer.writerows(km_data)

    # Process per minute
    min_data = []
    current_min = 1
    min_start_time = records[0]['timestamp']
    min_start_idx = 0
    for i, r in enumerate(records):
        if (r['timestamp'] - min_start_time).total_seconds() >= current_min * 60:
            subset = records[min_start_idx:i+1]
            dist_delta = subset[-1]['distance'] - subset[0]['distance']
            time_delta = (subset[-1]['timestamp'] - subset[0]['timestamp']).total_seconds()
            
            if time_delta > 0:
                avg_speed = dist_delta / time_delta
                avg_hr = sum(x['heart_rate'] for x in subset) / len(subset)
                avg_cadence = sum(x['cadence'] for x in subset) / len(subset)
                avg_power = sum(x['power'] for x in subset) / len(subset)
                re = avg_speed / (avg_power / weight) if avg_power > 0 else 0
                
                min_data.append({
                    'distance': f"{subset[-1]['distance']/1000:.2f}",
                    'cumulative_time': f"{(subset[-1]['timestamp'] - records[0]['timestamp']).total_seconds():.0f}",
                    'pace': format_pace(get_pace(avg_speed)),
                    'max_pace': format_pace(get_pace(max(x['speed'] for x in subset))),
                    'heart_rate': f"{avg_hr:.0f}",
                    'hrr_percent': f"{(avg_hr - resting_hr) / hrr * 100:.1f}%" if hrr > 0 else "0%",
                    'max_heart_rate': f"{max(x['heart_rate'] for x in subset):.0f}",
                    'cadence': f"{avg_cadence:.0f}",
                    'max_cadence': f"{max(x['cadence'] for x in subset):.0f}",
                    'stride_length': f"{sum(x['step_length'] for x in subset) / len(subset):.2f}",
                    'gct': f"{sum(x['stance_time'] for x in subset) / len(subset):.1f}",
                    'vertical_oscillation': f"{sum(x['vertical_oscillation'] for x in subset) / len(subset):.1f}",
                    'power': f"{avg_power:.0f}",
                    'max_power': f"{max(x['power'] for x in subset):.0f}",
                    'running_effectiveness': f"{re:.3f}",
                    'altitude_change': f"{subset[-1]['altitude'] - subset[0]['altitude']:.1f}"
                })
            min_start_idx = i
            current_min += 1

    if min_data:
        with open(f"{base_name}_min.csv", 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=min_data[0].keys())
            writer.writeheader()
            writer.writerows(min_data)

    generate_md(file_path, session_data)

def main():
    parser = argparse.ArgumentParser(description='Analyze runner FIT files.')
    parser.add_argument('path', help='Path to a folder or a .fit file')
    args = parser.parse_args()

    person_info = {
        'max_hr': 189,
        'resting_hr': 58,
        'weight': 72.0
    }

    if os.path.isdir(args.path):
        pattern = r'^\d{8}-\d{6}[+-]\d{4}\.fit$'
        for f in os.listdir(args.path):
            if re.match(pattern, f):
                analyze_fit(os.path.join(args.path, f), person_info)
    elif os.path.isfile(args.path):
        analyze_fit(args.path, person_info)

if __name__ == "__main__":
    main()
