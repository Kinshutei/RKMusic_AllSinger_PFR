# RKMusic AllSinger PFR

RKMusic 所属シンガー全員のYouTubeチャンネル統計・動画データを自動収集し、Webダッシュボードで閲覧できるシステムです。

## 対象シンガー（23名）

焔魔るり / HACHI / 瀬戸乃とと / 水瀬凪 / KMNZ / VESPERBELL / CULUA / NEUN / MEDA / CONA / IMI / XIDEN / ヨノ / MEMESIA / LEWNE / 羽緒 / Cil / 深影 / wouca / Diα / 妃玖 / HONK THE HORN / NUROJUNK

## 機能

### Webダッシュボード（`web/`）

- **Dashboard**
  - **ランキング**: 登録者数・総再生数・総コメント数のシンガー別前日比ランキング、動画/ショート/ライブ部門の再生数・高評価・コメントランキング
    - 集計日は「1日」（◀▶で1日ずつ）か「期間」（開始日〜終了日）で選べる。選べるのは 2026-04-01 から最新日まで
    - 期間中に公開された動画は0から数える。途中から加わったタレントは記録を始めた日から数える
  - **Statistics**: 全シンガー合計の登録者数・総再生数推移グラフ（累計/日次増加の切り替え対応）
- **シンガー個別ページ**: 動画/ショート/ライブタブ別の動画一覧、ソート・絞り込み、Statistics（動画別再生数推移グラフ）

### 自動データ収集（`auto_check.py`）

GitHub Actions により毎日 JST 00:00 に実行。

- 全シンガーのチャンネル統計（登録者数・総再生数・動画数）を取得
- 全動画の再生数・高評価数・コメント数・再生時間を取得
- `video_flags.json` を参照してコンテンツ種別を判定（最優先）
- 種別判定：チャンネルの「動画／ショート／ライブ」タブの再生リスト（UULF / UUSH / UULV）のどれに入っているかで決める。配信前・配信中は確定するまで毎日判定し直す
- データ保存先：`all_history_2026.json`（年別履歴）、`all_snapshots.json`（最新スナップショット）

### 動画フラグ設定ツール（`RKMusic 動画フラグ設定ツール_v2.00.html`）

スタンドアロンHTMLツール。自動判定の誤りを「動画／ショート／ライブ」の例外として手で決め、`video_flags.json` へ書き込む。

- GitHubから `channels_config.json` / `all_snapshots.json` / `video_flags.json` を読み込み（どれかが読めなければ保存できない）
- 一覧は「要確認（未確定・時間で仮判定・7分前後・自動判定と違う例外）」「新着」「タレント別」「例外」
- 保存するのは手で決めた例外だけ。自動判定の結果は書き出さない
- GitHub Contents API 経由で `video_flags.json` をプッシュ。GitHub Personal Access Token（`localStorage` 保存）で認証

## ファイル構成

```
.
├── auto_check.py                          # 自動データ収集スクリプト
├── backfill_duration.py                   # duration バックフィル用スクリプト（初回のみ）
├── all_history_2026.json                  # 全シンガーの日別履歴データ（自動生成）
├── all_snapshots.json                     # 最新スナップショット・チャンネルIDキャッシュ（自動生成）
├── video_flags.json                       # 動画コンテンツ種別フラグ
├── daily/YYYY-MM-DD.json                  # 日ごとの全動画の累計（日付指定用、2026-03-31〜。自動生成）
├── RKMusic 動画フラグ設定ツール_v2.00.html  # 動画フラグ設定スタンドアロンツール
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

1. `video_flags.json` に該当エントリがあれば最優先で適用（手で決めた例外だけを置く）
2. 配信前・配信中（長さ0）→ Pending。サイトには出さず、翌日以降に判定し直す
3. チャンネルの「動画／ショート／ライブ」タブの再生リストのどれに入っているか → Movie / Short / LiveArchive（確定）。
   再生リストのIDはチャンネルIDの先頭 `UC` を `UULF`（動画）/ `UUSH`（ショート）/ `UULV`（ライブ）に替えたもの。
   YouTube の公式文書には無い仕組みのため、読めないときは次の 4 で仮に決める
4. タブで分からないときだけ時間で仮判定（確定はせず、翌日タブで判定し直す）：
   3分以下は YouTube Shorts URL を確認 → Short（確認できなければ Pending）、それ以外は 7分以上 → LiveArchive、未満 → Movie

自動判定の結果は `all_snapshots.json` の `auto`、確定したかは `fixed` に残る。確定した動画は以後判定し直さない。

## データ仕様

- `all_history_2026.json` のキー構造：`{ [シンガー名]: { _channel_stats: { [日付]: {...} }, [動画ID]: { タイトル, 公開日, type, duration, records: { [日付]: { 再生数, 高評価数, コメント数 } } } } }`
- 正式データ期間：2026年4月1日〜
