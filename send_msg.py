import sys
import requests
import os
import re

def load_dotenv(dot_env_path=".env"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    potential_paths = [dot_env_path, os.path.join(script_dir, dot_env_path)]
    for path in potential_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"): continue
                        if "=" in line:
                            key, value = line.split("=", 1)
                            os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))
                break
            except: pass

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        sys.stderr.write("❌ 錯誤: 缺少設定。\n")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Telegram 單則訊息上限為 4096 字元
    if len(message) > 4000:
        message = message[:4000] + "\n\n...(訊息已截斷)"

    # 第一階段：嘗試使用 MarkdownV2 (支援表格但語法更嚴格)
    # 但為求最穩，我們維持原來的 Markdown (V1)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        
        # 如果報錯 (400)，表示 Markdown 解析失敗
        if response.status_code == 400:
            sys.stderr.write("⚠️ 偵測到格式解析失敗，正在以「純文字」模式重發...\n")
            # 移除所有 Markdown 標記，將其變為純文字
            payload.pop("parse_mode", None)
            
            # 針對表格內容做簡單對齊優化（可選）
            # clean_msg = message.replace("|", " ").replace("-", "-")
            payload["text"] = message 
            
            response = requests.post(url, data=payload, timeout=10)
            
        response.raise_for_status()
        print("✅ Telegram 訊息發送成功！")
        return True
    except Exception as e:
        sys.stderr.write(f"❌ Telegram 發送失敗: {e}\n")
        if hasattr(e, 'response') and e.response is not None:
            sys.stderr.write(f"   API 回傳內容: {e.response.text}\n")
        return False

if __name__ == "__main__":
    if not sys.stdin.isatty():
        msg = sys.stdin.read()
    elif len(sys.argv) >= 2:
        msg = sys.argv[1]
    else:
        sys.exit(1)
    
    if msg.strip():
        if not send_telegram_message(msg):
            sys.exit(1)
