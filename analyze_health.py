#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purpose: Convert Garmin health data from raw text table to Markdown trend report.
Author: AI Coach
Changelog:
2026-04-27: Enhanced with specific table title and bolded AI comments.
"""

import sys
import re
from datetime import datetime

def parse_health_data(input_file):
    rows = []
    # 精確匹配資料列的正規表達式
    pattern = re.compile(r'^(\d{4}-\d{2}-\d{2})\s+\|\s+([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)')
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('-') or '日期' in line:
                    continue
                    
                match = pattern.search(line)
                if match:
                    date_str = match.group(1).strip()
                    rhr = match.group(5).split('/')[0].strip()
                    stress = match.group(6).split('/')[0].strip()
                    bb = match.group(7).split('/')[0].strip()
                    sleep = match.group(8).split('(')[0].strip()
                    hrv = match.group(9).split('/')[0].strip()
                    
                    rows.append({
                        'date': datetime.strptime(date_str, '%Y-%m-%d').strftime('%m/%d'),
                        'rhr': rhr,
                        'stress': stress,
                        'bb': bb,
                        'sleep': sleep,
                        'hrv': hrv
                    })
    except FileNotFoundError:
        print(f"Error: File {input_file} not found.")
        sys.exit(1)
    
    return rows

def generate_markdown(rows):
    if not rows:
        return "無數據可轉換"

    # 表格標題
    output = ["### 📋 關鍵生理指標監控表 (近 7 天)"]
    
    headers = ["指標"] + [row['date'] for row in rows] + ["趨勢分析"]
    
    def format_row(label, key, data):
        line = [f"**{label}**"]
        for i, row in enumerate(data):
            val = row[key]
            # 最後一天加粗顯示
            if i == len(data) - 1 and val != '--':
                line.append(f"**{val}**")
            else:
                line.append(val)
        # 趨勢分析欄位加粗標記
        line.append("**AI生成註解")
        return f"| {' | '.join(line)} |"

    output.append(f"| {' | '.join(headers)} |")
    # 生成對齊列
    align = [":---"] + [":---:"] * len(rows) + [":---"]
    output.append(f"| {' | '.join(align)} |")
    
    output.append(format_row("RHR (靜息心率)", "rhr", rows))
    output.append(format_row("BB (能量最大值)", "bb", rows))
    output.append(format_row("Stress (壓力值)", "stress", rows))
    output.append(format_row("Sleep (睡眠分數)", "sleep", rows))
    output.append(format_row("HRV (心率變異度)", "hrv", rows))
    
    return "\n".join(output)

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 analyze_health.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    data = parse_health_data(input_file)
    
    if not data:
        print("No valid data rows found.")
        sys.exit(1)
        
    markdown_table = generate_markdown(data)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_table)
    
    print(f"Successfully generated {output_file}")

if __name__ == "__main__":
    main()
