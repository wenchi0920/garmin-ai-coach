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

# 2. 動態計算或接收週資訊
if [ -n "$1" ] && [ -n "$2" ]; then
    YEAR=$1
    WEEK_NUM=$(printf "%02d" "$2")
    # 根據 ISO 週次計算該週週一的日期
    MONDAY_DATE=$(date -d "${YEAR}-W${WEEK_NUM}-1" +%Y-%m-%d)
    echo "使用指定週次: ${YEAR} W${WEEK_NUM} (週一日期: ${MONDAY_DATE})"
else
    # 預設為本週 (以本週一為基準)
    NEXT_MONDAY=$(date -d "next-monday" +%Y-%m-%d)
    MONDAY_DATE=$(date -d "$NEXT_MONDAY -7 days" +%Y-%m-%d)
    YEAR=$(date -d "$MONDAY_DATE" +%Y)
    WEEK_NUM=$(date -d "$MONDAY_DATE" +%V)
    echo "使用當前週次: ${YEAR} W${WEEK_NUM} (週一日期: ${MONDAY_DATE})"
fi

# 定義輸出的檔案路徑
weekfile="logs/Workouts/${YEAR}/Workouts-${YEAR}-W${WEEK_NUM}.md"
yamlfile="logs/Workouts/${YEAR}/Workouts-${YEAR}-W${WEEK_NUM}.yaml"

echo "========================================"
echo "📅 檢查課表週期: ${MONDAY_DATE} (${YEAR}-W${WEEK_NUM})"
echo "📍 Markdown 檔案: ${weekfile}"
echo "📍 Garmin YAML 檔案: ${yamlfile}"
echo "========================================"

if [ ! -f "${weekfile}" ] || [ ! -f "${yamlfile}" ]; then
    # 3. 產生該週課表
    mkdir -p "$(dirname "${weekfile}")"
    
    PROMPT=" @logs/PERSON.md @GEMINI.md
你現在是一位資深的馬拉松教練 AI Coach。
請根據 @logs/PERSON.md 中的賽事規劃與目標，參考 @Workouts.md 的結構，為跑者產生 ${YEAR} 第 ${WEEK_NUM} 週 (從 ${MONDAY_DATE} 開始) 的課表。

### 任務：
1. **產生 Markdown 課表說明**：包含上週回饋（參考過往紀錄）、本週訓練重點、每日詳細課表。
   - 請使用 \`write_file\` 寫入至 \`${weekfile}\`。
2. **產生 Garmin 上傳用 YAML 課表**：符合 garmin-tools-kit(https://github.com/wenchi0920/garmin-tools-kit) 格式，包含本週所有 跑步/肌力訓練(徒手or重量訓練)/瑜伽(每日放鬆舒緩) 課表。
   **課表名稱範例 W12-修復瑜伽-賽後排除疲勞 (0317) 、 W13-5km Z2 基礎有氧 (0326) 、 W13-6km Z2 輕鬆跑 (0329) **
   - 請使用 \`write_file\` 寫入至 \`${yamlfile}\`。

### 要求：
- 確保內容使用繁體中文，語氣專業、嚴謹且具鼓勵性。
- YAML 內容必須精確，以便後續自動化上傳。
- 課表應嚴格遵守 @GEMINI.md 中的週期化訓練原則（每週 1 天休息、1 天長跑、1 天Zoone 2訓練日、1 天質量日）。
"

    echo "--------------------------------------------------"
    echo "🚀 正在啟動 ${YEAR}-W${WEEK_NUM} 課表 (MD & YAML) 更新程序 ..."
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
            sleep 10
        done

	if [ "$result" == "Y" ]; then
		python3 /app/garmin-tools-kit/garmin_tools.py --env-file /app/garmin-tools-kit/.env workout upload "${yamlfile}"
#		python3 /app/garmin-tools-kit/garmin_tools.py --env-file /app/garmin-tools-kit/.env workout upload "${yamlfile}"
		#git commit -m "docs: update training logs ${markdown_file}" "${markdown_file}"
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
	git add -f "${weekfile}" "${yamlfile}"
	git commit -m "docs: update ${YEAR} W$WEEK_NUM 課表" "${weekfile}" "${yamlfile}"
	echo "${weekfile}"
fi

exit 0
