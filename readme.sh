#!/bin/bash

# 1. 環境設定
export PATH=$PATH:/usr/local/bin:/usr/local/sbin
export LANG=zh_TW.UTF-8

# 切換至專案根目錄
dname=$(/usr/bin/dirname "$0")
dname=$(/bin/readlink -f "$dname")
cd "${dname}"

# 2. 檔案路徑檢索
# 取得最新的一份課表 (本週計畫)
current_workout=$(ls logs/Workouts/Workouts-*.md 2>/dev/null | sort -V | tail -n 1)

# 取得最近一個月的課表清單 (建立連結)
recent_workouts_list=$(ls logs/Workouts/Workouts-*.md 2>/dev/null | sort -V | tail -n 4)

# 取得最近 10 筆活動紀錄檔案路徑 (建立清單)
recent_activities_list=$(find logs/activity/ -name "activity_*.md" 2>/dev/null | sort -V | tail -n 10)

# 取得最近 2 天的健康數據內容 (注入上下文)
latest_health_files="data/health/health.txt"

# 3. 建構上下文參數 (用於 @ 標註)
# 我們只注入最關鍵的內容以節省 Token，其餘以清單呈現
CONTEXT_FILES="@GEMINI.md @logs/PERSON.md @README.md"
[ -n "$current_workout" ] && CONTEXT_FILES="$CONTEXT_FILES @$current_workout"
for f in $latest_health_files; do
    CONTEXT_FILES="$CONTEXT_FILES @$f"
done

# 4. 建構 Prompt
PROMPT="$CONTEXT_FILES
你現在是一位資深的馬拉松教練 AI Coach。請根據提供附件內容，優化並更新目前的 README.md。

### 任務要求：
1. **系統核心定位**：簡述系統如何結合數據分析與自動化課表，協助跑者達成目標。
2. **🎯 核心賽事目標**：從 PERSON.md 提取雪梨馬拉松等關鍵資訊與當前跑力 VDOT。
3. **📊 最新健康與恢復摘要**：
   - 整合最近兩天健康數據內容。
   - 結合 $current_workout 中的「上週回顧」。
   - 提供專業的恢復建議（如傷勢進度、疲勞度評估）。
4. **📅 本週訓練重點**：摘要本週課表的核心目標（如：Return to Run 測試、基礎耐力累積）。
5. **🔗 歷史課表紀錄**：
$(echo "${recent_workouts_list}" | sed 's/^/- /')

6. **🏃 最近 10 筆訓練摘要表**：
   - 請根據檔案名稱與內容，整理日期、項目與簡短成效摘要。
$(echo "${recent_activities_list}" | sed 's/^/- /')

請確保內容使用繁體中文，語氣專業、嚴謹且具鼓勵性。
"

echo "--------------------------------------------------"
echo "🚀 正在啟動 README.md 更新程序..."
echo "📍 參考課表: ${current_workout:-無}"
echo "📍 健康數據: $(echo $latest_health_files | xargs)"
echo "--------------------------------------------------"

# 5. 執行更新
if command -v gemini &> /dev/null; then
    gemini -y -p "$PROMPT" <<< "" &> /dev/null && echo "✅ README.md 更新成功！" || echo "❌ AI 處理失敗。"
else
    echo "提示：未偵測到 gemini 指令，請複製以下 Prompt 使用："
    echo "=================================================="
    echo "${PROMPT}"
    echo "=================================================="
fi
