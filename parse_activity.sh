#!/bin/bash 

export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
export LANG=zh_TW.UTF-8

# 取得腳本所在目錄並切換進去
dname=$(/usr/bin/dirname "$0")
dname=$(/bin/readlink -f "$dname")
cd "${dname}"

fit_file="$1"

# 檢查參數是否存在
if [ -z "${fit_file}" ]; then
    echo "使用方式: $0 <fit_file>"
    exit 1
fi

# 檢查檔案是否存在
if [ ! -f "${fit_file}" ]; then
    echo "錯誤: 找不到檔案 ${fit_file}"
    exit 1
fi

# 將 .fit 替換為 .md
markdown_file="${fit_file%.fit}.md"

# 如果 md 檔不存在則執行分析
if [ ! -f "${markdown_file}" ]; then
    echo "正在分析 ${fit_file}..."
    python3 fit_analyzer.py "${fit_file}" > "${markdown_file}"
    echo "分析完成，結果儲存至 ${markdown_file}"
    
    #
    PROMPT="請幫我 依照訓練的結果  `${markdown_file}` 補上 教練建議與成效分析/改進建議 "
    gemini -y -p "$PROMPT" <<< "" || echo ""
    
else
    echo "Markdown 檔案已存在: ${markdown_file}"
fi


