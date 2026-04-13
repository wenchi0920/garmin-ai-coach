#!/bin/bash

# 1. 環境設定
export PATH=$PATH:/usr/local/bin:/usr/local/sbin
export PATH=$PATH:/usr/local/bin:/usr/local/sbin:/home/gemini/.npm-global/bin
export LANG=zh_TW.UTF-8

# 切換至專案根目錄
dname=$(/usr/bin/dirname "$0")
dname=$(/bin/readlink -f "$dname")
cd "${dname}"


pip3 install -r /app/requirements.txt --break-system-packages

git config --global user.name wenchi
git config --global user.email wenchi0920@gmail.com
git config --global credential.helper store

curl "https://raw.githubusercontent.com/wenchi0920/ai-tools-kit/refs/heads/main/tools/git-commit" > /usr/local/bin/git-commit
chmod a+x /usr/local/bin/git-commit


# 檢查是否為 production 環境 (從 .env 讀取或檢查是否存在 production 字樣)
if [ -f .env ] && grep -qi "production" .env; then
    echo "環境為 production，正在啟動 cron 服務..."
    /etc/init.d/cron restart
    crontab /app/crontab.txt
else
    echo "not production"
fi

su gemini

/bin/bash
# tail -f /dev/null

