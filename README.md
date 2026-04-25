# RKMusic AllSinger PFR

RKMusic 所属シンガー全員のYouTubeチャンネル統計・動画データを自動収集し、Webダッシュボードで閲覧できるシステムです。

## 対象シンガー（22名）

焔魔るり / HACHI / 瀬戸乃とと / 水瀬凪 / KMNZ / VESPERBELL / CULUA / NEUN / MEDA / CONA / IMI / XIDEN / ヨノ / LEWNE / 羽緒 / Cil / 深影 / wouca / Diα / 妃玖 / HONKTHEHORN / NUROJUNK

## 機能

### Webダッシュボード（`web/`）

- **Dashboard**
  - **ランキング**: 登録者数・総再生数・総コメント数のシンガー別前日比ランキング、動画/ショート/ライブ部門の再生数・高評価・コメントランキング
  - **Statistics**: 全シンガー合計の登録者数・総再生数推移グラフ（累計/日次増加の切り替え対応）
- **シンガー個別ページ**: 動画/ショート/ライブタブ別の動画一覧、ソート・絞り込み、Statistics（動画別再生数推移グラフ）

### 自動データ収集（`auto_check.py`）

GitHub Actions により毎日 JST 00:00 に実行。

- 全シンガーのチャンネル統計（登録者数・総再生数・動画数）を取得
- 全動画の再生数・高評価数・コメント数・再生時間を取得
- `video_flags.json` を参照してコンテンツ種別を判定（最優先）
- ショート判定：YouTube Shorts URL へのリダイレクト確認
- ライブアーカイブ判定：`liveBroadcastContent` / `liveStreamingDetails` を確認
- データ保存先：`all_history_2026.json`（年別履歴）、`all_snapshots.json`（最新スナップショット）

### 動画フラグ設定ツール（`RKMusic 動画フラグ設定ツール_v1.00.html`）

スタンドアロンHTMLツール。動画を「動画（Movie）」「ライブ（LiveArchive）」に手動分類し、`video_flags.json` へ書き込む。

- GitHubから `all_history_2026.json` / `video_flags.json` を読み込み
- 全シンガーの全非ショート動画の分類状態を一覧表示・編集
- GitHub Contents API 経由で `video_flags.json` をプッシュ
- GitHub Personal Access Token（`localStorage` 保存）で認証

## ファイル構成

```
.
├── auto_check.py                          # 自動データ収集スクリプト
├── backfill_duration.py                   # duration バックフィル用スクリプト（初回のみ）
├── all_history_2026.json                  # 全シンガーの日別履歴データ（自動生成）
├── all_snapshots.json                     # 最新スナップショット・チャンネルIDキャッシュ（自動生成）
├── video_flags.json                       # 動画コンテンツ種別フラグ
├── RKMusic 動画フラグ設定ツール_v1.00.html  # 動画フラグ設定スタンドアロンツール
├── requirements.txt                       # Python依存パッケージ
├── .github/
│   └── workflows/
│       └── auto_check.yml                # GitHub Actions設定（毎日JST 00:00実行）
└── web/                                   # Webダッシュボード（Vite + React + TypeScript）
    └── src/
        ├── components/
        │   ├── DashboardPage.tsx          # ダッシュボード（ランキング・Statistics）
        │   ├── TalentPage.tsx             # シンガー個別ページ
        │   └── Footer.tsx
        └── utils/
            └── data.ts                    # データ取得・集計ロジック
```

## GitHub Secrets

| Secret名 | 内容 |
|---|---|
| `YOUTUBE_API_KEY` | YouTube Data API v3 のAPIキー |
| `CHANNELS` | チャンネル設定JSON（name・url の配列） |

## コンテンツ種別判定ロジック

1. `video_flags.json` に該当エントリがあれば最優先で適用
2. YouTube Shorts URL へのリダイレクト確認 → Short
3. `liveBroadcastContent == completed` または `liveStreamingDetails` あり → LiveArchive（6分以上）
4. それ以外 → Movie

## データ仕様

- `all_history_2026.json` のキー構造：`{ [シンガー名]: { _channel_stats: { [日付]: {...} }, [動画ID]: { タイトル, 公開日, type, duration, records: { [日付]: { 再生数, 高評価数, コメント数 } } } } }`
- 正式データ期間：2026年4月1日〜
