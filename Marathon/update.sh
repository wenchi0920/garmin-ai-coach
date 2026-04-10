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
        PROMPT="您是 AI Coach。請針對賽事「${m}」執行以下任務：
1. 判斷該賽事所屬國家。
2. 若該國資料夾（如 twn/, jpn/）不存在，請先建立。
3. 依照 @GEMINI.md 規範：
   - 在該國的 README.md 表格中新增一列（無須檢查重複，嚴禁刪除既有內容）。
   - 在該國的 info.md 中，從「歷史背景」、「賽道技術分析」、「補給特色」與「教練專業評論」四個維度撰寫詳情。
   - **嚴禁修改跟 ${m} 不相關的 賽事資料**
4. 確保 ${m} 每篇詳情在 100-200 字之間，語氣專業且科學。
5. **直接執行檔案修改操作，不要只給建議**。"

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
