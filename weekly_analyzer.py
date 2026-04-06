#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purpose: Consolidate Weekly Health, Activity, and Workout data into a single minified report.
Author: AI Coach
Changelog:
- 2026-03-28: Consolidated health, activity, and workout parsing for Plan 10.
"""

import sys
import os
import json
import re
from datetime import datetime, timedelta

def get_json_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try: return json.load(f).get('data', {})
            except: return {}
    return {}

def parse_health_section(data_dir, days=7):
    today = datetime.now()
    dates, rhr_l, bb_l, str_l, slp_l, hrv_l = [], [], [], [], [], []

    for i in range(days - 1, -1, -1):
        dt = today - timedelta(days=i)
        d_str = dt.strftime('%Y-%m-%d')
        dates.append(dt.strftime('%m/%d(%a)'))

        hr_d = get_json_data(os.path.join(data_dir, 'heart-rate', f'heart-rate_{d_str}.json'))
        rhr_l.append(f"{hr_d.get('restingHeartRate', '--')}bpm")
        str_l.append(str(hr_d.get('averageStressLevel', '--')))
        
        bb_h = hr_d.get('bodyBatteryHighestValue', '--')
        bb_l_v = hr_d.get('bodyBatteryLowestValue', '--')
        bb_l.append(f"{bb_l_v}↗{bb_h}" if bb_h != '--' else '--')

        slp_d = get_json_data(os.path.join(data_dir, 'sleep', f'sleep_{d_str}.json'))
        slp_l.append(str(slp_d.get('dailySleepDTO', {}).get('sleepScores', {}).get('overall', {}).get('value', '--')))

        hrv_v = slp_d.get('avgOvernightHrv', get_json_data(os.path.join(data_dir, 'hrv', f'hrv_{d_str}.json')).get('hrvSummary', {}).get('lastNightAvg', '--'))
        hrv_l.append(f"{int(hrv_v)}ms" if hrv_v != '--' and hrv_v is not None else '--')

    out = ["### HEALTH METRICS (Last 7 Days)", "|Item|" + "|".join(dates) + "|Trend|", "|:---| " + "|:---| " * len(dates) + ":---|"]
    out.append(f"|RHR|{'|'.join(rhr_l)}|AI|")
    out.append(f"|BB|{'|'.join(bb_l)}|AI|")
    out.append(f"|Stress|{'|'.join(str_l)}|AI|")
    out.append(f"|Sleep|{'|'.join(slp_l)}|AI|")
    out.append(f"|HRV|{'|'.join(hrv_l)}|AI|")
    return "\n".join(out)

def parse_activities_section(activity_dir, count=10):
    files = sorted([os.path.join(activity_dir, f) for f in os.listdir(activity_dir) if f.startswith('activity_') and f.endswith('.md')], reverse=True)[:count]
    out = ["\n### RECENT ACTIVITIES", "|Date|Type|Dist|Pace|Note|Link|", "|:---|:---|:---|:---|:---|:---|"]
    for fpath in reversed(files):
        with open(fpath, 'r') as f:
            content = f.read()
            date = re.search(r'日期[：\s]+([\d-]+)', content)
            type = re.search(r'運動類型[：\s]+([^\n]+)', content)
            dist = re.search(r'距離[：\s]+([\d\.km]+)', content)
            pace = re.search(r'平均配速[：\s]+([^\n]+)', content)
            # Minify note: first 30 chars of coach advice
            advice = re.search(r'## 💡 教練建議與成效分析\n+([^\n]+)', content)
            
            d = date.group(1) if date else "--"
            t = type.group(1).strip() if type else "--"
            ds = dist.group(1) if dist else "--"
            p = pace.group(1).strip() if pace else "--"
            a = (advice.group(1)[:30] + "...") if advice else "--"
            l = os.path.relpath(fpath, '.')
            out.append(f"|{d}|{t}|{ds}|{p}|{a}|{l}|")
    return "\n".join(out)

def parse_workout_section(workout_file):
    if not workout_file or not os.path.exists(workout_file): return "\n### WEEKLY WORKOUT SUMMARY: (None)"
    with open(workout_file, 'r') as f:
        lines = f.readlines()
    
    # Extract only key headers and summaries to save tokens
    extracted = ["\n### WEEKLY WORKOUT SUMMARY"]
    capture = False
    for line in lines:
        if "## 上週執行回顧" in line or "## 本週訓練重點" in line:
            extracted.append(line.strip())
            capture = True
        elif line.startswith("## ") and capture: # Stop at next header
            capture = False
        elif capture and line.strip() and not line.startswith("<!--"):
            extracted.append(line.strip())
    return "\n".join(extracted)

if __name__ == "__main__":
    # Args: datadir activitydir workoutfile
    d_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    a_dir = sys.argv[2] if len(sys.argv) > 2 else "logs/activity"
    w_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    print(parse_health_section(d_dir))
    print(parse_activities_section(a_dir))
    print(parse_workout_section(w_file))
