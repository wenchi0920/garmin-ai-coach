# 使用 Node.js 官方輕量鏡像
FROM node:20-slim

# 設定環境變數
ENV TZ=Asia/Taipei \
    DEBIAN_FRONTEND=noninteractive \
    NPM_CONFIG_PREFIX=/home/gemini/.npm-global \
    PATH=$PATH:/home/gemini/.npm-global/bin

# 1. 系統層級配置：安裝時區資料與基礎工具
RUN apt-get update && apt-get install -y \
    tzdata \
    procps \
    git \
    rsync \
    cron \
    vim python3 python3-pip \
    ca-certificates python3.11-venv \
    && ln -fs /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# 2. 建立 UID/GID = 1000 的 gemini 使用者
# 說明：官方 node 鏡像頉 UID 1000 的 node 用戶，必須先移除以避免衝突
RUN if getent passwd node; then userdel -r node; fi && \
    groupadd -g 1000 gemini && \
    useradd -l -u 1000 -g gemini -m -s /bin/bash gemini

# 3. 切換至 gemini 使用者並安裝 CLI
USER gemini
WORKDIR /home/gemini

copy . /home/gemini

RUN pip3 install -r requirements.txt --break-system-packages
RUN pip3 install pandas fitparse --break-system-packages


RUN mkdir -p /home/gemini/.npm-global && \
    npm install -g @google/gemini-cli

# 預設執行指令
ENTRYPOINT ["gemini"]
