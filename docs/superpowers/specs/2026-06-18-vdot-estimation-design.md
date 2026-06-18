# VDOT Estimation Feature Design Spec

## 1. Overview
The goal of this feature is to estimate Jack Daniels' VDOT for everyday running training without asking an AI. This is achieved by taking the heart rate and pace from a Garmin `.fit` file's derived `_laps.csv` and extrapolating the theoretical 100% VO2max utilizing the Heart Rate Reserve (HRR) percentage method.

## 2. Architecture & Data Flow
1. **Execution Point**: The feature integrates into the existing `parse_activity.sh` shell script.
2. **Sequential Step**: 
   - `parse_activity.sh` runs `fit_analyzer.py <fit_file>` which generates a `*_laps.csv`.
   - `parse_activity.sh` immediately calls a new script: `python vdot_calculator.py <CSV_PATH>`.
3. **Data Injection**: The stdout Markdown string produced by `vdot_calculator.py` is captured and appended/injected into the final Markdown report of the activity.
4. **Constraint Checklist**: 
   - [x] Does not modify `fit_analyzer.py`.
   - [x] Does not modify `PERSON.md` or `GEMINI.md`.
   - [x] Uses existing `_laps.csv` output.

## 3. Core Logic (vdot_calculator.py)
* **Input Extraction**:
  - `PERSON.md` is parsed to find `Resting HR` and `Max HR` to calculate HRR (Heart Rate Reserve).
  - The `_laps.csv` file is read using `pandas` to aggregate moving distance, time, and average heart rate over the entire run (or weighted average of valid laps).
* **Algorithm (Jack Daniels VO2 Translation)**:
  1. Average pace is converted to velocity ($v$) in meters per minute.
  2. Compute Oxygen Cost ($VO_2$) for that pace: 
     $$VO_2 = 0.182258 \times v + 0.000104 \times v^2 - 4.60$$
  3. Compute Intensity Percentage (%HRR): 
     $$\%HRR = \frac{AvgHR - RestHR}{MaxHR - RestHR}$$
  4. Estimate VDOT: 
     $$VDOT = \frac{VO_2}{\%HRR}$$
* **Output Format**:
  - A small Markdown block, e.g.:
    `> 🏃 **估算 VDOT**: 48.5 (基於平均配速 5'15"/km 與 心率 148 bpm, 佔比 75%)`

## 4. Edge Cases & Error Handling
* **Non-Running Detection**: If average pace is extremely slow (< 10'00"/km) or extremely fast (< 2'30"/km), or if HR data is missing/corrupted, the script exits silently with a return code 0 and an empty string.
* **Low Intensity Misfire**: If %HRR < 50%, VDOT scaling becomes highly inaccurate. The script will output a placeholder stating "本次訓練強度過低，無法準確估算 VDOT".
* **Exception Safety**: Any missing files, `pandas` parse errors, or divide-by-zero occurrences are caught (`try/except`) to ensure the shell pipeline is never broken.
