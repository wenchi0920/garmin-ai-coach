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
echo "AI Coach 賽事庫資料完整性檢查報告"
echo "更新時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
printf "%-35s | %-18s | %-15s\n" "賽事名稱" "國家索引 (List)" "詳細分析 (Info)"
echo "-----------------------------------------------------------------------------"

IFS=$'\n'
for m in $(cat "$LIST_FILE"); 
do 
    # 清理潛在的隱形字元
    m=$(echo "$m" | tr -d '\r' | xargs)
    
    [ -z "$m" ] && continue

    # 檢查是否在各國 README.md (索引) 中出現過 (排除頂層 README.md)
    hasList=$(grep -l "${m}" */README.md 2>/dev/null)
    
    # 檢查是否在各國 info.md (詳情) 中出現過
    hasInfo=$(grep -l "${m}" */info.md 2>/dev/null)

    # 狀態標記
    list_status="[ - ]"
    info_status="[ - ]"
    prefix="  "
    
    if [ -n "$hasList" ]; then
        # 取得資料夾名稱 (國家碼)
        country=$(dirname "$hasList")
        list_status="[ OK ] ($country)"
    fi
    
    if [ -n "$hasInfo" ]; then
        info_status="[ OK ]"
    fi

    # 如果有任何一項缺失，加上警告標記
    if [[ "$list_status" == "[ - ]" || "$info_status" == "[ - ]" ]]; then    
        prefix="[!]"
	PROMPT="@README.md, **直接新增無須檢查有無重複** 新增  ${m} , 從「歷史背景」、「賽道技術分析」、「補給特色」與「教練專業評論」四個維度進行撰寫，確保每篇都在 100-200 字之間"
	echo "start add "${m}"
	gemini -y -p "$PROMPT" <<< "" && echo "✅ 更新成功！" || echo "❌ AI 處理失敗。"
	git-commit -a . 
    fi

    printf "%-35s | %-18s | %-15s\n" "$prefix $m" "$list_status" "$info_status"
done

echo "-----------------------------------------------------------------------------"
echo "提示: [!] 代表資料不完整 (缺索引或缺詳情)。"
echo "檢查結束。"
