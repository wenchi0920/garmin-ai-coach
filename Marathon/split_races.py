import os
import re
import sys

def sanitize_filename(title_line):
    """從標題列提取括號內的英文名稱並轉為合法檔名"""
    # 支援 (English Name) 格式，取括號內文字
    match = re.search(r'\((.*?)\)', title_line)
    if match:
        name = match.group(1).strip()
        # 存下原始英文名稱用於後續匹配 README
        raw_name = name
        # 取代空格為底線，移除不合法字元作為檔名
        filename_base = name.replace(' ', '_')
        filename_base = re.sub(r'[^\w\s-]', '', filename_base)
        return raw_name, f"{filename_base}.md"
    return None, None

def update_readme(target_dir, race_map):
    """更新 README.md 中的連結"""
    readme_path = os.path.join(target_dir, 'README.md')
    if not os.path.exists(readme_path):
        print(f"找不到 {readme_path}，跳過連結更新。")
        return

    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    updated_count = 0
    for raw_name, filename in race_map.items():
        # 尋找包含該賽事名稱的行，並替換 info.md#... 連結
        # 匹配邏輯：找到包含英文名稱的表格行，並捕捉該行末尾的 [文字](info.md#錨點)
        pattern = re.compile(rf'(\|.*?{re.escape(raw_name)}.*?\|.*?\[.*?\]\()info\.md#.*?\)')
        if pattern.search(content):
            content = pattern.sub(rf'\1{filename})', content)
            updated_count += 1
            print(f"README 更新連結: {raw_name} -> {filename}")

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"README 更新完成，共修改 {updated_count} 處連結。")

def split_races(target_dir='.'):
    input_file = os.path.join(target_dir, 'info.md')
    if not os.path.exists(input_file):
        print(f"在 {target_dir} 找不到 {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用正則表達式尋找所有以 ### 開頭的賽事區塊
    pattern = r'(###\s+.*?(?=\n###|\Z))'
    races = re.findall(pattern, content, re.DOTALL)

    # 導航連結
    nav_links = "[返回國家索引](README.md) | [返回全球總索引](../README.md)\n\n"

    race_map = {} # 紀錄 {英文名稱: 檔名} 用於更新 README
    count = 0
    
    for race_content in races:
        lines = race_content.strip().split('\n')
        if not lines: continue
        title_line = lines[0]
        
        raw_name, filename = sanitize_filename(title_line)
        if filename:
            race_map[raw_name] = filename
            file_path = os.path.join(target_dir, filename)
            
            # 組合新內容：導航連結 + 賽事內容
            # 移除內容結尾可能存在的分隔線
            clean_race_content = race_content.strip().rstrip('---').strip()
            new_content = nav_links + clean_race_content + "\n"
            
            with open(file_path, 'w', encoding='utf-8') as nf:
                nf.write(new_content)
            print(f"成功建立: {file_path}")
            count += 1
    
    print(f"\n處理完成，共建立 {count} 個檔案。")
    
    # 執行 README 連結更新
    update_readme(target_dir, race_map)

    # 刪除原始 info.md
    try:
        os.remove(input_file)
        print(f"已成功刪除原始檔案: {input_file}")
    except Exception as e:
        print(f"刪除 {input_file} 失敗: {e}")

if __name__ == "__main__":
    # 接受目錄參數，預設為當前目錄
    dir_to_process = sys.argv[1] if len(sys.argv) > 1 else '.'
    split_races(dir_to_process)
