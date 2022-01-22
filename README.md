# アプリについて
Salesforce から 4時間に一度、[同期用シート](https://docs.google.com/spreadsheets/d/13WXWBeHL_nd0BYp98-L3S-eKrCjGsXd8lrBzPNWVMzs/edit#gid=2110653188) にデータ同期を行っている。  
このデータを Pandas を用いて加工し、[出力用シート](https://docs.google.com/spreadsheets/d/19x_5wEIvBYMADexOvKA5et5qQ2brhL6TsdUitvajIX8/edit?usp=sharing) に書き込む。  

一連の処理は、AWS Lambda 上で動作し、AWS Event Bridge で 6時間ごとに行うよう設定している。

## ディレクトリ構成
```
.
├── Dockerfile
├── Makefile
├── README.md
├── app            # アプリケーション本体
│   ├── credentials.json.example
│   └── lambda.py
├── app.py         # cdk のルート
├── cdk.json
├── cdk.out
├── deploy.sh      # デプロイコマンド
├── requirements.txt
└── stacks         # インフラの設定
    ├── __init__.py
    ├── common.py
    └── lambda_stack.py
```

# 開発環境の準備

## aws-cli, aws-cdk をインストール
AWS のインフラ設定を Python から制御できる aws-cdk を使用。
```
# aws-cli
% brew install awscli
% aws --version


# aws-cdk
% npm install -g aws-cdk
% cdk --version
% cdk ls
```

## 環境構築
以下のコマンドで venv を作成し、その中にライブラリをインストールする。  
詳細は `Makefile` を参照。
```
% make init
```

## example ファイルをコピー
```
% cp .env.example .env
% cp app/credentials.json.example app/credentials.json
```
作成したファイルに、以下 URL の内容を貼り付ける。  
https://docs.google.com/document/d/1RepVn2j4NE9-rndDrs0NNLUeof8ojeW2JgE66q-QOcg/edit?usp=sharing

# CI / CD
## 開発 & デプロイ
- `app/lambda.py` を編集 (必要に応じてモジュールを分けても OK)
- `make deploy`
```
# app/ 配下を docker image としてビルドし、AWS ECR へプッシュする

% make deploy
```

## インフラ & デプロイ

- AWS SSO のサインイン画面へいき、アカウントをクリック
- `Command line or programmatic access` をクリック
- `Option 1: Set AWS environment variables` の中身をコピー
- 自身のターミナルに貼り付ける
- `stacks/lambda_stack.py` を編集する
- `cdk deploy`
```
# stacks/ 配下の lambda_stack.py の内容を、AWS Lambda, IAM, AWS ECR, AWS EventBridge へ反映させる

% cdk deploy
```
