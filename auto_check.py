#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube チャンネル統計 自動チェックスクリプト
GitHub Actionsで定期実行される（JST 00:00）

- 全アーティストのチャンネル統計・動画データを収集
- Movie/Short/LiveArchive自動判別（並列処理）
- video_type_overrides.json による例外設定対応
- チャンネルIDキャッシュで無駄なAPIコールを削減
- データ保存先:
    all_snapshots.json        : 全アーティストの最新スナップショット
    all_history_{year}.json   : 年ごとの動画履歴（日次集約済み）
"""

import os
import json
import requests
import threading
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
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

# ファイル書き込みの排他制御用ロック（並列処理による競合防止）
_file_lock = threading.Lock()

def history_file(year):
    return f'all_history_{year}.json'

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

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ----------------------------------------------------------------
# 例外設定
# ----------------------------------------------------------------

def load_overrides():
    overrides = load_json('video_type_overrides.json', {})
    total = sum(len(v) for v in overrides.values())
    if total:
        print(f'✓ 例外設定を読み込みました: {total}件')
    return overrides

# ----------------------------------------------------------------
# Short判定
# ----------------------------------------------------------------

def is_short_video(video_id):
    """ShortsのURLにアクセスしてリダイレクト先で判定"""
    try:
        url = f'https://www.youtube.com/shorts/{video_id}'
        response = requests.head(url, allow_redirects=True, timeout=5)
        return 'shorts' in response.url.lower()
    except Exception:
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
    1. video_type_overrides.json（最優先）
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
            resp = youtube.channels().list(
                part='id', forHandle=handle
            ).execute()
            if resp.get('items'):
                return resp['items'][0]['id']
        # /channel/UC... 形式の直接ID指定
        if '/channel/' in channel_url:
            channel_id = channel_url.split('/channel/')[-1].strip('/')
            resp = youtube.channels().list(
                part='id', id=channel_id
            ).execute()
            if resp.get('items'):
                return resp['items'][0]['id']
    except Exception as e:
        print(f'  ⚠️  チャンネルID取得エラー: {e}')
    return None

def get_channel_stats(youtube, channel_id):
    """チャンネル統計を取得"""
    try:
        resp = youtube.channels().list(
            part='statistics,snippet,brandingSettings', id=channel_id
        ).execute()
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
    videos = []

    # 既存のtypeキャッシュをall_snapshots.jsonから取得
    snapshots = load_json(SNAPSHOTS_FILE, {})
    cached_videos = snapshots.get(channel_name, {}).get('videos', {})

    try:
        resp = youtube.channels().list(
            part='contentDetails', id=channel_id
        ).execute()
        if not resp['items']:
            return videos

        playlist_id = resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        next_page_token = None

        while True:
            playlist_resp = youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            video_ids = [
                item['snippet']['resourceId']['videoId']
                for item in playlist_resp['items']
            ]

            videos_resp = youtube.videos().list(
                part='snippet,statistics,liveStreamingDetails,contentDetails',
                id=','.join(video_ids)
            ).execute()

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
                if vid in cached_videos and vid not in new_video_ids:
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
                    'type': vtype
                })

            next_page_token = playlist_resp.get('nextPageToken')
            if not next_page_token:
                break

        print(f'  ✓ 完了: {len(videos)}本')
        print(f'    Movie: {sum(1 for v in videos if v["type"] == "Movie")}本 / '
              f'Short: {sum(1 for v in videos if v["type"] == "Short")}本 / '
              f'LiveArchive: {sum(1 for v in videos if v["type"] == "LiveArchive")}本')

    except Exception as e:
        print(f'  ⚠️  動画取得エラー: {e}')

    return videos

# ----------------------------------------------------------------
# データ保存
# ----------------------------------------------------------------

def update_snapshots(channel_name, channel_id, channel_stats, videos):
    """all_snapshots.json を更新"""
    with _file_lock:
        snapshots = load_json(SNAPSHOTS_FILE, {})

        snapshots[channel_name] = {
            'channel_id': channel_id,
            'channel_stats': channel_stats,
            'videos': {
                v['動画ID']: {
                    'タイトル': v['タイトル'],
                    '再生数': v['再生数'],
                    '高評価数': v['高評価数'],
                    'type': v['type']
                } for v in videos
            }
        }

        save_json(SNAPSHOTS_FILE, snapshots)
        print(f'  スナップショット保存: {SNAPSHOTS_FILE}')

def update_history(channel_name, videos, today_str, year, channel_stats=None):
    """all_history_{year}.json を更新（日次集約: 1日1レコード）"""
    path = history_file(year)
    with _file_lock:
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
                    'records': {}
                }
            else:
                old_type = channel_history[video_id].get('type')
                if old_type != video['type']:
                    print(f'  🔄 タイプ更新: [{video["タイトル"][:40]}] {old_type} → {video["type"]}')
                channel_history[video_id]['type'] = video['type']
                channel_history[video_id]['タイトル'] = video['タイトル']

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
# チャンネル処理
# ----------------------------------------------------------------

def process_channel(channel_config, overrides, today_str, year):
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

    print(f'  登録者数: {channel_stats["登録者数"]:,}人 / '
          f'総再生数: {channel_stats["総再生数"]:,}回 / '
          f'動画数: {channel_stats["動画数"]:,}本')

    # 全動画取得
    videos = get_all_videos(youtube, channel_id, channel_name, overrides)
    if not videos:
        print(f'  ❌ 動画を取得できませんでした')
        return False

    # 保存
    update_snapshots(channel_name, channel_id, channel_stats, videos)
    update_history(channel_name, videos, today_str, year, channel_stats=channel_stats)

    print(f'  ✓ {channel_name} 完了')
    return True

# ----------------------------------------------------------------
# メイン
# ----------------------------------------------------------------

def main():
    now = datetime.now(timezone(timedelta(hours=9)))
    today_str = now.strftime('%Y-%m-%d')
    year = now.strftime('%Y')

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
    with ThreadPoolExecutor(max_workers=CHANNEL_WORKERS) as executor:
        futures = {
            executor.submit(
                process_channel, ch, overrides, today_str, year
            ): ch['name']
            for ch in CHANNELS
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                if future.result():
                    success += 1
            except Exception as e:
                print(f'  ❌ {name} で予期しないエラー: {e}')

    print(f'\n{"=" * 50}')
    print(f'✓ 全処理完了: {success}/{len(CHANNELS)} チャンネル成功')
    print('=' * 50)

if __name__ == '__main__':
    main()
