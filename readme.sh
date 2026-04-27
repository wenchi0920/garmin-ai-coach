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
LOG_FILE="${LOG_DIR}/readme_$(date +%Y-%m-%d).log"

# 將所有輸出 (stdout & stderr) 同時輸出到終端機與日誌檔案
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "========================================"
echo "README 更新時間: $(date '+%Y-%m-%d %H:%M:%S')"

# 2. 檔案路徑檢索
# 取得最新的一份課表 (本週計畫)
current_workout=$(ls logs/Workouts/*/Workouts-*.md 2>/dev/null | sort -V | tail -n 1)

# 取得最近一個月的課表清單 (建立連結)
recent_workouts_list=$(ls logs/Workouts/*/Workouts-*.md 2>/dev/null | sort -V | tail -n 10 |sort -r)

# 取得最近 5 筆活動紀錄檔案路徑
recent_activities_list=$(find logs/activity/ -name "activity_*.md" 2>/dev/null | sort -V | tail -n 10)

# 取得最近 2 天的健康數據內容
latest_health_files="data/health/health.txt"

# 3. 建構上下文參數 (用於 @ 標註)
CONTEXT_FILES="@GEMINI.md @logs/PERSON.md @README.md"
[ -n "$current_workout" ] && CONTEXT_FILES="$CONTEXT_FILES @$current_workout"

# 注入健康數據
if [ -f "${latest_health_files}" ]; then
    python3 analyze_health.py "${latest_health_files}" "${latest_health_files%.*}.tmp"
    [ -f "${latest_health_files%.*}.tmp" ] && CONTEXT_FILES="$CONTEXT_FILES @${latest_health_files%.*}.tmp"
fi

# 注入最近 5 筆活動紀錄，供 AI 讀取內容產生摘要
for f in $recent_activities_list; do
    CONTEXT_FILES="$CONTEXT_FILES @$f"
done

# 4. 建構 Prompt
today=$(date +%Y-%m-%d)
week_num=$(date +%V)
year=$(date +%Y)

PROMPT="$CONTEXT_FILES
你現在是一位資深的馬拉松教練 AI Coach。請根據提供附件內容，更新目前的 @README.md。

### 任務要求：
0. **執行方式**：請直接使用 \`write_file\` 工具更新 \`README.md\` 檔案內容，不要僅僅在終端機輸出文字。
1. **系統核心定位**：簡述系統如何結合數據分析與自動化課表，協助跑者達成目標。
2. **🎯 核心賽事目標**：從 PERSON.md 提取雪梨馬拉松等關鍵資訊與當前跑力 VDOT , 大約 300 字。
3. **📊 最新健康與恢復摘要**：
   - **今天日期 ${today}, 為 ${year} 第 W${week_num} 週 **
   - 整合最近兩天健康數據內容。
   - 提供健康摘要的 table。
   - 結合 $current_workout 中的「上週回顧」。
   - 提供專業的恢復建議（如傷勢進度、疲勞度評估）。
   - 大約 1000 字詳盡描述。
3.1 **關鍵生理指標監控表**: 
   - **欄位**：靜止心率 (RHR), 身體能量 (BB), 壓力指數 (Stress), 睡眠分數 (Sleep), HRV, 趨勢分析
   - 顯示 近 7 天 資料 
4. **📅 本週訓練重點**：摘要本週課表的核心目標。
   - 至少分為 5 大項目，包含：訓練重點、核心目標、關鍵課表、預期成效、執行建議。
   - 大約 1000 字詳盡描述。
5. **🔗 歷史課表紀錄**：
$(echo "${recent_workouts_list}" | sed 's/^/- /')

6. **🏃 最近 10 筆訓練摘要表**：
   - 請根據附件檔案內容，整理成表格。
   - 表格欄位：訓練日期, 項目, 距離, 配速, 摘要描述, 詳情路徑。
   - 「詳情路徑」請使用 link, 文字顯示 「詳情」 。
7. 教練寄語:提供大約 100字

請確保內容使用繁體中文，語氣專業、嚴謹且具鼓勵性。
"

echo "--------------------------------------------------"
echo "🚀 正在啟動 README.md 更新程序..."
echo "📍 參考課表: ${current_workout:-無}"
echo "📍 活動紀錄數: $(echo "$recent_activities_list" | wc -l)"
echo "--------------------------------------------------"

# 5. 執行更新
if gemini -v &> /dev/null; then

	num=0
	max=5
	old=$(md5sum README.md |awk '{print $1}')
	result="N"
	while [ $max -gt $num ] ;
	do
		echo "gemini 第 $((num+1)) 次 執行"
		gemini -y -p "$PROMPT" <<< "" && echo "✅ README.md 更新成功！" || echo "❌ AI 處理失敗。"

		new=$(md5sum README.md |awk '{print $1}')
		if [ "$new" != "$old" ] ; then
			result="Y"
			break
		fi
		num=$((num+1))
	done

	git commit -m "docs: update Workouts" logs/Workouts/*/*.md logs/Workouts/*/*.yaml

	if [ "$result" == "Y" ]; then
		echo "update README.md SUCCESS" | python3 send_msg.py
	else
		echo "update README.md ERROR" | python3 send_msg.py
	fi

else
    echo "提示：未偵測到 gemini 指令，請複製以下 Prompt 使用："
    echo "=================================================="
    echo "${PROMPT}"
    echo "=================================================="
fi
