import os
import re

def find_duplicate_races(root_dir):
    # 賽事標題格式： ### [中文] ([英文])
    race_header_pattern = re.compile(r'^###\s+.*\(.*\)')
    
    duplicates = []
    
    # 遍歷 root_dir 下的所有國家目錄 (長度為 3)
    for item in os.listdir(root_dir):
        dir_path = os.path.join(root_dir, item)
        if os.path.isdir(dir_path) and len(item) == 3:
            for root, _, files in os.walk(dir_path):
                for file in files:
                    if file.endswith('.md') and file != 'README.md':
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                # 檢查 ### 開頭且包含括號的行
                                race_headers = []
                                for line in f:
                                    if line.startswith('### ') and '(' in line and ')' in line:
                                        race_headers.append(line.strip())
                                
                                if len(race_headers) > 1:
                                    duplicates.append({
                                        'file': file_path,
                                        'count': len(race_headers),
                                        'headers': race_headers
                                    })
                        except Exception:
                            pass

    # 輸出結果
    if duplicates:
        print(f"{'檔案路徑':<60} | {'賽事數量':<10}")
        print("-" * 75)
        for entry in duplicates:
            print(f"{entry['file']:<60} | {entry['count']:<10}")
            for h in entry['headers']:
                print(f"  - {h}")
        print(f"\n總共發現 {len(duplicates)} 個檔案包含多筆賽事資料。")
    else:
        print("未發現包含多筆賽事資料的檔案。")

if __name__ == "__main__":
    find_duplicate_races('.')
