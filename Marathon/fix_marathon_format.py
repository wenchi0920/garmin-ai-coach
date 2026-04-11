import os
import sys

def fix_marathon_file_safe(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    header_text = "[返回國家索引](README.md) | [返回全球總索引](../README.md)"
    footer_sep = "---"
    
    # 提取中間原始資料
    content_lines = []
    for line in lines:
        stripped = line.strip()
        if "[返回國家索引](README.md)" in stripped:
            continue
        if stripped == footer_sep:
            continue
        content_lines.append(line)
    
    content = "".join(content_lines).strip()
    
    # 組合最終格式
    final_output = f"{header_text}\n\n{content}\n\n{footer_sep}\n{header_text}\n"
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_output)
        print(f"Structure Verified (Middle Data Preserved): {file_path}")
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")

def main():
    # 支援命令列輸入目錄，否則預設為當前目錄
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
    else:
        target_dir = "."

    if not os.path.isdir(target_dir):
        print(f"Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)

    print(f"Processing directory: {os.path.abspath(target_dir)}")
    
    # 處理該目錄下除了 README.md 與 腳本本身 以外的所有 .md 檔案
    files = [f for f in os.listdir(target_dir) if f.endswith(".md") and f != "README.md"]
    
    if not files:
        print("No matching .md files found.")
        return

    for filename in files:
        fix_marathon_file_safe(os.path.join(target_dir, filename))

if __name__ == "__main__":
    main()
