import os
import sys
import re

def fix_readme_links(country_code):
    # Get the directory where the script is located
    base_dir = os.getcwd()
    target_dir = os.path.join(base_dir, country_code.lower())
    readme_path = os.path.join(target_dir, "README.md")

    if not os.path.exists(readme_path):
        print(f"Error: {readme_path} not found.")
        return

    # 1. Get all race detail files (excluding README.md)
    race_files = [f for f in os.listdir(target_dir) if f.endswith(".md") and f != "README.md"]
    
    with open(readme_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    updated = False

    # 2. Scan README.md table lines
    for line in lines:
        # Match Markdown table rows (at least 6 pipes for 5+ columns)
        if "|" in line and line.count("|") >= 6:
            parts = [p.strip() for p in line.split("|")]
            # Table Structure Expected:
            # | Index | 月份 | 賽事名稱(中文) | Race Name | 特色描述 | 賽道認證 | 詳情連結 |
            # OR (according to GEMINI.md)
            # | 月份 | 賽事名稱(中文) | Race Name | 特色描述 | 賽道認證 | 詳情連結 |
            
            # Find which column contains Race Name and Details Link
            # We look for the "詳情連結" column index
            header_row = False
            if "詳情連結" in line:
                header_row = True
            
            if not header_row and len(parts) >= 6:
                # Basic heuristic: 
                # Find the English name (usually column 3 or 4)
                # Find the link column (usually last or second to last)
                
                # Let's find columns by checking content
                race_name_en = ""
                link_col_idx = -1
                
                # Based on GEMINI.md: 月份, 賽事名稱(中文), Race Name, 特色描述, 賽道認證, 詳情連結
                # parts[0] is empty if line starts with |
                # Indexing: 0:| 1:月份 2:中文 3:Race Name 4:特色 5:認證 6:詳情
                if len(parts) >= 7:
                    race_name_en = parts[3]
                    link_col_idx = 6
                elif len(parts) == 6:
                    race_name_en = parts[2]
                    link_col_idx = 5
                
                if race_name_en and link_col_idx != -1:
                    clean_name = race_name_en.replace(" ", "_").replace("'", "").replace(":", "").replace("/", "_")
                    
                    matched_file = None
                    # 1. Exact match (case insensitive)
                    for rf in race_files:
                        if rf.lower() == f"{clean_name}.md".lower():
                            matched_file = rf
                            break
                    
                    # 2. Partial match if not found
                    if not matched_file:
                        for rf in race_files:
                            clean_rf = rf.replace(".md", "").lower()
                            if clean_rf in clean_name.lower() or clean_name.lower() in clean_rf:
                                matched_file = rf
                                break
                    
                    if matched_file:
                        old_link_content = parts[link_col_idx]
                        # Create standard link: [詳情](filename.md)
                        new_link_content = f"[詳情]({matched_file})"
                        
                        if old_link_content != new_link_content:
                            parts[link_col_idx] = new_link_content
                            # Reconstruct line, handling empty first/last parts from split
                            if line.strip().startswith("|"):
                                line = "| " + " | ".join(parts[1:-1]) + " |\n"
                            else:
                                line = " | ".join(parts) + "\n"
                            updated = True
        
        new_lines.append(line)

    if updated:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"Successfully updated links in {readme_path}")
    else:
        print(f"No changes needed for {readme_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_readme_link.py [country_code]")
    else:
        fix_readme_links(sys.argv[1])
