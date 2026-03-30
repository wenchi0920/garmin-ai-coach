#!/bin/bash

# 1. 環境設定
export PATH=$PATH:/usr/local/bin:/usr/local/sbin
export PATH=$PATH:/usr/local/bin:/usr/local/sbin:/home/gemini/.npm-global/bin
export LANG=zh_TW.UTF-8

# 切換至專案根目錄
dname=$(/usr/bin/dirname "$0")
dname=$(/bin/readlink -f "$dname")
cd "${dname}"

# 設定日誌檔案
LOG_DIR="logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/week_$(date +%Y-%m-%d).log"

# 將所有輸出 (stdout & stderr) 同時輸出到終端機與日誌檔案
exec > >(tee -a "${LOG_FILE}") 2>&1

# 2. 動態計算本週資訊 (以本週一為基準)
# 使用更穩健的方式計算本週一
NEXT_MONDAY=$(date -d "next-monday" +%Y-%m-%d)
MONDAY_DATE=$(date -d "$NEXT_MONDAY -7 days" +%Y-%m-%d)

YEAR=$(date -d "$MONDAY_DATE" +%Y)
WEEK_NUM=$(date -d "$MONDAY_DATE" +%V)

# 定義輸出的檔案路徑
weekfile="logs/Workouts/${YEAR}/Workouts-${MONDAY_DATE}-W${WEEK_NUM}.md"
yamlfile="logs/Workouts/${YEAR}/Workouts-${MONDAY_DATE}-W${WEEK_NUM}.yaml"

echo "========================================"
echo "📅 檢查課表週期: ${MONDAY_DATE} (W${WEEK_NUM})"
echo "📍 Markdown 檔案: ${weekfile}"
echo "📍 Garmin YAML 檔案: ${yamlfile}"
echo "========================================"

if [ ! -f "${weekfile}" ] || [ ! -f "${yamlfile}" ]; then
    # 3. 產生本週課表
    mkdir -p "$(dirname "${weekfile}")"
    
    PROMPT=" @logs/PERSON.md @GEMINI.md
你現在是一位資深的馬拉松教練 AI Coach。
請根據 @logs/PERSON.md 中的賽事規劃與目標，參考 @Workouts.md 的結構，為跑者產生本週課表。

### 任務：
1. **產生 Markdown 課表說明**：包含上週回顧、本週訓練重點、每日詳細課表。
   - 請使用 \`write_file\` 寫入至 \`${weekfile}\`。
2. **產生 Garmin 上傳用 YAML 課表**：符合 garmin-tools-kit(https://github.com/wenchi0920/garmin-tools-kit) 格式，包含本週所有 跑步/肌力訓練(徒手or重量訓練)/瑜伽(每日放鬆舒緩) 課表。
   - 請使用 \`write_file\` 寫入至 \`${yamlfile}\`。

### 要求：
- 確保內容使用繁體中文，語氣專業、嚴謹且具鼓勵性。
- YAML 內容必須精確，以便後續自動化上傳。
"

    echo "--------------------------------------------------"
    echo "🚀 正在啟動 本週課表 (MD & YAML) 更新程序 ..."
    echo "--------------------------------------------------"

    # 4. 執行更新
    if gemini -v &> /dev/null; then
        num=0
        max=3
        result="N"
        
        while [ $max -gt $num ]; do
            echo "gemini 第 $((num+1)) 次執行..."
            # 執行 gemini，並檢查檔案是否產生
            gemini -y -p "$PROMPT" <<< ""
            
            if [ -f "${weekfile}" ] && [ -f "${yamlfile}" ]; then
                echo "✅ 課表與 YAML 更新成功！"
                result="Y"
                break
            fi
            echo "⚠️ 第 $((num+1)) 次嘗試未完整偵測到檔案產生，準備重試..."
            num=$((num+1))
            sleep 2
        done

        if [ "$result" == "Y" ]; then
		python3 /app/garmin-tools-kit/garmin_tools.py --env-file /app/garmin-tools-kit/.env workout upload "${weekfile}"
            echo "Update 課表 SUCCESS: W${WEEK_NUM}" | python3 send_msg.py
        else
            echo "Update 課表 ERROR: 檔案生成不完整" | python3 send_msg.py
        fi
    else
        echo "❌ 錯誤：未偵測到 gemini 指令。"
    fi
else
    echo "ℹ️ 課表與 YAML 檔案皆已存在，跳過生成程序。"
fi

# 5. 輸出結果
if [ -f "${weekfile}" ]; then
    cat "${weekfile}"
fi

exit 0
