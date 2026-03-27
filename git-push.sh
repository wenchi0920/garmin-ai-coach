#!/bin/bash

# 1. 環境設定
export PATH=$PATH:/usr/local/bin:/usr/local/sbin
export LANG=zh_TW.UTF-8

# 切換至腳本所在目錄 (專案根目錄)
dname=$(/usr/bin/dirname "$0")
dname=$(/bin/readlink -f "$dname")
cd "${dname}"

# 設定日誌檔案
LOG_DIR="logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/git-push_$(date +%Y-%m-%d).log"

# 將所有輸出 (stdout & stderr) 同時輸出到終端機與日誌檔案
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "--------------------------------------------------"
echo "🚀 準備同步訓練數據至 GitHub... (執行時間: $(date '+%Y-%m-%d %H:%M:%S'))"

# 2. 準備追蹤清單
# 包含：本週課表、YAML 設定、訓練日誌、個人資料、README
TARGET_FILES=(
    "logs/Workouts/*/*.md"
    "logs/Workouts/*/*.yaml"
    "logs/activity/"
    "logs/PERSON.md"
    "README.md"
)

git pull

# 執行 Git Add
git add logs/Workouts/*/*.md logs/Workouts/*/*.yaml logs/activity/ logs/PERSON.md README.md 2>/dev/null

# 3. 檢查是否有變更
if git diff --cached --quiet; then
    echo "✅ 目前沒有需要更新的變更，跳過同步。"
    exit 0
fi

# 4. 執行 Commit
# 優先嘗試自定義的 git-commit --auto，失敗則使用標準 git commit
current_date=$(date +"%Y-%m-%d")
commit_msg="docs: update training logs and workouts ($current_date)"

echo "📝 正在產生 Commit: $commit_msg"

if command -v git-commit &> /dev/null; then
    git-commit --auto logs/Workouts/*/*.md logs/Workouts/*/*.yaml logs/activity/ 2>/dev/null || \
    git commit -m "$commit_msg"
else
    git commit -m "$commit_msg"
fi

# 5. 推送至遠端
echo "雲端同步中..."
if git push; then
    echo "🎉 同步完成！所有訓練紀錄已安全儲存。"
else
    echo "❌ 推送失敗，請檢查網路連線或權限。"
    exit 1
fi
