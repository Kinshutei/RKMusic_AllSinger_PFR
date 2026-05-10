# RKMusic_AllSinger_PFR プロジェクト仕様メモ

## 自動実行の仕組み
- `auto_check.yml` は `workflow_dispatch`（手動トリガー）のみ設定
- **cron-job.org Console から定期的に workflow_dispatch を外部トリガーしている**
- GitHub Actions のスケジュール（cron）は使っていない
- 実行タイミングは cron-job.org 側で管理

## CHANNELS シークレット
- GitHub Actions シークレット（画面から値を確認不可）
- 内容は `channels_config.json`（ローカル）を参照
- 形式：`[{"name": "タレント名", "url": "YouTubeチャンネルURL"}, ...]`
- channel_id は `all_snapshots.json` にキャッシュされる（初回実行後）

## タレント追加手順
1. `channels_config.json` にエントリ追加
2. GitHub の `CHANNELS` シークレットを `channels_config.json` の内容で更新
3. `RKMusic 動画フラグ設定ツール_v1.00.html` の `TALENT_ORDER` に追加
4. cron-job.org または手動で workflow を実行 → `all_history_YYYY.json` に自動追加
5. Web ダッシュボードに自動で表示される（コード変更不要）

## Web ダッシュボードのタレント表示
- `all_history_YYYY.json` に存在するタレントを自動で一覧表示
- ハードコードなし。workflow 実行後に自動反映される

## ファイル対応表
| ファイル | 用途 |
|---|---|
| `auto_check.py` | データ収集スクリプト（GitHub Actions で実行） |
| `all_history_YYYY.json` | 全タレントの日別履歴（自動生成） |
| `all_snapshots.json` | 最新スナップショット・channel_id キャッシュ（自動生成） |
| `video_flags.json` | 動画/ライブ フラグ（フラグ設定ツールで編集） |
| `channels_config.json` | CHANNELS シークレットのローカルコピー |
| `RKMusic 動画フラグ設定ツール_v1.00.html` | フラグ編集ツール（スタンドアロンHTML） |
