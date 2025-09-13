EDINET大量保有報告書スクレイピング & LINE Bot

EDINETから大量保有報告書を自動取得し、LINE Botで通知・分析できるシステムです。

## 概要

このプロジェクトは2つの主要機能を提供します：

1. **EDINETスクレイピング機能**: 金融庁のEDINETから大量保有報告書を自動取得・解析
2. **LINE Bot機能**: 取得した報告書の通知、株みくじ機能、インタラクティブな分析

## プロジェクト構造

```
HoldingReport/
├── src/
│   ├── core/               # メインのスクレイピング機能
│   │   ├── main.py         # メイン実行ファイル
│   │   ├── hikariget.py    # EDINETからのデータ取得
│   │   ├── parser.py       # XBRLファイル解析
│   │   └── notifier.py     # LINE通知機能
│   ├── webhook/            # LINE Bot機能
│   │   ├── webhook_server.py  # Webhookサーバー
│   │   └── stock_fortune.json # 株みくじデータ
│   └── utils/              # 共通ユーティリティ
│       └── db.py           # データベース管理
├── data/
│   ├── downloads/          # EDINETダウンロードファイル
│   └── database/           # データベースファイル
├── config/
│   └── config.py           # 設定ファイル
├── run_scraper.py          # スクレイピング実行スクリプト
├── run_webhook.py          # Webhook サーバー実行スクリプト
├── pyproject.toml          # Poetry依存関係管理
├── .env.example            # 環境変数のサンプル
└── README.md              # このファイル
```

## セットアップ

### 1. Poetryのインストール

まず、Poetryをインストールします：

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Poetryのパスを設定します：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 2. 依存関係のインストール

```bash
poetry install
```

### 3. 環境変数の設定

`.env` ファイルを作成し、以下の変数を設定してください：

```env
# EDINET設定
EDINET_CODE=E35239  # 対象企業コード（デフォルト: 光通信）
DOWNLOAD_DIR=data/downloads  # ダウンロード先ディレクトリ

# LINE Bot設定
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_USER_ID=your_line_user_id

# データベース設定（オプション）
DB_PATH=data/database/edinet_reports.db
```

### 4. LINE Bot設定

1. [LINE Developers](https://developers.line.biz/)でBotを作成
2. Channel Access TokenとChannel Secretを取得
3. WebhookのURLを設定（例: `https://your-domain.com/callback`）

## 使用方法

### EDINETスクレイピングの実行

```bash
poetry run python run_scraper.py
```

または、Poetry環境内で実行：

```bash
poetry shell
python run_scraper.py
```

このコマンドは以下を実行します：
- 本日の大量保有報告書をEDINETから取得
- XBRLファイルを解析
- データベースに保存
- LINE通知を送信

### LINE Bot サーバーの起動

```bash
poetry run python run_webhook.py
```

または、Poetry環境内で実行：

```bash
poetry shell
python run_webhook.py
```

デフォルトでポート5000でサーバーが起動します。環境変数`PORT`で変更可能です。

### LINE Bot機能

LINE Botでは以下の機能が利用できます：

- **`光通信を分析`**: 最新の報告書を分析（クイックリプライで企業選択）
- **`今日の株みくじをする！`**: ランダムな銘柄をおすすめ
- **自動通知**: 新しい大量保有報告書が見つかった際の通知

## 主要機能

### 1. EDINETスクレイピング

- **自動取得**: 指定した企業の大量保有報告書を自動取得
- **XBRL解析**: XBRLファイルから企業情報、保有比率等を抽出
- **重複除去**: 既に処理済みの報告書は除外
- **エラーハンドリング**: ネットワークエラーや解析エラーの適切な処理

### 2. データベース管理

- **SQLite**: 軽量なSQLiteデータベースを使用
- **レポート管理**: 処理済み報告書の管理と検索
- **統計機能**: 企業別、期間別の統計情報

### 3. LINE Bot

- **インタラクティブ**: クイックリプライによる直感的な操作
- **株みくじ**: 業種や投資スタイルに応じた銘柄推奨
- **リアルタイム通知**: 新しい報告書の即座な通知

## 開発・カスタマイズ

### 対象企業の変更

`config/config.py` の `EDINET_CODE` を変更：

```python
EDINET_CODE = "E12345"  # 対象企業のEDINETコード
```

### 通知メッセージのカスタマイズ

`src/core/notifier.py` でメッセージ形式を変更可能です。

### 株みくじデータの更新

`src/webhook/stock_fortune.json` で推奨銘柄を管理できます。

## トラブルシューティング

### よくある問題

1. **LINE Bot が応答しない**
   - Webhook URLが正しく設定されているか確認
   - サーバーがポート5000で起動しているか確認

2. **EDINETからデータを取得できない**
   - インターネット接続を確認
   - EDINET_CODEが正しいか確認

3. **データベースエラー**
   - `data/database/` ディレクトリが存在するか確認
   - ファイルの書き込み権限を確認

### ログの確認

アプリケーションは詳細なログを出力します。問題が発生した場合は、コンソール出力を確認してください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグレポートや機能要求は、GitHubのIssuesでお願いします。プルリクエストも歓迎します。

## 注意事項

- EDINETの利用規約を遵守してください
- 大量のリクエストを送信する際は、適切な間隔を設けてください
- 本システムは情報提供のみを目的としており、投資判断の責任は利用者にあります
