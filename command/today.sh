#!/bin/bash

dname=$(/usr/bin/dirname $0)
dname=$(/bin/readlink -f "$dname")

cd "${dname}/../"

# 1. 設定日期與週次
TODAY=$(date +"%Y-%m-%d")
TOMORROW=$(date -d "tomorrow" +"%Y-%m-%d")
WEEK_NUM=$(date +"%V")
YEAR=$(date +"%Y")

#	for test
TODAY="2026-03-14"

echo "--- [AI Coach] 數據處理中: $TODAY ---"

# 2. 自動分析今天的 .fit 檔案
FIT_FILES=$(ls data/activity/activity_${TODAY}*.fit 2>/dev/null)
if [ -n "$FIT_FILES" ]; then
    echo "[Step 1] 發現今日活動紀錄，開始分析..."
#    python3 "${dname}/../fit_analyzer.py" "${FIT_FILES}"
else
    echo "[Step 1] 今日尚未發現新的 .fit 活動紀錄。"
fi

for f in $(ls data/activity/activity_${TODAY}*.md 2>/dev/null) ; 
do 
	echo "${f}"
done


exit;

# 3. 尋找當週課表檔案
# 搜尋包含當週週次的 Workouts 檔案
WORKOUT_FILE=$(ls logs/Workouts/Workouts-*-W${WEEK_NUM}.md 2>/dev/null | head -n 1)

if [ -z "$WORKOUT_FILE" ]; then
    echo "[Error] 找不到本週 (W${WEEK_NUM}) 的課表檔案。"
    exit 1
fi

echo "[Step 2] 讀取課表: $(basename $WORKOUT_FILE)"

# 4. 擷取今天與明天的課表內容 (從 Markdown 表格擷取)
echo ""
echo "--- 今日與明日計畫 ---"

# 提取今天的行
TODAY_PLAN=$(grep "| ${TODAY:5}" "$WORKOUT_FILE")
if [ -n "$TODAY_PLAN" ]; then
    echo "📅 今天 ($TODAY):"
    echo "$TODAY_PLAN" | awk -F'|' '{print "   - 內容: "$3"\n   - 目的: "$4"\n   - 狀態: "$5}'
else
    echo "📅 今天 ($TODAY): 課表中無紀錄"
fi

echo ""

# 提取明天的行
TOMORROW_PLAN=$(grep "| ${TOMORROW:5}" "$WORKOUT_FILE")
if [ -n "$TOMORROW_PLAN" ]; then
    echo "📅 明天 ($TOMORROW):"
    echo "$TOMORROW_PLAN" | awk -F'|' '{print "   - 內容: "$3"\n   - 目的: "$4"\n   - 狀態: "$5}'
else
    echo "📅 明天 ($TOMORROW): 課表中無紀錄"
fi

# 5. 教練提點 (根據 PERSON.md 的目標)
echo ""
echo "--- 教練提示 ---"
if [[ "$TODAY_PLAN" == *"休息"* ]]; then
    echo "💡 休息是為了走更長遠的路。請確保傷口通風乾燥。"
else
    echo "💡 執行課表前，請再次確認左腳大拇指是否有疼痛感。"
fi
echo "--- [End of Report] ---"
