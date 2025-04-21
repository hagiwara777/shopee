# ベースに Python 3.12 + Node.js 18 LTS が入ったイメージを利用
FROM mcr.microsoft.com/vscode/devcontainers/python:3.12-bullseye

# 必要なツール類を追加インストール（例：git, curl）
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ
WORKDIR /workspace

# Node.js 18 を追加（Dev Container イメージには入っていない場合）
ARG INSTALL_NODE="true"
RUN if [ "$INSTALL_NODE" = "true" ]; then su vscode -c "npm install -g npm@9"; fi

# デフォルトユーザーを vscode ユーザーに
USER vscode
