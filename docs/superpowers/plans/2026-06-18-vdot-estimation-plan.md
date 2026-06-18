# VDOT Estimation Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Estimate Jack Daniels' VDOT for running activities based on Garmin `.fit` generated `_laps.csv` files and inject the result into the activity's markdown report.

**Architecture:** Create a standalone Python script `vdot_calculator.py` that parses `PERSON.md` and `_laps.csv` to calculate VDOT using %HRR and VO2 cost, then modify `parse_activity.sh` to call this script and append the output to the generated markdown file.

**Tech Stack:** Python 3, Pandas, Bash

---

### Task 1: Create the VDOT Calculator Script

**Files:**
- Create: `vdot_calculator.py`

- [ ] **Step 1: Write the minimal initial implementation**

```python
import sys
import os
import re
import pandas as pd

def get_person_data(md_path='logs/PERSON.md'):
    person_data = {"resting_hr": 58, "max_hr": 180}
    if not os.path.exists(md_path):
        return person_data
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
        m_max = re.search(r'最大心率[^\d]*(\d+)\s*bpm', content)
        if not m_max:
            m_max = re.search(r'Z5[^\d]*(\d+)\s*bpm', content)
        if m_max:
            person_data["max_hr"] = int(m_max.group(1))
            
        m_rest = re.search(r'靜息心率[^\d]*(\d+)\s*bpm', content)
        if m_rest:
            person_data["resting_hr"] = int(m_rest.group(1))
    return person_data

def pace_to_velocity(pace_str):
    # Convert pace like "5'30\"/km" or "5'30" to m/min
    if not isinstance(pace_str, str):
        return 0
    m = re.search(r'(\d+)\s*\'\s*(\d+)', pace_str)
    if m:
        mins = int(m.group(1))
        secs = int(m.group(2))
        total_mins = mins + secs / 60.0
        if total_mins > 0:
            return 1000.0 / total_mins
    return 0

def calculate_vdot(csv_path):
    if not os.path.exists(csv_path):
        return ""
        
    person = get_person_data()
    rest_hr = person["resting_hr"]
    max_hr = person["max_hr"]
    hrr = max_hr - rest_hr
    
    if hrr <= 0:
        return ""

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return ""
        
    # Check if necessary columns exist
    if '配速' not in df.columns or '心率' not in df.columns or '累計時間' not in df.columns:
        return ""
        
    # Calculate weighted averages (simplified to mean for now, or just drop empty HRs)
    df = df.dropna(subset=['心率', '配速'])
    if df.empty:
        return ""
        
    avg_hr = df['心率'].mean()
    # To get avg velocity, we can average the velocities of each lap
    velocities = df['配速'].apply(pace_to_velocity)
    velocities = velocities[velocities > 0]
    
    if velocities.empty:
        return ""
        
    avg_v = velocities.mean()
    
    # Non-running sanity check (slower than 10min/km or faster than 2.5min/km)
    if avg_v < 100 or avg_v > 400:
        return ""
        
    # Daniels Formula
    vo2_cost = 0.182258 * avg_v + 0.000104 * (avg_v ** 2) - 4.60
    
    hrr_pct = (avg_hr - rest_hr) / hrr
    
    if hrr_pct < 0.50:
        return "\n> ⚠️ **估算 VDOT**: 本次訓練強度過低 (HRR% < 50%)，無法準確估算 VDOT。\n"
        
    vdot = vo2_cost / hrr_pct
    
    # Format output (ensure it matches markdown style)
    # Convert avg_v back to pace for display
    display_pace_mins = 1000.0 / avg_v
    pmins = int(display_pace_mins)
    psecs = int((display_pace_mins - pmins) * 60)
    
    return f"\n> 🏃 **估算 VDOT**: **{vdot:.1f}** (基於等效配速 {pmins}'{psecs:02d}\"/km 與 平均心率 {avg_hr:.0f} bpm, 強度佔比 {hrr_pct*100:.1f}%)\n"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        result = calculate_vdot(csv_file)
        if result:
            print(result)

```

- [ ] **Step 2: Commit Task 1**

```bash
git add vdot_calculator.py
git commit -m "feat: add VDOT calculator script"
```

---

### Task 2: Integrate VDOT calculation into parse_activity.sh

**Files:**
- Modify: `parse_activity.sh`

- [ ] **Step 1: Modify parse_activity.sh to call vdot_calculator.py**

Modify the success branch of `fit_analyzer.py` execution to check for `_laps.csv` and append VDOT results to the markdown file.
Replace lines 88-94 in `parse_activity.sh` (or conceptually around that block):

```bash
if [[ ! -f "${markdown_file}" || "${force_reanalyze}" == "true" ]]; then
    echo "正在分析 ${fit_file}..."
    if python3 fit_analyzer.py "${fit_file}" > "${markdown_file}"; then
        echo "✅ 分析完成: ${markdown_file}"
        
        # 估算 VDOT 並附加至報告
        laps_csv="${fit_file%.fit}_laps.csv"
        if [[ -f "${laps_csv}" ]]; then
            echo "正在估算 VDOT..."
            python3 vdot_calculator.py "${laps_csv}" >> "${markdown_file}"
        fi
        
        # 初始分析時加入 schedule 參考
        run_ai_coach_advice "${markdown_file}" "並 參照 \`data/schedule.txt\` 參賽紀錄 對比賽"
```

- [ ] **Step 2: Commit Task 2**

```bash
git add parse_activity.sh
git commit -m "feat: integrate VDOT estimation into activity parser"
```
