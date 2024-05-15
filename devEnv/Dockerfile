# Debianイメージをベースとする
FROM debian:bookworm-slim

ARG UID=1000
ARG GID=1000


# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    curl \
    git \
    vim \
    zip \
    unzip \
    build-essential \
    pipx \
    gosu \
    python3-dev \
    libsqlite3-dev\
    && rm -rf /var/lib/apt/lists/*

COPY createuser.sh /usr/bin/createuser.sh
RUN chmod +x /usr/bin/createuser.sh
ENTRYPOINT ["/usr/bin/createuser.sh"]

# 作業ディレクトリの設定
WORKDIR /app

# コンテナ起動時に実行されるコマンド
CMD pipx ensurepath && pipx install poetry && exec bash

