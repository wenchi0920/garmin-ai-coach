#!/bin/bash

# 1. 環境設定
export PATH=$PATH:/usr/local/bin:/usr/local/sbin
export PATH=$PATH:/usr/local/bin:/usr/local/sbin:/home/gemini/.npm-global/bin
export LANG=zh_TW.UTF-8

# 切換至專案根目錄
dname=$(/usr/bin/dirname "$0")
dname=$(/bin/readlink -f "$dname")
cd "${dname}"

LIST_FILE="list.txt"

if [ ! -f "$LIST_FILE" ]; then
    echo "錯誤: 找不到 $LIST_FILE"
    exit 1
fi

echo "========================================"
echo "AI Coach 賽事庫資料自動補全與檢查"
echo "更新時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
printf "%-35s | %-18s | %-15s\n" "賽事名稱" "國家索引 (List)" "詳細分析 (Info)"
echo "-----------------------------------------------------------------------------"

# 隨機排序 list.txt 以分散處理壓力
IFS=$'\n'
for m in $(cat "$LIST_FILE" | sort -R); 
do 
    # 清理潛在的隱形字元
    m=$(echo "$m" | tr -d '\r' | xargs)
    [ -z "$m" ] && continue

    # 檢查是否在各國 README.md (索引) 中出現過 (排除頂層 README.md)
    hasList=$(grep -Fl "${m}" */README.md 2>/dev/null)
    
    # 檢查是否在各國 info.md (詳情) 中出現過
    hasInfo=$(grep -Fl "${m}" */info.md 2>/dev/null)

    # 狀態標記
    list_status="[ - ]"
    info_status="[ - ]"
    prefix="  "
    country=""
    
    if [ -n "$hasList" ]; then
        country=$(dirname "$hasList")
        list_status="[ OK ] ($country)"
    fi
    
    if [ -n "$hasInfo" ]; then
        [ -z "$country" ] && country=$(dirname "$hasInfo")
        info_status="[ OK ]"
    fi

    # 如果有任何一項缺失，啟動 AI 補全
    if [[ "$list_status" == "[ - ]" || "$info_status" == "[ - ]" ]]; then
        prefix="[!]"
        echo "-----------------------------------------------------------------------------"
        echo "檢測到缺少資料: ${m}"
        
        # 建立 AI Prompt
        PROMPT="您是具有 20 年馬拉松經驗的 AI Coach。請針對賽事「${m}」進行專業資料補全：
1. **定位**：判斷該賽事所屬國家的 ISO 代碼 (如 twn, jpn, usa)。若目錄不存在請依 \`Marathon/GEMINI.md\` 規範建立。
2. **README.md (索引)**：在該國 README.md 表格新增一列。包含：月份、中文名、英文名、特色、認證、詳情連結 (\`info.md#錨點\`)。**重要：新增後必須確保表格按月份 (1-12) 重新排序**。
3. **info.md (詳情)**：在末尾新增四段式結構：### [中文名] ([英文名])。包含「1. 歷史背景」、「2. 賽道技術分析」(含配速策略)、「3. 補給特色」、「4. 教練專業評論」(含 PB 潛力、LSD 定位)。
4. **專業要求**：內容約 100-200 字，語氣科學嚴謹，必須使用術語如 PB, BQ, LSD, RPE, 負分割 (Negative Split), 離心收縮。
5. **安全原則**：遵循「最小異動原則」，僅 Additive Changes，嚴禁更動或刪除其他賽事。
6. **執行**：請直接呼叫工具修改檔案，確保 Markdown 表格對齊與格式正確。"

        echo "正在啟動 AI 處理 ${m}..."
        if gemini -y -p "$PROMPT" <<< ""; then
            echo "✅ AI 更新成功: ${m}"
            # 提交並推播
            git add .
            git commit -m "auto: update marathon data for ${m}"
            git push && echo "🚀 Git Push 成功" || echo "⚠️ Git Push 失敗 (請檢查權限)"
            
            # 重新檢查狀態以更新報表
            hasList=$(grep -Fl "${m}" */README.md 2>/dev/null)
            hasInfo=$(grep -Fl "${m}" */info.md 2>/dev/null)
            [ -n "$hasList" ] && list_status="[ OK ] ($(dirname $hasList))"
            [ -n "$hasInfo" ] && info_status="[ OK ]"
            prefix="  "
        else
            echo "❌ AI 處理失敗: ${m}"
        fi
        
        echo "冷卻中 (60s)..."
        sleep 60
    fi

    printf "%-35s | %-18s | %-15s\n" "$prefix $m" "$list_status" "$info_status"
done

echo "-----------------------------------------------------------------------------"
echo "提示: [!] 代表資料已補全或原本不完整。"
echo "檢查結束。"
