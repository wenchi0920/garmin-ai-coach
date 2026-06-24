#!/bin/bash

# 1. 環境設定
export PATH=$PATH:/usr/local/bin:/usr/local/sbin
export PATH=$PATH:/usr/local/bin:/usr/local/sbin:/home/gemini/.npm-global/bin:/root/.local/bin
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
請根據 @logs/PERSON.md 中的賽事規劃與目標，**課表應嚴格遵守 @logs/PERSON.md 中的個人化課表 週期化訓練原則**，參考 @Workouts.md 的結構，為跑者產生 ${YEAR} 第 ${WEEK_NUM} 週 (從 ${MONDAY_DATE} 開始) 的課表。

### 任務：
1. **產生 Markdown 課表說明**：包含上週回饋（參考過往紀錄）、本週訓練重點、每日詳細課表。
   - 請使用 \`write_file\` 寫入至 \`${weekfile}\`。
   - ** 需要依照比賽 當地的 天氣/賽道特性 規劃課表 **
2. **產生 Garmin 上傳用 YAML 課表**：符合 garmin-tools-kit(https://github.com/wenchi0920/garmin-tools-kit) 格式，包含本週所有 跑步/肌力訓練(徒手or重量訓練)/瑜伽(每日放鬆舒緩) 課表。
   **並確保 \`${yamlfile}\` 格式 跟 \`Workouts.yaml\` 一致**
   **課表名稱範例 W12-修復瑜伽-賽後排除疲勞 (0317) 、 W13-5km Z2 基礎有氧 (0326) 、 W13-6km Z2 輕鬆跑 (0329), 一天可以多個訓練 跑步+(瑜伽/肌力)**
   - 請使用 \`write_file\` 寫入至 \`${yamlfile}\`。

### 要求：
- 確保內容使用繁體中文，語氣專業、嚴謹且具鼓勵性。
- YAML 內容必須精確，以便後續自動化上傳。
- **課表應嚴格遵守 @logs/PERSON.md 中的個人化課表 週期化訓練原則**。
"

    echo "--------------------------------------------------"
    echo "🚀 正在啟動 ${YEAR}-W${WEEK_NUM} 課表 (MD & YAML) 更新程序 ..."
    echo "--------------------------------------------------"

    # 4. 執行更新
    if agy -v &> /dev/null; then
        num=0
        max=3
        result="N"
        
        while [ $max -gt $num ]; do
            echo "gemini 第 $((num+1)) 次執行..."
            # 執行 gemini，並檢查檔案是否產生
            agy --dangerously-skip-permissions -p "$PROMPT" <<< ""
            
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
    # 修正：加入 XXXXXX 以符合 mktemp 規範，同時保留 WEEK_NUM 方便除錯
    TMP_LIST=$(mktemp "/tmp/garmin_list.W${WEEK_NUM}.XXXXXX")
    
    # 設定離開時自動清理暫存檔
    trap 'rm -f "$TMP_LIST"' EXIT

    # 執行指令並捕捉失敗狀態
    if ! python3 /app/garmin-tools-kit/garmin_tools.py --env-file /app/garmin-tools-kit/.env workout list > "$TMP_LIST" 2>/dev/null; then
        echo "[ERROR] 無法取得 workout 列表" >&2
        exit 1
    fi
    
    # 計算是否已存在該週課表
    num=$(grep -c "W${WEEK_NUM}" "$TMP_LIST")
    
    # 邏輯確認：如果是「不存在才要上傳」，使用 -eq 0
    if [ "${num}" -eq 0 ] ; then
        # 修正：移除高度危險的 -f 參數
        git add "${weekfile}" "${yamlfile}" "logs/SCHEDULE.md"
        
        # 檢查是否有實際變更
        if ! git diff-index --quiet HEAD --; then
            git commit -m "docs: update ${YEAR:-$(date +%Y)} W${WEEK_NUM} 課表"
        else
            echo "[INFO] 檔案無變更，跳過 Git Commit。"
        fi
        
        # 執行上傳
        if python3 /app/garmin-tools-kit/garmin_tools.py --env-file /app/garmin-tools-kit/.env workout upload "${yamlfile}"; then
            echo "${weekfile}"
        else
            echo "[ERROR] Workout 上傳失敗" >&2
            exit 1
        fi
    else
        echo "[INFO] W${WEEK_NUM} 課表已存在，跳過上傳。"
    fi
fi

exit 0
