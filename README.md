# YouTube チャンネル統計ダッシュボード

YouTubeチャンネルの統計を自動取得し、キリ番達成を通知するシステムです。

## 機能

- 📊 **自動データ取得**: 3時間ごとにチャンネル統計を自動取得
- 🎯 **キリ番検知**: 再生数のキリ番（5,000、10,000、50,000...）達成を自動検知
- 📧 **メール通知**: キリ番達成時に自動でメール送信
- 📈 **推移グラフ**: 登録者数・再生数の推移を可視化
- 🌐 **Webダッシュボード**: Streamlit Cloudで24時間アクセス可能

## セットアップ手順

### 1. GitHubリポジトリの作成

1. GitHubにログイン
2. 新しいリポジトリを作成（例：`youtube-stats`）
3. このプロジェクトのファイルをアップロード

### 2. GitHub Secretsの設定

リポジトリの `Settings` → `Secrets and variables` → `Actions` → `New repository secret` で以下を設定：

- `YOUTUBE_API_KEY`: YouTube Data API v3のAPIキー
- `CHANNEL_URL`: 監視するチャンネルのURL（例：`https://www.youtube.com/@Mikage_RKMusic`）
- `EMAIL_ENABLED`: メール通知の有効/無効（`true` または `false`）
- `SENDER_EMAIL`: 送信元Gmailアドレス
- `SENDER_PASSWORD`: Gmailアプリパスワード（16桁）
- `RECEIVER_EMAIL`: 通知先メールアドレス

### 3. GitHub Actionsの有効化

1. リポジトリの `Actions` タブを開く
2. ワークフローを有効化
3. 初回は手動で `Run workflow` をクリックして実行

### 4. Streamlit Cloudへのデプロイ

1. [Streamlit Cloud](https://streamlit.io/cloud) にサインアップ
2. GitHubアカウントと連携
3. `New app` をクリック
4. リポジトリと `youtube_dashboard.py` を選択
5. デプロイ

## ファイル構成

```
.
├── auto_check.py              # 自動実行スクリプト
├── youtube_dashboard.py       # Streamlitダッシュボード
├── requirements.txt           # 依存パッケージ
├── video_history.json         # 動画データ履歴（自動生成）
├── check_log.json            # 実行ログ（自動生成）
├── .github/
│   └── workflows/
│       └── auto_check.yml    # GitHub Actions設定
├── .gitignore                # Git除外設定
└── README.md                 # このファイル
```

## 実行頻度

- デフォルト: 3時間ごと（UTC時刻: 0, 3, 6, 9, 12, 15, 18, 21時）
- 変更方法: `.github/workflows/auto_check.yml` の `cron` を編集

### Cron例

```yaml
# 6時間ごと
- cron: '0 */6 * * *'

# 1日4回（6時間間隔）
- cron: '0 0,6,12,18 * * *'

# 毎日正午のみ
- cron: '0 12 * * *'
```

## YouTube Data API クォータ

- 無料枠: 10,000ユニット/日
- 1回の実行: 約7ユニット
- 3時間ごと実行: 約56ユニット/日（余裕あり）

## トラブルシューティング

### GitHub Actionsが実行されない

- `Actions` タブでワークフローが有効になっているか確認
- GitHub Secretsが正しく設定されているか確認

### メール通知が届かない

- Gmailの2段階認証が有効になっているか確認
- アプリパスワードが正しいか確認
- `EMAIL_ENABLED` が `true` になっているか確認

### ダッシュボードにデータが表示されない

- 初回の自動実行が完了するまで待つ
- GitHubリポジトリに `video_history.json` が作成されているか確認

## ライセンス

MIT License

## 作成者

Ayumi (Kinshutei)
