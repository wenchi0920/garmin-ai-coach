import sys
import os
import csv
import pandas as pd
import numpy as np
import re
import yaml
from datetime import datetime, timedelta
from fitparse import FitFile
from geopy.geocoders import Nominatim

# Configuration for HR and Pace Zones (from PERSON.md)
DEFAULT_PERSON_DATA = {
    "resting_hr": 50,
    "max_hr": 180,
    "hr_zones": [(119, 131), (131, 143), (143, 155), (155, 167), (167, 180)],
    "pace_zones": [(471, 9999), (421, 471), (383, 421), (358, 383), (330, 358), (0, 330)],
}

# Load Activity Type Config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'activity_types.yml')
EXERCISE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'garmin_exercises.yml')
ACTIVITY_CONFIG = {}
CATEGORY_MAP = {}
EXERCISE_MAP = {}

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            ACTIVITY_CONFIG = yaml.safe_load(f)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to load activity config: {e}\n")

if os.path.exists(EXERCISE_CONFIG_PATH):
    try:
        with open(EXERCISE_CONFIG_PATH, 'r', encoding='utf-8') as f:
            ex_data = yaml.safe_load(f)
            CATEGORY_MAP = ex_data.get('categories', {})
            EXERCISE_MAP = ex_data.get('exercises', {})
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to load exercise map: {e}\n")

def get_exercise_name_zh(category, name_enum):
    # Try raw values from exercises first (specific strings)
    if name_enum in EXERCISE_MAP:
        return EXERCISE_MAP[name_enum]
    
    # Try raw values from categories (integers)
    if category in CATEGORY_MAP:
        return CATEGORY_MAP[category]
        
    # Fallback to string mapping
    cat_str = str(category).lower()
    name_str = str(name_enum).lower() if name_enum else ""
    
    if name_str in EXERCISE_MAP:
        return EXERCISE_MAP[name_str]
    if cat_str in CATEGORY_MAP:
        return CATEGORY_MAP[cat_str]
    
    # Fallback to raw strings if not in map
    if name_str and name_str != 'none' and name_str != '0':
        return name_str.replace('_', ' ').title()
    return cat_str.replace('_', ' ').title()

def get_activity_type_zh(sport, sub_sport):
    sport_map = ACTIVITY_CONFIG.get('sport_map', {})
    sub_sport_map = ACTIVITY_CONFIG.get('sub_sport_map', {})
    
    sport_zh = sport_map.get(sport, str(sport))
    sub_sport_zh = sub_sport_map.get(sub_sport, str(sub_sport))
    
    if sub_sport and sub_sport != 'generic' and sub_sport != sport:
        if sub_sport_zh != str(sub_sport):
            return f"{sport_zh} - {sub_sport_zh}"
        return f"{sport_zh} ({sub_sport})"
    return sport_zh

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
            # Extract Max HR
            m_max = re.search(r'最大心率[^\d]*(\d+)\s*bpm', content)
            if not m_max:
                m_max = re.search(r'Z5[^\d]*(\d+)\s*bpm', content)
            if m_max: 
                person_data["max_hr"] = int(m_max.group(1))
            
            # Extract Resting HR
            m_rest = re.search(r'靜息心率[^\d]*(\d+)\s*bpm', content)
            if m_rest:
                person_data["resting_hr"] = int(m_rest.group(1))
            else:
                # Fallback or keep default
                person_data["resting_hr"] = 58 # As seen in previous code
                
            # Calculate HRR zones according to GEMINI.md
            # Z1: 59%~74%, Z2: 74%~84%, Z3: 84%~88%, Z4: 88%~95%, Z5: 95%~100%
            hrr = person_data["max_hr"] - person_data["resting_hr"]
            def get_hr(pct): return int(person_data["resting_hr"] + hrr * pct)
            
            person_data["hr_zones"] = [
                (get_hr(0.59), get_hr(0.74)), # Z1
                (get_hr(0.74), get_hr(0.84)), # Z2
                (get_hr(0.84), get_hr(0.88)), # Z3
                (get_hr(0.88), get_hr(0.95)), # Z4
                (get_hr(0.95), get_hr(1.00))  # Z5
            ]
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to parse {md_path}: {e}\n")
    return person_data

def get_location_str(lat, lon):
    if lat is None or lon is None: return ""
    
    # Try reverse geocoding to get city/district
    try:
        # Nominatim requires a user_agent
        geolocator = Nominatim(user_agent="garmin_ai_coach")
        # Reverse geocode with Traditional Chinese language
        location = geolocator.reverse((lat, lon), language='zh-tw', timeout=10)
        if location:
            address = location.raw.get('address', {})
            # Preferred components for Taiwan/General
            # City/County -> Town/District
            city = address.get('city') or address.get('town') or address.get('village') or address.get('county') or address.get('state', '')
            district = address.get('suburb') or address.get('district', '')
            
            # Combine to form something like "台東縣台東市" or "台北市信義區"
            # If city and district are the same (e.g. Taipei City), only return one if needed, but usually they are distinct
            location_name = f"{city}{district}".strip()
            if location_name:
                return location_name
            return str(location)
    except Exception as e:
        sys.stderr.write(f"Warning: Geocoding failed: {e}\n")
    
    # Fallback to GPS coordinates if geocoding fails
    return f"{lat:.6f}, {lon:.6f}"

