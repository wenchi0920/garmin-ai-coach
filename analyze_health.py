#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purpose: Analyze health metrics from Garmin JSON files and generate a Markdown table.
Author: AI Coach
Changelog:
- 2026-03-28: Initial version for JSON data structure.
"""

import sys
import os
import json
from datetime import datetime, timedelta

def get_json_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f).get('data', {})
            except json.JSONDecodeError:
                return {}
    return {}

def parse_health_json(data_dir, days=7):
    # Determine the date range (ending today or the latest available date)
    # For now, we use the current date as reference
    today = datetime.now()
    # If we want to align with the data, we might want to find the latest date in the files
    # But as a general tool, we'll take the last N days from "today"
    
    date_list = []
    for i in range(days - 1, -1, -1):
        date_list.append(today - timedelta(days=i))

    dates_formatted = []
    rhr_list = []
    bb_list = []
    stress_list = []
    sleep_list = []
    hrv_list = []

    for dt in date_list:
        date_str = dt.strftime('%Y-%m-%d')
        weekday = dt.strftime('%a')
        dates_formatted.append(dt.strftime('%m/%d') + f" ({weekday})")

        # 1. RHR & Stress (often in heart-rate or stress folder, same structure)
        # We'll try heart-rate first
        hr_file = os.path.join(data_dir, 'heart-rate', f'heart-rate_{date_str}.json')
        hr_data = get_json_data(hr_file)
        
        rhr = hr_data.get('restingHeartRate', '--')
        rhr_list.append(f"{rhr} bpm" if rhr != '--' else '--')
        
        stress = hr_data.get('averageStressLevel', '--')
        stress_list.append(str(stress))

        # 2. Body Battery
        bb_file = os.path.join(data_dir, 'body-battery_2026', f'body-battery_{date_str}.json')
        bb_data = get_json_data(bb_file)
        # Fallback if highest/lowest not in heart-rate data
        bb_high = hr_data.get('bodyBatteryHighestValue', bb_data.get('bodyBatteryHighestValue', '--'))
        bb_low = hr_data.get('bodyBatteryLowestValue', bb_data.get('bodyBatteryLowestValue', '--'))
        
        if bb_high != '--' and bb_low != '--':
            bb_list.append(f"{bb_low} ↗ {bb_high}")
        else:
            bb_list.append("--")

        # 3. Sleep
        sleep_file = os.path.join(data_dir, 'sleep', f'sleep_{date_str}.json')
        sleep_data = get_json_data(sleep_file)
        sleep_score = sleep_data.get('dailySleepDTO', {}).get('sleepScores', {}).get('overall', {}).get('value', '--')
        sleep_list.append(str(sleep_score))

        # 4. HRV
        hrv_file = os.path.join(data_dir, 'hrv', f'hrv_{date_str}.json')
        hrv_data = get_json_data(hrv_file)
        hrv_val = hrv_data.get('hrvSummary', {}).get('lastNightAvg', '--')
        # If not in hrv file, try sleep file (sometimes it's there)
        if hrv_val == '--':
            hrv_val = sleep_data.get('avgOvernightHrv', '--')
        
        hrv_list.append(f"{int(hrv_val)} ms" if hrv_val != '--' and hrv_val is not None else '--')

    # Build Markdown Table
    header = "| 指標項目 | " + " | ".join(dates_formatted) + " | 趨勢分析 |"
    separator = "| :--- | " + " | ".join([":---"] * len(dates_formatted)) + " | :--- |"
    
    rows = [
        f"| **靜止心率 (RHR)** | " + " | ".join(rhr_list) + " | AI分析 |",
        f"| **身體能量 (BB)** | " + " | ".join(bb_list) + " | AI分析 |",
        f"| **壓力指數 (Stress)** | " + " | ".join(stress_list) + " | AI分析 |",
        f"| **睡眠分數 (Sleep)** | " + " | ".join(sleep_list) + " | AI分析 |",
        f"| **HRV (心率變異度)** | " + " | ".join(hrv_list) + " | AI分析 |"
    ]

    output = [
        f"### **關鍵生理指標監控表 (近 {days} 天)(勿修改格式)**",
        header,
        separator
    ] + rows

    return "\n".join(output)

if __name__ == "__main__":
    # Usage: python analyze_health.py <datadir> <days>
    if len(sys.argv) < 2:
        print("Usage: python analyze_health.py <datadir> [days]")
        sys.exit(1)
    
    data_dir = sys.argv[1]
    num_days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    
    print(parse_health_json(data_dir, num_days))
