# Discord bot

[こちらの方](https://github.com/watagashi0619/discord_bot)のbotソースをベースに動かないライブラリなどを変更したもの。

現状GPTBOTのみが稼働可能  

## 起動方法

`production`内で`docker compose up -d`でコンテナを立ち上げる。

## 開発する方法

`devenv`内で`docker compose up -d`でコンテナを立ち上げる。
あとはそのコンテナ内に入って(vscodeで)開発する。

## GPTbot (`gpt/gptbot.py`)

特定のチャンネルにChatGPTを常駐させます。

### command

- `gpt-hflush`: ChatGPTのチャット履歴を消去する
- `gpt-switch`: 言語モデルを切り替えます.初期設定は`gpt4o`
  - gpt-4-turbo
  - gpt-4-vision-preview
  - gpt-4o
- `gpt-system`: ChatGPTのキャラクター設定をする

## 設定

- `.env` の設定
    - `OPENAI_API_KEY`: ChatGPTキー
    - `DISCORD_BOT_TOKEN_GPT`: DiscordのChatGPT botトークン
    - `CHANNEL_ID_GPT`: GPT botが投稿するチャンネルのID
- logの設定
    - `pyproject.toml` にログの設定
        - `logs` フォルダに各ファイルの実行履歴が流れる
- gptチャットの性格付けの設定   
  - gptディレクトリ直下にsystemrole.txtを配置しその中に性格付設定を記載する。

## Directory structure

```
.
├── README.md
├── devEnv
│   ├── Dockerfile
│   ├── createuser.sh
│   └── docker-compose.yml
├── logs
├── production
│   ├── Dockerfile_gpt
│   └── docker-compose.yml
├── pyproject.toml
└── src
    ├── .gitignore
    ├── discord_bot
    │   └── gpt
    │       ├── .env
    │       ├── README.md
    │       ├── __init__.py
    │       ├── constants.py
    │       ├── gptbot.py
    │       ├── openaiUtil.py
    │       ├── poetry.lock
    │       ├── pyproject.toml
    │       └── systemrole.txt
    └── tests
        └── __init__.py

```