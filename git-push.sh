#!/bin/bash 

# 不要覆蓋使用者的 PATH，否則會找不到像 gemini 這樣的指令
export PATH=$PATH:/usr/local/bin:/usr/local/sbin
export LANG=zh_TW.UTF-8

# 取得腳本所在目錄並切換進去
dname=$(/usr/bin/dirname "$0")
dname=$(/bin/readlink -f "$dname")
cd "${dname}"

git add -f /app/logs/Workouts/*.md /app/logs/Workouts/*.yaml /app/logs/activity/*.md
git commit --auto /app/logs/Workouts/*.md /app/logs/Workouts/*.yaml /app/logs/activity/*.md


