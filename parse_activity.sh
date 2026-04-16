#!/bin/bash 

# --- 環境設定 ---
# 不要覆蓋使用者的 PATH，否則會找不到像 gemini 這樣的指令
export PATH=$PATH:/usr/local/bin:/usr/local/sbin:/home/gemini/.npm-global/bin
export LANG=zh_TW.UTF-8

# 取得腳本所在絕對目錄
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cd "${SCRIPT_DIR}"

# --- 日誌設定 ---
LOG_DIR="logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/parse_activity_$(date +%Y-%m-%d).log"

# 將所有輸出 (stdout & stderr) 同時輸出到終端機與日誌檔案
exec > >(tee -a "${LOG_FILE}") 2>&1

# --- 共用函數：AI 分析、Git 提交與通知 ---
# 參數: $1: markdown_file, $2: prompt_suffix (選填)
run_ai_coach_advice() {
    local md_file="$1"
    local suffix="$2"
    
    if ! command -v gemini &> /dev/null; then
        echo "💡 提示: 未安裝 gemini 指令，請手動補全 ${md_file} 的教練建議。"
        return 0
    fi

    # 檢查 node 版本或 gemini 是否可用，避免輸出語法錯誤
    if ! gemini --version &> /dev/null; then
        echo "💡 提示: 系統 gemini 指令版本不相容，請通知 AI Coach 手動為您分析報告。"
        return 0
    fi

    echo "正在請求 AI Coach 深度建議..."
    local prompt="@GEMINI.md 請幫我依照 \`${md_file}\` 的數據補全「教練建議與成效分析」與「改進建議」。${suffix}"
    
    if gemini -y -p "${prompt}" <<< "" &> /dev/null; then
        git add -f "${md_file}"
        git commit -m "docs: update training logs and workouts ${md_file}"
        cat "${md_file}" | python3 send_msg.py
    else
        echo "⚠️ AI 建議補全失敗，請手動執行補全。"
    fi
}

# --- 參數檢查 ---
fit_file="$1"
force_reanalyze="${2:-false}"

if [[ -z "${fit_file}" ]]; then
    echo "使用方式: $0 <fit_file> [force_reanalyze: true/false]"
    exit 1
fi

if [[ ! -f "${fit_file}" ]]; then
    echo "錯誤: 找不到檔案 ${fit_file}"
    exit 1
fi

echo "========================================"
echo "執行時間: $(date '+%Y-%m-%d %H:%M:%S')"
echo "${PATH}"

# --- 路徑解析 ---
base_name=$(basename "${fit_file}")
markdown_name="${base_name%.fit}.md"

# 提取年份、月份與完整日期 (假設檔名格式為 activity_YYYY-MM-DD_...)
# 使用 IFS 解析檔名
IFS='_' read -ra ADDR <<< "${base_name}"
if [[ ${#ADDR[@]} -ge 2 && ${ADDR[1]} =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    date_str="${ADDR[1]}"
    year="${date_str%%-*}"
    month=$(echo "${date_str}" | cut -d'-' -f2)
    output_dir="logs/activity/${year}/${month}/${date_str}"
else
    # 如果提取失敗，預設到 logs/activity
    output_dir="logs/activity"
fi

markdown_file="${output_dir}/${markdown_name}"
mkdir -p "${output_dir}"

# --- 主邏輯：分析與生成 ---
if [[ ! -f "${markdown_file}" || "${force_reanalyze}" == "true" ]]; then
    echo "正在分析 ${fit_file}..."
    if python3 fit_analyzer.py "${fit_file}" > "${markdown_file}"; then
        echo "✅ 分析完成: ${markdown_file}"
        
        # 初始分析時加入 schedule 參考
        run_ai_coach_advice "${markdown_file}" "並 參照 \`data/schedule.txt\` 參賽紀錄 對比賽"
    else
        echo "❌ 分析失敗。"
        exit 1
    fi
else
    echo "Markdown 檔案已存在: ${markdown_file}"
    
    # 額外檢查：如果檔案已存在，但內容包含預留字串，表示尚未經過 AI 分析
    if grep -q "(提供 1000 字 內文分析)" "${markdown_file}"; then
        echo "🔍 偵測到 AI 分析缺失，正在請求 AI Coach 補全建議..."
        run_ai_coach_advice "${markdown_file}" ""
    fi
fi
