#!/bin/bash

# 確保路徑與語系正確
export PATH=$PATH:/usr/local/bin:/usr/local/sbin
export LANG=zh_TW.UTF-8

# 切換至專案根目錄
dname=$(/usr/bin/dirname "$0")
dname=$(/bin/readlink -f "$dname")
cd "${dname}"

# 1. 取得最新的一份課表 (本週執行中)
current_workout=$(ls logs/Workouts/Workouts-*.md 2>/dev/null | sort -V | tail -n 1)

# 2. 取得最近一個月的課表清單 (用於建立 README 連結)
recent_workouts=$(ls logs/Workouts/Workouts-*.md 2>/dev/null | sort -V | tail -n 4)

# 3. 取得最近 5 筆活動紀錄檔案路徑
recent_activities=$(ls logs/activity/activity_*.md 2>/dev/null | sort -V | tail -n 10)


healths=$(find data/ -type f |grep health|sort|tail -n 2)

# 4. 建構 Prompt
# 透過 @ 符號將關鍵檔案引入上下文，讓 AI Coach 擁有完整資訊
PROMPT="@GEMINI.md @logs/PERSON.md @${current_workout} @README.md
請依照以下要求，優化並更新目前的 README.md：

1. **系統功能描述**：強調科學化訓練、數據分析與自動化課表管理。
2. **健康摘要**： 根據最近兩天（${healths}）健康數據撰寫，並提供詳細的摘要 和 
3. **🎯 核心目標**：從 PERSON.md 提取雪梨馬拉松等近期關鍵賽事與目標成績。
4. **📊 最新健康摘要**：根據最新課表（${current_workout}）中的「上週回顧」與最近兩天的狀態撰寫。
5. **📅 本週計畫摘要**：摘要本週的訓練重點與目標。
6. **🔗 課表歷史紀錄**：
$(echo "${recent_workouts}" | sed 's/^/- /')

7. **🏃 最近 10 筆訓練摘要**：請參考以下檔案清單撰寫日期、項目與摘要：
$(echo "${recent_activities}" | sed 's/^/- /')

請確保內容專業、嚴謹，並符合跑者教練的口吻。
"

echo "----------------------------------------"
echo "🚀 準備更新 README.md"
echo "最新課表: ${current_workout}"
echo "----------------------------------------"

# 執行 AI 更新 (若環境支援 gemini 指令則自動執行)
if command -v gemini &> /dev/null; then
    gemini -y -p "$PROMPT" <<< "" &> /dev/null && echo "✅ README.md 已自動更新完成。" || echo "⚠️ AI 更新過程發生錯誤。"
else
    echo "提示：偵測不到 gemini 指令，請複製以下 Prompt 至 AI 介面執行："
    echo ""
    echo "${PROMPT}"
fi
