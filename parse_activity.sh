#!/bin/bash 

# 不要覆蓋使用者的 PATH，否則會找不到像 gemini 這樣的指令
export PATH=$PATH:/usr/local/bin:/usr/local/sbin:/home/gemini/.npm-global/bin
export LANG=zh_TW.UTF-8

# 取得腳本所在目錄並切換進去
dname=$(/usr/bin/dirname "$0")
dname=$(/bin/readlink -f "$dname")
cd "${dname}"

# 設定日誌檔案
LOG_DIR="logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/parse_activity_$(date +%Y-%m-%d).log"

# 將所有輸出 (stdout & stderr) 同時輸出到終端機與日誌檔案
# 使用 { ... } 區塊來包裝原本的邏輯，或者直接使用 exec
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "========================================"
echo "執行時間: $(date '+%Y-%m-%d %H:%M:%S')"

echo "${PATH}"

fit_file="$1"
force_reanalyze="${2:-false}"

# 檢查參數
if [ -z "${fit_file}" ]; then
    echo "使用方式: $0 <fit_file> [force_reanalyze: true/false]"
    exit 1
fi

if [ ! -f "${fit_file}" ]; then
    echo "錯誤: 找不到檔案 ${fit_file}"
    exit 1
fi

base_name=$(basename "${fit_file}")
markdown_name="${base_name%.fit}.md"

# 提取年份與月份 (假設檔名格式為 activity_YYYY-MM-DD_...)
year=$(echo "${base_name}" | cut -d'_' -f2 | cut -d'-' -f1)
month=$(echo "${base_name}" | cut -d'_' -f2 | cut -d'-' -f2)

# 如果提取失敗，預設到 logs/activity
if [[ -z "$year" || -z "$month" ]]; then
    output_dir="logs/activity"
else
    output_dir="logs/activity/${year}/${month}"
fi

markdown_file="${output_dir}/${markdown_name}"

mkdir -p "${output_dir}"

# 分析邏輯
if [ ! -f "${markdown_file}" ] || [ "${force_reanalyze}" == "true" ]; then
    echo "正在分析 ${fit_file}..."
    python3 fit_analyzer.py "${fit_file}" > "${markdown_file}"
    
    if [ $? -eq 0 ]; then
        echo "✅ 分析完成: ${markdown_file}"
        
        # 嘗試呼叫 AI 分析 (靜默模式)
        if command -v gemini &> /dev/null; then
            PROMPT="@GEMINI.md 請幫我依照 \`${markdown_file}\` 的數據補全「教練建議與成效分析」與「改進建議」。"
            # 檢查 node 版本或 gemini 是否可用，避免輸出語法錯誤
            if gemini --version &> /dev/null; then
                echo "正在請求 AI Coach 深度建議..."
                gemini -y -p "$PROMPT" <<< "" &> /dev/null || echo "⚠️ AI 建議補全失敗，請手動執行補全。"
		#bash readme.sh
            else
                echo "💡 提示: 系統 gemini 指令版本不相容，請通知 AI Coach 手動為您分析報告。"
            fi
        else
            echo "💡 提示: 請手動請 AI Coach 補全 ${markdown_file} 的教練建議。"
        fi
    else
        echo "❌ 分析失敗。"
        exit 1
    fi
else
    echo "Markdown 檔案已存在: ${markdown_file}"
    
    # 額外檢查：如果檔案已存在，但內容包含預留字串，表示尚未經過 AI 分析
    if grep -q "(提供 1000 字 內文分析)" "${markdown_file}"; then
        echo "🔍 偵測到 AI 分析缺失，正在請求 AI Coach 補全建議..."
        
        if command -v gemini &> /dev/null; then
            PROMPT="@GEMINI.md 請幫我依照 \`${markdown_file}\` 的數據補全「教練建議與成效分析」與「改進建議」。"
            if gemini --version &> /dev/null; then
                gemini -y -p "$PROMPT" <<< "" &> /dev/null || echo "⚠️ AI 建議補全失敗。"
            else
                echo "💡 提示: 系統 gemini 指令版本不相容，請通知 AI Coach 手動補全。"
            fi
        else
            echo "💡 提示: 請手動請 AI Coach 補全 ${markdown_file} 的教練建議。"
        fi
    fi
fi

# 顯示摘要內容
echo "--- 報告摘要 ---"
cat "${markdown_file}"




