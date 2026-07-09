#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube チャンネル統計 自動チェックスクリプト
GitHub Actionsで定期実行される（JST 00:00）

- 全アーティストのチャンネル統計・動画データを収集
- Movie/Short/LiveArchive自動判別（並列処理）
- video_flags.json による例外設定対応
- チャンネルIDキャッシュで無駄なAPIコールを削減
- データ保存先:
    all_snapshots.json            : 全アーティストの最新スナップショット
    history_{channel_name}.json   : チャンネルごとの動画履歴（日次集約済み）
"""

import os
import sys
import json
import requests
import threading
import tempfile
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import isodate

# ----------------------------------------------------------------
# 設定
# ----------------------------------------------------------------
API_KEY = os.environ.get('YOUTUBE_API_KEY')
CHANNELS_JSON = os.environ.get('CHANNELS', '[]')

try:
    CHANNELS = json.loads(CHANNELS_JSON)
except Exception:
    CHANNELS = []

MAX_WORKERS = 10       # Short判定の同時並列数
CHANNEL_WORKERS = 3   # チャンネル処理の同時並列数

SNAPSHOTS_FILE = 'all_snapshots.json'

# スナップショット書き込みの排他制御用ロック（並列処理による競合防止）
_snapshot_lock = threading.Lock()

def history_file(channel_name):
    return f'history_{channel_name}.json'

# ----------------------------------------------------------------
# ファイル読み書き
# ----------------------------------------------------------------

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f'⚠️  {path} 読み込みエラー: {e}')
    return default

def save_json(path, data, indent=2):
    dir_ = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=dir_, delete=False, suffix='.tmp') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        tmp_path = f.name
    os.replace(tmp_path, path)

# ----------------------------------------------------------------
# 例外設定
# ----------------------------------------------------------------

def load_overrides():
    overrides = load_json('video_flags.json', {})
    total = sum(len(v) for v in overrides.values())
    if total:
        print(f'✓ フラグ設定を読み込みました: {total}件')
    return overrides

# ----------------------------------------------------------------
# APIリトライ
# ----------------------------------------------------------------

def execute_with_retry(request, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            return request.execute()
        except HttpError as e:
            if e.status_code in (500, 503) and attempt < max_retries:
                wait = 2 ** attempt
                print(f'  ⚠️  API {e.status_code}エラー、{wait}秒後にリトライ ({attempt + 1}/{max_retries})')
                time.sleep(wait)
                continue
            raise

# ----------------------------------------------------------------
# Short判定
# ----------------------------------------------------------------

def is_short_video(video_id):
    """ShortsのURLにアクセスしてリダイレクト先で判定"""
    url = f'https://www.youtube.com/shorts/{video_id}'
    for attempt in range(3):
        try:
            response = requests.head(url, allow_redirects=True, timeout=5)
            return 'shorts' in response.url.lower()
        except Exception:
            if attempt < 2:
                wait = 2 ** attempt
                print(f'  ⚠️  Short判定失敗、{wait}秒後にリトライ ({attempt + 1}/2): {video_id}')
                time.sleep(wait)
    return False

def check_shorts_batch(video_ids):
    """複数動画のShort判定を並列実行"""
    results = {}
    if not video_ids:
        return results

    print(f'  並列Short判定: {len(video_ids)}本 ({MAX_WORKERS}並列)')
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_id = {executor.submit(is_short_video, vid): vid for vid in video_ids}
        completed = 0
        for future in as_completed(future_to_id):
            vid = future_to_id[future]
            try:
                results[vid] = future.result()
            except Exception:
                results[vid] = False
            completed += 1
            if completed % 20 == 0:
                print(f'    → {completed}/{len(video_ids)}本完了')

    elapsed = time.time() - start
    short_count = sum(1 for v in results.values() if v)
    print(f'  Short判定完了: {elapsed:.1f}秒 ({short_count}本がShort)')
    return results

# ----------------------------------------------------------------
# 動画タイプ判定
# ----------------------------------------------------------------

def get_duration_minutes(video):
    try:
        duration_str = video['contentDetails']['duration']
        duration = isodate.parse_duration(duration_str)
        return duration.total_seconds() / 60
    except Exception:
        return 0

def determine_video_type(video, short_cache, overrides, channel_name):
    """
    判定順序:
    1. video_flags.json（最優先）
    2. Short（URLリダイレクト判定）
    3. liveBroadcastContent == completed → duration で Movie/LiveArchive
    4. その他 → Movie
    """
    video_id = video['id']

    # 1. 例外設定
    if overrides and channel_name in overrides:
        if video_id in overrides[channel_name]:
            override_type = overrides[channel_name][video_id]
            print(f'  ⚙️  例外設定: [{video["snippet"]["title"][:40]}] → {override_type}')
            return override_type

    # 2. Short
    if short_cache.get(video_id, False):
        return 'Short'

    # 3. ライブアーカイブ判定
    live = video['snippet'].get('liveBroadcastContent', 'none')
    if live == 'completed':
        return 'LiveArchive' if get_duration_minutes(video) >= 6 else 'Movie'

    if 'liveStreamingDetails' in video:
        if 'actualStartTime' in video['liveStreamingDetails']:
            return 'LiveArchive' if get_duration_minutes(video) >= 6 else 'Movie'

    # 4. デフォルト
    return 'Movie'

# ----------------------------------------------------------------
# YouTube API
# ----------------------------------------------------------------

def get_channel_id(youtube, channel_url):
    """チャンネルURLからチャンネルIDを取得"""
    try:
        if '@' in channel_url:
            handle = channel_url.split('@')[-1]
            # forHandle を使うと @ハンドルで本人チャンネルを直接取得（Topic誤認なし）
            resp = execute_with_retry(youtube.channels().list(
                part='id', forHandle=handle
            ))
            if resp.get('items'):
                return resp['items'][0]['id']
        # /channel/UC... 形式の直接ID指定
        if '/channel/' in channel_url:
            channel_id = channel_url.split('/channel/')[-1].strip('/')
            resp = execute_with_retry(youtube.channels().list(
                part='id', id=channel_id
            ))
            if resp.get('items'):
                return resp['items'][0]['id']
    except Exception as e:
        print(f'  ⚠️  チャンネルID取得エラー: {e}')
    return None

def get_channel_stats(youtube, channel_id):
    """チャンネル統計を取得"""
    try:
        resp = execute_with_retry(youtube.channels().list(
            part='statistics,snippet,brandingSettings', id=channel_id
        ))
        if resp['items']:
            item = resp['items'][0]
            banner_url = (
                item.get('brandingSettings', {})
                    .get('image', {})
                    .get('bannerExternalUrl', '')
            )
            return {
                'チャンネル名': item['snippet']['title'],
                '登録者数': int(item['statistics'].get('subscriberCount', 0)),
                '総再生数': int(item['statistics'].get('viewCount', 0)),
                '動画数': int(item['statistics'].get('videoCount', 0)),
                'banner_url': banner_url,
                '取得日時': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    except Exception as e:
        print(f'  ⚠️  チャンネル統計取得エラー: {e}')
    return None

def get_all_videos(youtube, channel_id, channel_name, overrides):
    """チャンネルの全動画を取得してタイプ判定（Short判定はキャッシュ活用）"""
    snapshots = load_json(SNAPSHOTS_FILE, {})
    cached_videos = snapshots.get(channel_name, {}).get('videos', {})

    for attempt in range(3):
        videos = []
        try:
            resp = execute_with_retry(youtube.channels().list(
                part='contentDetails', id=channel_id
            ))
            if not resp['items']:
                return videos

            playlist_id = resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            next_page_token = None

            while True:
                playlist_resp = execute_with_retry(youtube.playlistItems().list(
                    part='snippet',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ))

                video_ids = [
                    item['snippet']['resourceId']['videoId']
                    for item in playlist_resp['items']
                ]

                videos_resp = execute_with_retry(youtube.videos().list(
                    part='snippet,statistics,liveStreamingDetails,contentDetails',
                    id=','.join(video_ids)
                ))

                print(f'  取得中... {len(videos) + len(videos_resp["items"])}本')

                # 新規動画（キャッシュにないもの）のみShort判定
                new_video_ids = [
                    vid for vid in video_ids
                    if vid not in cached_videos
                ]
                if new_video_ids:
                    print(f'  新規動画 {len(new_video_ids)}本のShort判定を実行')
                    short_cache = check_shorts_batch(new_video_ids)
                else:
                    short_cache = {}

                for video in videos_resp['items']:
                    vid = video['id']

                    # キャッシュにtypeがある場合は例外設定のみチェックして再利用
                    if vid in cached_videos:
                        cached_type = cached_videos[vid].get('type', 'Movie')
                        # 例外設定は常に最優先
                        if overrides and channel_name in overrides and vid in overrides[channel_name]:
                            vtype = overrides[channel_name][vid]
                            print(f'  ⚙️  例外設定: [{video["snippet"]["title"][:40]}] → {vtype}')
                        else:
                            vtype = cached_type
                    else:
                        vtype = determine_video_type(video, short_cache, overrides, channel_name)

                    videos.append({
                        '動画ID': vid,
                        'タイトル': video['snippet']['title'],
                        '公開日': video['snippet']['publishedAt'][:10],
                        '再生数': int(video['statistics'].get('viewCount', 0)),
                        '高評価数': int(video['statistics'].get('likeCount', 0)),
                        'コメント数': int(video['statistics'].get('commentCount', 0)),
                        'type': vtype,
                        'duration': int(isodate.parse_duration(
                            video['contentDetails'].get('duration', 'PT0S')
                        ).total_seconds()),
                    })

                next_page_token = playlist_resp.get('nextPageToken')
                if not next_page_token:
                    break

            # グリッチ検知: 高評価・コメント数が0だが過去に非0だった動画を再取得
            glitch_ids = [
                v['動画ID'] for v in videos
                if v['高評価数'] == 0 and v['コメント数'] == 0
                and (
                    cached_videos.get(v['動画ID'], {}).get('高評価数', 0) > 0
                    or cached_videos.get(v['動画ID'], {}).get('コメント数', 0) > 0
                )
            ]
            if glitch_ids:
                print(f'  ⚠️  グリッチ疑い: {len(glitch_ids)}本（高評価・コメント数が0）。5秒後に再取得...')
                for gid in glitch_ids:
                    title = next((v['タイトル'] for v in videos if v['動画ID'] == gid), gid)
                    print(f'    - {title[:50]}')
                time.sleep(5)
                retry_resp = execute_with_retry(youtube.videos().list(
                    part='statistics',
                    id=','.join(glitch_ids)
                ))
                retried = {item['id']: item['statistics'] for item in retry_resp.get('items', [])}
                fixed = 0
                for v in videos:
                    if v['動画ID'] in retried:
                        stats = retried[v['動画ID']]
                        new_likes = int(stats.get('likeCount', 0))
                        new_comments = int(stats.get('commentCount', 0))
                        if new_likes > 0 or new_comments > 0:
                            print(f'    ✓ 修正: [{v["タイトル"][:40]}] '
                                  f'高評価 {v["高評価数"]}→{new_likes} / コメント {v["コメント数"]}→{new_comments}')
                            v['高評価数'] = new_likes
                            v['コメント数'] = new_comments
                            fixed += 1
                print(f'  グリッチ修正: {fixed}/{len(glitch_ids)}本')

            print(f'  ✓ 完了: {len(videos)}本')
            print(f'    Movie: {sum(1 for v in videos if v["type"] == "Movie")}本 / '
                  f'Short: {sum(1 for v in videos if v["type"] == "Short")}本 / '
                  f'LiveArchive: {sum(1 for v in videos if v["type"] == "LiveArchive")}本')
            return videos

        except HttpError as e:
            if e.status_code == 404 and attempt < 2:
                wait = 30
                print(f'  ⚠️  404 playlistNotFound、{wait}秒後にリトライ ({attempt + 1}/2)')
                time.sleep(wait)
                continue
            print(f'  ⚠️  動画取得エラー: {e}')
            return []
        except Exception as e:
            print(f'  ⚠️  動画取得エラー: {e}')
            return []

    return []

# ----------------------------------------------------------------
# データ保存
# ----------------------------------------------------------------

def update_snapshots(channel_name, channel_id, channel_stats, videos):
    """all_snapshots.json を更新"""
    with _snapshot_lock:
        snapshots = load_json(SNAPSHOTS_FILE, {})

        snapshots[channel_name] = {
            'channel_id': channel_id,
            'channel_stats': channel_stats,
            'videos': {
                v['動画ID']: {
                    'タイトル': v['タイトル'],
                    '再生数': v['再生数'],
                    '高評価数': v['高評価数'],
                    'コメント数': v['コメント数'],
                    'duration': v.get('duration', 0),
                    'type': v['type']
                } for v in videos
            }
        }

        save_json(SNAPSHOTS_FILE, snapshots)
        print(f'  スナップショット保存: {SNAPSHOTS_FILE}')

def update_history(channel_name, videos, today_str, channel_stats=None):
    """history_{channel_name}.json を更新（日次集約: 1日1レコード）"""
    path = history_file(channel_name)
    history = load_json(path, {})

    if channel_name not in history:
        history[channel_name] = {}

    channel_history = history[channel_name]

    # チャンネル統計の日次履歴を保存（_channel_stats キーに蓄積）
    if channel_stats:
        if '_channel_stats' not in channel_history:
            channel_history['_channel_stats'] = {}
        channel_history['_channel_stats'][today_str] = {
            '登録者数': channel_stats.get('登録者数', 0),
            '総再生数': channel_stats.get('総再生数', 0),
            '動画数':   channel_stats.get('動画数', 0),
        }

    for video in videos:
        video_id = video['動画ID']

        if video_id not in channel_history:
            channel_history[video_id] = {
                'タイトル': video['タイトル'],
                '公開日': video['公開日'],
                'type': video['type'],
                'duration': video.get('duration', 0),
                'records': {}
            }
        else:
            old_type = channel_history[video_id].get('type')
            if old_type != video['type']:
                print(f'  🔄 タイプ更新: [{video["タイトル"][:40]}] {old_type} → {video["type"]}')
            channel_history[video_id]['type'] = video['type']
            channel_history[video_id]['タイトル'] = video['タイトル']
            channel_history[video_id]['duration'] = video.get('duration', 0)

        # 日次集約: 同日のレコードは上書き（最新値で更新）
        channel_history[video_id]['records'][today_str] = {
            '再生数': video['再生数'],
            '高評価数': video['高評価数'],
            'コメント数': video['コメント数']
        }

    history[channel_name] = channel_history
    save_json(path, history)
    print(f'  履歴保存: {path}')

# ----------------------------------------------------------------
# Dashboard用軽量集計ファイル
# ----------------------------------------------------------------

SUMMARY_FILE = 'dashboard_summary.json'
CHANNELS_CONFIG_FILE = 'channels_config.json'

def load_talent_names():
    """channels_config.jsonからタレント名一覧を取得（API/環境変数なしで動作）"""
    config = load_json(CHANNELS_CONFIG_FILE, [])
    return [c['name'] for c in config if 'name' in c]

def build_dashboard_summary():
    """
    Dashboard（全タレント横断のランキング・統計表示）専用の軽量サマリーを
    history_{talent}.json から再集計して dashboard_summary.json に書き出す。

    history_*.json は日々肥大化し続けるため、Dashboardの毎回の全件取得が
    レート制限を引き起こしていた。このサマリーは「全タレントの動画の
    直近2日分スナップショット」と「チャンネル統計の全期間」のみを持ち、
    動画本数の増加分でしか大きくならない。

    history_*.json / all_snapshots.json の書き込みには一切関与しない
    （既存の収集フローとは独立した読み取り専用の後処理）。
    """
    talents = load_talent_names()
    if not talents:
        print('  ⚠️  channels_config.json からタレント一覧を取得できませんでした。summary生成をスキップします。')
        return

    channel_stats_summary = {}
    all_dates = set()
    talent_videos = {}  # talent -> {vid_id: {タイトル, type, records}}

    for talent in talents:
        history = load_json(history_file(talent), {})
        channel_history = history.get(talent)
        if not channel_history:
            continue

        cs = channel_history.get('_channel_stats', {})
        if cs:
            channel_stats_summary[talent] = cs
            all_dates.update(cs.keys())

        videos = {
            vid_id: v for vid_id, v in channel_history.items()
            if vid_id != '_channel_stats' and v.get('records')
        }
        if videos:
            talent_videos[talent] = videos

    if not all_dates:
        print('  ⚠️  有効な_channel_statsが見つかりませんでした。summary生成をスキップします。')
        return

    sorted_dates = sorted(all_dates)
    n_date = sorted_dates[-1]
    n_idx = sorted_dates.index(n_date)
    p_date = sorted_dates[n_idx - 1] if n_idx > 0 else None

    # 動画スナップショット（n_date/p_dateの2日分のみ、記録が無ければnull）
    video_snapshots = []
    for talent, videos in talent_videos.items():
        for vid_id, v in videos.items():
            records = v.get('records', {})
            nr = records.get(n_date)
            pr = records.get(p_date) if p_date else None
            video_snapshots.append({
                't': talent,
                'id': vid_id,
                'ti': v.get('タイトル', vid_id),
                'ty': v.get('type', 'Movie'),
                'vn': nr.get('再生数') if nr else None,
                'ln': nr.get('高評価数') if nr else None,
                'cn': nr.get('コメント数') if nr else None,
                'vp': pr.get('再生数') if pr else None,
                'lp': pr.get('高評価数') if pr else None,
                'cp': pr.get('コメント数') if pr else None,
            })

    # 日別種別内訳（Movie/Short/LiveArchiveの再生数増分、全タレント合計）
    daily_type_totals = {}
    for talent, videos in talent_videos.items():
        for vid_id, v in videos.items():
            records = v.get('records', {})
            vtype = v.get('type', 'Movie')
            vdates = sorted(records.keys())
            for i in range(1, len(vdates)):
                d, prev = vdates[i], vdates[i - 1]
                diff = (records[d].get('再生数', 0) or 0) - (records[prev].get('再生数', 0) or 0)
                if diff <= 0:
                    continue
                bucket = daily_type_totals.setdefault(d, {'Movie': 0, 'Short': 0, 'LiveArchive': 0})
                if vtype in bucket:
                    bucket[vtype] += diff

    daily_type_breakdown = [
        {'date': d, **daily_type_totals[d]} for d in sorted(daily_type_totals.keys())
    ]

    summary = {
        'generated_at': datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S'),
        'n_date': n_date,
        'p_date': p_date,
        'channel_stats': channel_stats_summary,
        'daily_type_breakdown': daily_type_breakdown,
        'videos': video_snapshots,
    }

    save_json(SUMMARY_FILE, summary, indent=None)
    print(f'  Dashboard集計保存: {SUMMARY_FILE}（動画{len(video_snapshots)}件 / タレント{len(channel_stats_summary)}件 / n_date={n_date} p_date={p_date}）')

# ----------------------------------------------------------------
# チャンネル処理
# ----------------------------------------------------------------

def process_channel(channel_config, overrides, today_str):
    """1チャンネルの処理（スレッドセーフ：APIクライアントを個別生成）"""
    channel_name = channel_config['name']
    channel_url = channel_config['url']

    print(f'\n{"=" * 50}')
    print(f'処理中: {channel_name}')
    print(f'{"=" * 50}')

    # スレッドごとに独自のAPIクライアントを生成
    youtube = build('youtube', 'v3', developerKey=API_KEY)

    # チャンネルIDをキャッシュから取得、なければAPIで取得
    snapshots = load_json(SNAPSHOTS_FILE, {})
    channel_id = snapshots.get(channel_name, {}).get('channel_id')

    if not channel_id:
        print(f'  チャンネルIDを取得中...')
        channel_id = get_channel_id(youtube, channel_url)
        if not channel_id:
            print(f'  ❌ チャンネルが見つかりませんでした: {channel_name}')
            return False
        print(f'  チャンネルID: {channel_id}')
    else:
        print(f'  チャンネルID（キャッシュ）: {channel_id}')

    # チャンネル統計
    channel_stats = get_channel_stats(youtube, channel_id)
    if not channel_stats:
        print(f'  ❌ チャンネル統計を取得できませんでした')
        return False

    # 全動画取得
    videos = get_all_videos(youtube, channel_id, channel_name, overrides)
    if not videos:
        print(f'  ❌ 動画を取得できませんでした')
        return False

    # 総再生数 = 全動画（Movie/Short/LiveArchive）の再生数の総和（JST 00:00時点）
    channel_stats['総再生数'] = sum(v['再生数'] for v in videos)

    print(f'  登録者数: {channel_stats["登録者数"]:,}人 / '
          f'総再生数: {channel_stats["総再生数"]:,}回 / '
          f'動画数: {channel_stats["動画数"]:,}本')

    # 保存
    update_snapshots(channel_name, channel_id, channel_stats, videos)
    update_history(channel_name, videos, today_str, channel_stats=channel_stats)

    print(f'  ✓ {channel_name} 完了')
    return True

# ----------------------------------------------------------------
# メイン
# ----------------------------------------------------------------

def main():
    now = datetime.now(timezone(timedelta(hours=9)))
    today_str = now.strftime('%Y-%m-%d')

    print('=' * 50)
    print('YouTube統計 自動チェック開始')
    print(f'実行日時: {now.strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 50)

    if not API_KEY:
        print('❌ エラー: YOUTUBE_API_KEY が設定されていません')
        return

    if not CHANNELS:
        print('❌ エラー: CHANNELS が設定されていません')
        return

    print(f'\n処理対象: {len(CHANNELS)}チャンネル')
    for ch in CHANNELS:
        print(f'  - {ch["name"]}')

    overrides = load_overrides()

    # チャンネル処理を並列実行（3チャンネル同時）
    success = 0
    failed_channels = []
    with ThreadPoolExecutor(max_workers=CHANNEL_WORKERS) as executor:
        futures = {
            executor.submit(
                process_channel, ch, overrides, today_str
            ): ch
            for ch in CHANNELS
        }
        for future in as_completed(futures):
            ch = futures[future]
            try:
                if future.result():
                    success += 1
                else:
                    failed_channels.append(ch)
            except Exception as e:
                print(f'  ❌ {ch["name"]} で予期しないエラー: {e}')
                failed_channels.append(ch)

    # 失敗チャンネルのリトライ
    still_failed = []
    if failed_channels:
        print(f'\n⚠️  {len(failed_channels)}チャンネルが失敗。30秒後にリトライします...')
        for ch in failed_channels:
            print(f'  - {ch["name"]}')
        time.sleep(30)
        with ThreadPoolExecutor(max_workers=CHANNEL_WORKERS) as executor:
            futures = {
                executor.submit(
                    process_channel, ch, overrides, today_str
                ): ch
                for ch in failed_channels
            }
            for future in as_completed(futures):
                ch = futures[future]
                try:
                    if future.result():
                        success += 1
                    else:
                        still_failed.append(ch['name'])
                except Exception as e:
                    print(f'  ❌ {ch["name"]} で予期しないエラー: {e}')
                    still_failed.append(ch['name'])

    print(f'\n{"=" * 50}')
    print(f'✓ 全処理完了: {success}/{len(CHANNELS)} チャンネル成功')
    print('=' * 50)

    try:
        build_dashboard_summary()
    except Exception as e:
        print(f'⚠️  dashboard_summary.json 生成に失敗しました（本処理には影響しません）: {e}')

    if still_failed:
        print(f'❌ リトライ後も失敗: {", ".join(still_failed)}')
        sys.exit(1)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary-only', action='store_true',
                         help='既存のhistory_*.jsonからdashboard_summary.jsonのみ再生成（YouTube API呼び出しなし）')
    args = parser.parse_args()

    if args.summary_only:
        build_dashboard_summary()
    else:
        main()
