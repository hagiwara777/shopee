# ──────────────────────────────────────
# 1. ベースイメージを指定
#    → ここまでで「Python 3.12 が使える状態」です
FROM mcr.microsoft.com/vscode/devcontainers/python:3.12-bullseye

# ──────────────────────────────────────
# 2. 追加ツールと Node.js の元情報をダウンロード
#    a) システムのソフト一覧を最新にする
#    b) curl という“ファイルをダウンロードする道具”を入れる
#    c) NodeSource という配布サイトから
#       「Node.js 22.x を入れていいよ」という設定を読み込む
RUN apt-get update \
  && apt-get install -y --no-install-recommends git curl \
  && curl -fsSL https://deb.nodesource.com/setup_22.x | bash -

# ──────────────────────────────────────
# 3. いよいよ Node.js と npm をインストール
#    → Node.js（プログラム本体）と npm（ライブラリ管理ツール）が入る
RUN apt-get install -y --no-install-recommends nodejs \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# ──────────────────────────────────────
# 4. 作業フォルダとユーザー切り替え
WORKDIR /workspace
USER vscode
