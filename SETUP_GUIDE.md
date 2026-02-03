# 📝 詳細セットアップガイド

## ステップ1: GitHubリポジトリの作成

### 1-1. GitHubにアクセス
- https://github.com にアクセス
- アカウント（Kinshutei）でログイン

### 1-2. 新規リポジトリ作成
1. 右上の「+」→「New repository」をクリック
2. Repository name: `youtube-stats`（好きな名前でOK）
3. Public または Private を選択（Privateがおすすめ）
4. 「Create repository」をクリック

---

## ステップ2: ファイルのアップロード

### 2-1. ファイル構造
以下のファイルをGitHubにアップロードします：

```
youtube-stats/
├── auto_check.py
├── youtube_dashboard.py
├── requirements.txt
├── .gitignore
├── README.md
└── .github/
    └── workflows/
        └── auto_check.yml
```

### 2-2. アップロード方法（Web UIを使用）

#### 通常ファイルのアップロード
1. GitHubのリポジトリページで「Add file」→「Upload files」
2. 以下のファイルをドラッグ＆ドロップ：
   - `auto_check.py`
   - `youtube_dashboard.py`
   - `requirements.txt`
   - `.gitignore`
   - `README.md`
3. 「Commit changes」をクリック

#### .github/workflows/auto_check.ymlのアップロード
1. リポジトリのトップページで「Add file」→「Create new file」
2. ファイル名に `.github/workflows/auto_check.yml` と入力
   - フォルダも自動で作成されます
3. ダウンロードした `auto_check.yml` の内容をコピペ
4. 「Commit new file」をクリック

---

## ステップ3: GitHub Secretsの設定

### 3-1. Secrets画面を開く
1. リポジトリの「Settings」タブをクリック
2. 左メニューから「Secrets and variables」→「Actions」を選択
3. 「New repository secret」ボタンをクリック

### 3-2. 以下の6つのSecretを作成

#### Secret 1: YOUTUBE_API_KEY
- Name: `YOUTUBE_API_KEY`
- Value: `あなたのYouTube Data APIキー`

#### Secret 2: CHANNEL_URL
- Name: `CHANNEL_URL`
- Value: `https://www.youtube.com/@Mikage_RKMusic`

#### Secret 3: EMAIL_ENABLED
- Name: `EMAIL_ENABLED`
- Value: `true`（メール通知を使う場合）または `false`

#### Secret 4: SENDER_EMAIL
- Name: `SENDER_EMAIL`
- Value: `あなたのGmailアドレス@gmail.com`

#### Secret 5: SENDER_PASSWORD
- Name: `SENDER_PASSWORD`
- Value: `Gmailアプリパスワード16桁`

#### Secret 6: RECEIVER_EMAIL
- Name: `RECEIVER_EMAIL`
- Value: `通知を受け取るメールアドレス`

---

## ステップ4: GitHub Actionsの有効化と初回実行

### 4-1. Actionsタブを開く
1. リポジトリの「Actions」タブをクリック
2. ワークフローが表示される

### 4-2. 初回手動実行
1. 左メニューから「YouTube Stats Auto Check」を選択
2. 「Run workflow」ボタンをクリック
3. 「Run workflow」を再度クリックして実行開始

### 4-3. 実行結果の確認
1. 実行が始まると、進行状況が表示されます
2. 完了すると緑色のチェックマークが付きます
3. クリックして詳細ログを確認できます

### 4-4. 自動生成ファイルの確認
初回実行後、リポジトリに以下のファイルが自動作成されます：
- `video_history.json` - 動画データ履歴
- `check_log.json` - 実行ログ

---

## ステップ5: Streamlit Cloudへのデプロイ

### 5-1. Streamlit Cloudにサインアップ
1. https://streamlit.io/cloud にアクセス
2. 「Sign up」をクリック
3. 「Continue with GitHub」でGitHubアカウント連携

### 5-2. アプリのデプロイ
1. 「New app」をクリック
2. 設定：
   - Repository: `Kinshutei/youtube-stats`
   - Branch: `main`
   - Main file path: `youtube_dashboard.py`
3. 「Deploy!」をクリック

### 5-3. デプロイ完了
- 数分でデプロイ完了
- URLが発行されます（例: `https://kinshutei-youtube-stats.streamlit.app`）
- このURLをブックマーク！

---

## ステップ6: 動作確認

### 6-1. GitHub Actionsが自動実行されているか確認
- 3時間後にもう一度「Actions」タブを確認
- 自動実行されていればOK

### 6-2. ダッシュボードでデータを確認
- Streamlit CloudのURLにアクセス
- データが表示されていればOK
- 初回は「データを取得中」と表示される場合あり

### 6-3. メール通知のテスト
- 数日待ってキリ番達成を待つ
- または、`video_history.json`を手動編集してテスト

---

## トラブルシューティング

### GitHub Actionsでエラーが出る
- Secretsが正しく設定されているか確認
- YouTube API キーが有効か確認
- ログの詳細を確認

### ダッシュボードにデータが表示されない
- GitHub Actionsが最低1回実行されたか確認
- `video_history.json`がリポジトリに作成されているか確認
- Streamlit Cloudのログを確認

### メールが届かない
- `EMAIL_ENABLED`が`true`になっているか確認
- Gmailアプリパスワードが正しいか確認
- Gmail側で送信制限がかかっていないか確認

---

## 完了！

これで全てのセットアップが完了しました。

- ✅ 3時間ごとに自動でデータ取得
- ✅ キリ番達成時に自動メール通知
- ✅ Webダッシュボードで24時間いつでも確認可能

お疲れ様でした！🎉