def extract_tz_offset(file_path):
    basename = os.path.basename(file_path)
    # Pattern: activity_..._HH-MM-SS+0800.fit
    match = re.search(r'\+([0-9]{2})([0-9]{2})', basename)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return timedelta(hours=hours, minutes=minutes)
    return timedelta(0)

def extract_local_time_from_filename(file_path):
    basename = os.path.basename(file_path)
    # Pattern: activity_YYYY-MM-DD_HH-MM-SS+ZZZZ.fit
    match = re.search(r'activity_(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})-(\d{2})', basename)
    if match:
        date_str = match.group(1)
        h, m, s = match.group(2), match.group(3), match.group(4)
        try:
            return datetime.strptime(f"{date_str} {h}:{m}:{s}", '%Y-%m-%d %H:%M:%S')
        except:
            return None
    return None

def parse_fit(file_path):
    if not file_path.lower().endswith('.fit'):
        sys.stderr.write(f"Error: {file_path} is not a .fit file.\n")
        return

    sys.stderr.write(f"Analyzing {file_path}...\n")
    try:
        fitfile = FitFile(file_path)
    except Exception as e:
        sys.stderr.write(f"Error parsing {file_path}: {e}\n")
        return
    
    person_data = parse_person_md()
    records = []
    hrv_data = []
    laps_data = []
    
    # Extract Timezone Offset
    tz_offset = extract_tz_offset(file_path)
    
    # Extract HRV
    for message in fitfile.get_messages('hrv'):
        hrv_vals = message.get_values().get('time')
        if hrv_vals:
            if isinstance(hrv_vals, tuple): hrv_data.extend(hrv_vals)
            else: hrv_data.append(hrv_vals)

    # Extract Laps with full metrics
    for i, lap in enumerate(fitfile.get_messages('lap')):
        data = lap.get_values()
        
        lap_dist = (data.get('total_distance') or 0) / 1000.0
        lap_time = data.get('total_timer_time') or 0
        avg_speed = data.get('avg_speed')
        if (avg_speed is None or avg_speed == 0) and lap_dist > 0 and lap_time > 0:
            avg_speed = (lap_dist * 1000.0) / lap_time
            
        max_speed = data.get('max_speed')
        if (max_speed is None or max_speed == 0) and avg_speed:
            max_speed = avg_speed
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
            "配速": format_pace(1000.0 / avg_speed if avg_speed and avg_speed > 0 else 0),
            "最快配速": format_pace(1000.0 / max_speed if max_speed and max_speed > 0 else 0),
            "心率": f"{avg_hr:.0f}" if avg_hr else '',
            "儲備心率%": hrr_pct,
            "最大心率": f"{data.get('max_heart_rate'):.0f}" if data.get('max_heart_rate') else '',
            "步頻": f"{data.get('avg_cadence'):.0f}" if data.get('avg_cadence') else '',
            "最大步頻": f"{data.get('max_cadence'):.0f}" if data.get('max_cadence') else '',
            "步幅": f"{data.get('avg_step_length') / 1000.0:.2f}" if data.get('avg_step_length') else '',
            "觸地時間": f"{data.get('avg_stance_time'):.1f}" if data.get('avg_stance_time') else '',
            "垂直振幅": f"{data.get('avg_vertical_oscillation'):.1f}" if data.get('avg_vertical_oscillation') else '',
            "功率": f"{avg_power:.0f}" if avg_power is not None else '',
            "最大功率": f"{data.get('max_power'):.0f}" if data.get('max_power') else '',
            "效能": efficiency,
            "海拔變化": f"{data.get('total_ascent', 0) - data.get('total_descent', 0):.0f}" if data.get('total_ascent') is not None else ''
        })

    # Extract Exercise Titles and Workout Steps for Strength/Yoga
    exercise_titles = {}
    for m in fitfile.get_messages('exercise_title'):
        val = m.get_values()
        exercise_titles[val.get('message_index')] = val.get('wkt_step_name')
    
    workout_steps = {}
    for m in fitfile.get_messages('workout_step'):
        val = m.get_values()
        workout_steps[val.get('message_index')] = val.get('notes')

    # Extract Sets
    all_sets = []
    for m in fitfile.get_messages('set'):
        val = m.get_values()
        # Get local start time
        start_time_utc = val.get('start_time')
        local_start = start_time_utc + tz_offset if start_time_utc else None
        
        # Determine name: For Strength, prioritize Category mapping to avoid mismatch
        wkt_idx = val.get('wkt_step_index')
        cat = val.get('category')
        cat_val = cat[0] if isinstance(cat, (tuple, list)) else cat
        subcat = val.get('category_subtype')
        subcat_val = subcat[0] if isinstance(subcat, (tuple, list)) else subcat
        
        # Logic improvement: 
        # 1. First check if there's a custom name from workout steps (often used in Yoga/Custom Workouts)
        custom_name = exercise_titles.get(wkt_idx) or workout_steps.get(wkt_idx)
        
        name = None
        # For Yoga (36) or Flexibility (35), custom_name is usually more accurate
        if (cat_val == 35 or cat_val == 36) and custom_name:
            name = custom_name
        
        # 2. If no custom name, or it's a standard strength category, try mapping
        if not name and cat_val is not None:
            name = get_exercise_name_zh(cat_val, subcat_val)
            
        # 3. Final fallback
        if not name or name == "Unknown" or name == "瑜伽 (Yoga)" or name == "伸展 (Flexibility/Stretch)":
            name = custom_name or name or "Unknown"
            
        all_sets.append({
            "set_type": val.get('set_type'),
            "local_start": local_start,
            "name": name,
            "reps": val.get('repetitions'),
            "weight": val.get('weight'),
            "duration": val.get('duration') or 0,
        })
    
    # Sort all sets by local time
    all_sets.sort(key=lambda x: x['local_start'] if x['local_start'] else datetime.min)
    
    # Extract Records for Summary
    for record in fitfile.get_messages('record'):
        data = record.get_values()
        r = {k: data.get(k) for k in ['timestamp', 'distance', 'heart_rate', 'cadence', 'speed']}
        lat, lon = data.get('position_lat'), data.get('position_long')
        if lat is not None and lon is not None:
            r['lat'], r['lon'] = lat * (180.0 / 2**31), lon * (180.0 / 2**31)
        else: r['lat'] = r['lon'] = None
        records.append(r)

    if not records and not all_sets: return

    # Session handling
    sessions = list(fitfile.get_messages('session'))
    session = next((s.get_values() for s in sessions if s.get_values().get('sport') == 'running'), sessions[0].get_values() if sessions else {})

    # Map activity type to Chinese using config
    sport_type = session.get('sport')
    sub_sport_type = session.get('sub_sport')
    sport_zh = get_activity_type_zh(sport_type, sub_sport_type)

    # Process sets into the requested format
    processed_strength_sets = []
    processed_yoga_sets = []
    exercise_counts = {} # To track set numbers per exercise name
    
    # Use sport_zh to determine output format
    is_strength = "肌力訓練" in sport_zh
    is_yoga = "瑜伽" in sport_zh
    
    if is_strength:
        for i, s in enumerate(all_sets):
            if s['set_type'] in ['active', 'cooldown']:
                name = s['name']
                exercise_counts[name] = exercise_counts.get(name, 0) + 1
                
                # Look for the rest set immediately following this active set
                rest_duration = 0
                if i + 1 < len(all_sets) and all_sets[i+1]['set_type'] == 'rest':
                    rest_duration = all_sets[i+1]['duration']
                
                reps = s['reps'] or 0
                weight = s['weight'] or 0
                
                processed_strength_sets.append({
                    "執行時間": s['local_start'].strftime('%H:%M:%S') if s['local_start'] else "--",
                    "組數": exercise_counts[name],
                    "運動名稱": name,
                    "時間": f"{int(s['duration'] // 60):02d}:{int(s['duration'] % 60):02d}",
                    "休息": f"{int(rest_duration // 60):02d}:{int(rest_duration % 60):02d}",
                    "次數": reps if reps > 0 else "--",
                    "重量": f"{weight} kg" if weight > 0 else "--",
                    "總重量": f"{reps * weight:.1f} kg" if reps > 0 and weight > 0 else "--"
                })
    elif is_yoga:
        for s in all_sets:
            if s['set_type'] in ['active', 'cooldown']:
                processed_yoga_sets.append({
                    "執行時間": s['local_start'].strftime('%H:%M:%S') if s['local_start'] else "--",
                    "姿勢名稱": s['name'],
                    "時間": f"{int(s['duration'] // 60):02d}:{int(s['duration'] % 60):02d}"
                })

    df = pd.DataFrame(records) if records else pd.DataFrame()
    if not df.empty:
        df = df.sort_values('timestamp')
    
    dist = session.get('total_distance') or 0
    t_time = session.get('total_timer_time') or 0

    # Get start time from filename or session
    local_start_time = extract_local_time_from_filename(file_path)
    if not local_start_time:
        if not df.empty:
            local_start_time = session.get('start_time', df['timestamp'].iloc[0])
        else:
            local_start_time = session.get('start_time', datetime.now())

    summary = {
        "date": local_start_time.strftime('%Y-%m-%d'),
        "start_time": local_start_time.strftime('%H:%M:%S'),
        "sport": sport_zh,
        "distance": dist / 1000.0,
        "time": t_time,
        "avg_pace": format_pace(t_time / (dist / 1000.0)) if dist > 0 else "",
        "avg_hr": session.get('avg_heart_rate', df['heart_rate'].mean() if not df.empty else None),
        "max_hr": session.get('max_heart_rate', df['heart_rate'].max() if not df.empty else None),
        "avg_cadence": session.get('avg_cadence', df['cadence'].mean() if not df.empty else None),
        "avg_hrv": np.mean(hrv_data) if hrv_data else 0,
        "location": get_location_str(df['lat'].dropna().iloc[0], df['lon'].dropna().iloc[0]) if not df.empty and df['lat'].notnull().any() else ""
    }

    # Save Laps CSV
    if laps_data:
        pd.DataFrame(laps_data).to_csv(file_path.replace('.fit', '_laps.csv'), index=False, encoding='utf-8-sig')

    # Write MD Report to stdout
    avg_hr_str = f"{summary['avg_hr']:.0f} bpm" if summary['avg_hr'] else ""
    max_hr_str = f"{summary['max_hr']:.0f} bpm" if summary['max_hr'] else ""
    cad_str = f"{summary['avg_cadence']:.0f} spm" if summary['avg_cadence'] else ""
    
    output = []
    output.append(f"# 訓練分析報告: {summary['date']}-{summary['start_time'].replace(':','-')}\n")
    output.append("## 📊 核心數據\n")
    output.append(f"* **日期**：{summary['date']}\n")
    output.append(f"* **運動類型**：{summary['sport']}\n")
    output.append(f"* **起跑時間**：{summary['start_time']}\n")
    output.append(f"* **起跑地點**：{summary['location']}\n")
    output.append(f"* **距離**：{summary['distance']:.2f} km\n")
    output.append(f"* **時間**：{int(summary['time'] // 3600):02d}:{int((summary['time'] % 3600) // 60):02d}:{int(summary['time'] % 60):02d}\n")
    output.append(f"* **平均配速**：{summary['avg_pace']}\n")
    output.append(f"* **平均心率**：{avg_hr_str}\n")
    output.append(f"* **最大心率**：{max_hr_str}\n")
    output.append(f"* **平均步頻**：{cad_str}\n")
    
    if processed_strength_sets:
        output.append("\n## 🏋️ 訓練紀錄 (Sets)\n")
        output.append("| 執行時間 | 組數 | 運動名稱 | 時間 | 休息 | 次數 | 重量 | 總重量 |\n")
        output.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for s in processed_strength_sets:
            output.append(f"| {s['執行時間']} | {s['組數']} | {s['運動名稱']} | {s['時間']} | {s['休息']} | {s['次數']} | {s['重量']} | {s['總重量']} |\n")

    if processed_yoga_sets:
        output.append("\n## 🧘 瑜伽紀錄 (Sets)\n")
        output.append("| 執行時間 | 姿勢名稱 | 時間 |\n")
        output.append("| :--- | :--- | :--- |\n")
        for s in processed_yoga_sets:
            output.append(f"| {s['執行時間']} | {s['姿勢名稱']} | {s['時間']} |\n")

    if laps_data:
        output.append("\n## ⏱️ 分段紀錄 (Laps)\n")
        output.append("| 分段 | 距離 | 累計時間 | 配速 | 最快配速 | 心率 | 儲備心率% | 最大心率 | 步頻 | 最大步頻 | 步幅 | 觸地時間 | 垂直振幅 | 功率 | 最大功率 | 效能 | 海拔變化 |\n")
        output.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for l in laps_data:
            output.append(f"| {l['分段']} | {l['距離']} | {l['累計時間']} | {l['配速']} | {l['最快配速']} | {l['心率']} | {l['儲備心率%']} | {l['最大心率']} | {l['步頻']} | {l['最大步頻']} | {l['步幅']} | {l['觸地時間']} | {l['垂直振幅']} | {l['功率']} | {l['最大功率']} | {l['效能']} | {l['海拔變化']} |\n")

    output.append("\n## 💡 教練建議與成效分析(fit_parse.py 不 立刻分析, 事後分析)\n")
    output.append("(提供 1000 字 內文分析)\n\n")
    output.append("**改進建議：**\n")
    output.append("(提供 1000 字 內文分析)\n")


    sys.stdout.write("".join(output))
    sys.stderr.write(f"Analysis complete for {file_path}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if os.path.exists(arg): 
                parse_fit(arg)
