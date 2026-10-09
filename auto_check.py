#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube チャンネル統計 自動チェックスクリプト
GitHub Actionsで定期実行される（JST 00:00）

- 全アーティストのチャンネル統計・動画データを収集
- Movie/Short/LiveArchive自動判別（確定するまで毎日判定し直す。配信前・配信中は Pending）
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

LIVE_MIN_SEC = 420    # タブで分からないときの予備。これ以上の長さはライブ、未満は動画（2026-10-04 6分から7分へ）
SHORT_MAX_SEC = 180   # ショートは3分まで。これより長い動画はショート判定を省く
PENDING = 'Pending'   # 配信前・配信中など、まだ種別を決められない動画。サイトには出さない

# 取りこぼしへの備え（2026-10-10）。10/9 に CULUA の1ページで詳細が50本中19本しか返らず、31本がその日の記録から抜けた。
# 4/4・4/19・10/2 にも同じような抜けがあった
LIST_RETRIES = 2      # 一覧が総件数より少ないときに読み直す回数
DETAIL_RETRIES = 3    # 詳細が返ってこなかった動画を取り直す回数
RETRY_WAIT_SEC = 10   # 読み直し・取り直しの前に待つ秒数（回を重ねるごとに延ばす）
FILL_MARK = '補完'     # 取り切れなかった日を、直前の値で埋めた記録に付ける印

SNAPSHOTS_FILE = 'all_snapshots.json'

# スナップショット書き込みの排他制御用ロック（並列処理による競合防止）
_snapshot_lock = threading.Lock()

# この実行で取り切れなかった分・解消した分・埋めた日。最後に通知と日別ファイルの書き直しに使う
_report_lock = threading.Lock()
REPORT = {'alerts': [], 'resolved': [], 'filled_dates': set()}

def report(kind, value):
    with _report_lock:
        if kind == 'filled_dates':
            REPORT[kind].update(value)
        else:
            REPORT[kind].append(value)

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

def save_json(path, data, indent=None):
    """indent を省くと、区切りの空白も省いて詰めて書く（履歴ファイルの肥大を抑えるため）"""
    dir_ = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=dir_, delete=False, suffix='.tmp') as f:
        if indent is None:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        else:
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
    """
    ショートのURLを開き、そのまま表示されればショート、通常の再生ページへ転送されればショートではない。
    どちらとも言えない応答（通信失敗・同意画面への転送など）は None を返し、翌日に判定し直す。
    以前は失敗をショートではないと扱い、そのまま確定していた。
    """
    url = f'https://www.youtube.com/shorts/{video_id}'
    for attempt in range(3):
        try:
            response = requests.head(url, allow_redirects=False, timeout=5)
            if response.status_code == 200:
                return True
            if response.is_redirect and '/watch' in response.headers.get('Location', ''):
                return False
        except Exception:
            pass
        if attempt < 2:
            wait = 2 ** attempt
            print(f'  ⚠️  Short判定失敗、{wait}秒後にリトライ ({attempt + 1}/2): {video_id}')
            time.sleep(wait)
    return None

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
                results[vid] = None
            completed += 1
            if completed % 20 == 0:
                print(f'    → {completed}/{len(video_ids)}本完了')

    elapsed = time.time() - start
    short_count = sum(1 for v in results.values() if v)
    failed_count = sum(1 for v in results.values() if v is None)
    print(f'  Short判定完了: {elapsed:.1f}秒 ({short_count}本がShort'
          + (f'、{failed_count}本は判定できず翌日に持ち越し' if failed_count else '') + ')')
    return results

# ----------------------------------------------------------------
# 動画タイプ判定
# ----------------------------------------------------------------

def get_duration_seconds(video):
    try:
        return int(isodate.parse_duration(video['contentDetails'].get('duration', 'PT0S')).total_seconds())
    except Exception:
        return 0

def classify(duration_sec, live_status, tab_type, short_result):
    """
    自動判定。戻り値は (種別, 確定したか)。video_flags.json の例外はこの外で優先して当てる。

    1. 配信前・配信中（長さが0）は判定できないので Pending のまま持ち越す。
       以前は初めて見つけた日に1回だけ判定して固定していたため、
       待機所の段階で Movie に決まり、6分を超える配信が Movie のまま残っていた。
    2. チャンネルの「動画 / ショート / ライブ」タブのどれに入っているかで決める（確定）。
    3. タブで分からないときだけ、時間で仮に決める。確定はせず、翌日にタブで判定し直す。
       3分以下はショートかを確かめ（確かめられなければ Pending）、それ以外は長さで分ける。
    """
    if live_status in ('upcoming', 'live') or duration_sec <= 0:
        return PENDING, False
    if tab_type:
        return tab_type, True
    if duration_sec <= SHORT_MAX_SEC:
        if short_result is None:
            return PENDING, False
        if short_result:
            return 'Short', False
    return ('LiveArchive' if duration_sec >= LIVE_MIN_SEC else 'Movie'), False

TAB_PLAYLISTS = (('UULF', 'Movie'), ('UUSH', 'Short'), ('UULV', 'LiveArchive'))

def get_tab_types(youtube, channel_id):
    """
    チャンネルページの「動画 / ショート / ライブ」タブの再生リストから、動画ごとの種別を返す。
    再生リストのIDは、チャンネルIDの先頭 UC を UULF / UUSH / UULV に替えたもの。
    YouTube の公式の文書には無い仕組みなので、読めなければ空を返し、呼び出し側が時間で仮に判定する。
    2026-10-04、全23チャンネル9,431本のすべてが、どれか1つのタブにだけ入っていることを確認した。
    """
    result = {}
    for prefix, vtype in TAB_PLAYLISTS:
        token = None
        try:
            while True:
                resp = execute_with_retry(youtube.playlistItems().list(
                    part='contentDetails', playlistId=prefix + channel_id[2:],
                    maxResults=50, pageToken=token
                ))
                for item in resp.get('items', []):
                    result[item['contentDetails']['videoId']] = vtype
                token = resp.get('nextPageToken')
                if not token:
                    break
        except HttpError as e:
            if e.status_code == 404:
                # そのタブに1本も無いチャンネルでも起こりうるので、空のタブとして続ける
                print(f'  ⚠️  {prefix} のタブが見つかりません（空として扱います）')
                continue
            print(f'  ⚠️  タブの取得に失敗しました。今日の新しい動画は時間で仮に判定します: {e}')
            return {}
        except Exception as e:
            print(f'  ⚠️  タブの取得に失敗しました。今日の新しい動画は時間で仮に判定します: {e}')
            return {}
    return result

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

def list_upload_ids(youtube, playlist_id, name=''):
    """
    アップロードの一覧を最後まで読み、(IDの並び, 総件数, 総件数どおりに読めたか) を返す。
    一覧のAPIが返す総件数（pageInfo.totalResults）より少なければ、少し待って読み直し、読めたIDを足し合わせる。
    2026-10-10 の確認で、総件数は全23チャンネルで実際に受け取れたIDの数と一致した。
    """
    ids, seen, total = [], set(), None
    for attempt in range(LIST_RETRIES + 1):
        token, pages = None, 0
        while True:
            resp = execute_with_retry(youtube.playlistItems().list(
                part='contentDetails', playlistId=playlist_id, maxResults=50, pageToken=token
            ))
            if total is None:
                total = resp.get('pageInfo', {}).get('totalResults')
            pages += 1
            for item in resp.get('items', []):
                vid = item['contentDetails']['videoId']
                if vid not in seen:
                    seen.add(vid)
                    ids.append(vid)
            token = resp.get('nextPageToken')
            if not token:
                break
        print(f'  [{name}] 一覧: {len(ids)}本 / 総件数 {total}（{pages}ページ）')
        if total is None or len(ids) >= total:
            return ids, total, True
        if attempt < LIST_RETRIES:
            wait = RETRY_WAIT_SEC * (attempt + 1)
            print(f'  ⚠️  [{name}] 一覧が総件数より{total - len(ids)}本少ないため、{wait}秒後に読み直します ({attempt + 1}/{LIST_RETRIES})')
            time.sleep(wait)
    return ids, total, False

def fetch_details(youtube, ids, name=''):
    """
    動画の詳細を50本ずつ取る。頼んだIDのうち返ってこなかったものは、少し待って取り直す。
    戻り値は ({動画ID: 詳細}, 最後まで返ってこなかったIDの並び)。
    ページごとの「返ってきた数/頼んだ数」をログに出す（10/9 はどちらのAPIで欠けたかをログから追えなかった）。
    """
    got = {}
    pending = list(ids)
    missing = []
    for attempt in range(DETAIL_RETRIES + 1):
        missing, counts = [], []
        for i in range(0, len(pending), 50):
            batch = pending[i:i + 50]
            resp = execute_with_retry(youtube.videos().list(
                part='snippet,statistics,liveStreamingDetails,contentDetails', id=','.join(batch)
            ))
            items = {item['id']: item for item in resp.get('items', [])}
            got.update(items)
            counts.append(f'{len(items)}/{len(batch)}')
            missing += [vid for vid in batch if vid not in items]
        label = '詳細' if attempt == 0 else f'取り直し{attempt}回目'
        print(f'  [{name}] {label}（返ってきた数/頼んだ数）: {" ".join(counts)}')
        if not missing:
            break
        if attempt < DETAIL_RETRIES:
            wait = RETRY_WAIT_SEC * (attempt + 1)
            print(f'  ⚠️  [{name}] {len(missing)}本の詳細が返ってこなかったため、{wait}秒後に取り直します ({attempt + 1}/{DETAIL_RETRIES})')
            time.sleep(wait)
        pending = missing
    return got, missing

def describe_gone(youtube, ids):
    """
    一覧から外れた動画について、ログに出すための手がかりを返す（{動画ID: 説明}）。
    IDを指定して取れるか（取れたら公開状態）と、埋め込み情報（oEmbed）の応答コード。
    10/10 の確認では、一覧から外れた225本のうち206本はIDで取れず oEmbed が403か404、
    19本はIDで取れて oEmbed が200（限定公開4本、公開15本。メン限と思われるものを含む）だった。
    """
    status = {}
    for i in range(0, len(ids), 50):
        try:
            resp = execute_with_retry(youtube.videos().list(part='status', id=','.join(ids[i:i + 50])))
            for item in resp.get('items', []):
                status[item['id']] = item.get('status', {}).get('privacyStatus')
        except Exception:
            pass
    out = {}
    for vid in ids:
        try:
            code = requests.get('https://www.youtube.com/oembed',
                                params={'url': f'https://www.youtube.com/watch?v={vid}', 'format': 'json'},
                                timeout=10).status_code
        except Exception:
            code = '失敗'
        privacy = status.get(vid)
        out[vid] = (f'IDで取れる（{privacy}）' if privacy else 'IDで取れない') + f' / oEmbed {code}'
    return out

def get_all_videos(youtube, channel_id, channel_name, overrides):
    """
    チャンネルの全動画を取得してタイプ判定（確定済みの判定はキャッシュを再利用）。
    戻り値は (取れた動画の並び, 最後まで詳細が取れなかった動画ID, 一覧の様子)。失敗したときは ([], [], None)。
    詳細が取れなかった動画のうち前日まであったものは、呼び出し側が前日の値で埋める。
    総件数どおりに読めた一覧から外れた動画は、チャンネル側で外されたものとして収集をやめる（埋めない）。
    """
    snapshots = load_json(SNAPSHOTS_FILE, {})
    cached_videos = snapshots.get(channel_name, {}).get('videos', {})
    channel_flags = (overrides or {}).get(channel_name, {})

    for attempt in range(3):
        videos = []
        try:
            resp = execute_with_retry(youtube.channels().list(
                part='contentDetails', id=channel_id
            ))
            if not resp['items']:
                return [], [], None

            playlist_id = resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            listed, total, complete = list_upload_ids(youtube, playlist_id, channel_name)
            listed_set = set(listed)
            # 前日まで一覧にあって、今日の一覧に無い動画
            gone = [vid for vid in cached_videos if vid not in listed_set]
            targets = list(listed)
            if not complete:
                # 一覧が欠けたままなので、外されたのか取りこぼしたのか分からない。前日まであった動画はIDを指定して取りに行く
                targets += gone
                gone = []
            details, failed = fetch_details(youtube, targets, channel_name)
            items = [details[vid] for vid in targets if vid in details]

            # 自動判定が確定していない動画（新規・配信前・前回タブで分からなかったもの）だけ判定し直す。
            # 全部確定済みならタブは読まない
            unfixed = [video for video in items if not cached_videos.get(video['id'], {}).get('fixed')]
            tab_types = get_tab_types(youtube, channel_id) if unfixed else {}
            short_ids = [
                video['id'] for video in unfixed
                if video['id'] not in tab_types
                and video['snippet'].get('liveBroadcastContent', 'none') == 'none'
                and 0 < get_duration_seconds(video) <= SHORT_MAX_SEC
            ]
            if short_ids:
                print(f'  タブで分からない動画 {len(short_ids)}本のShort判定を実行')
                short_cache = check_shorts_batch(short_ids)
            else:
                short_cache = {}
            unfixed_ids = {video['id'] for video in unfixed}

            for video in items:
                vid = video['id']
                duration = get_duration_seconds(video)

                if vid in unfixed_ids:
                    auto, fixed = classify(duration,
                                           video['snippet'].get('liveBroadcastContent', 'none'),
                                           tab_types.get(vid), short_cache.get(vid))
                else:
                    cached = cached_videos[vid]
                    auto, fixed = cached.get('auto', cached.get('type', 'Movie')), True

                # 例外設定は常に最優先。auto は例外を外したときに戻る先として残しておく
                vtype = channel_flags.get(vid, auto)

                videos.append({
                    '動画ID': vid,
                    'タイトル': video['snippet']['title'],
                    '公開日': video['snippet']['publishedAt'][:10],
                    '再生数': int(video['statistics'].get('viewCount', 0)),
                    '高評価数': int(video['statistics'].get('likeCount', 0)),
                    'コメント数': int(video['statistics'].get('commentCount', 0)),
                    'type': vtype,
                    'auto': auto,
                    'fixed': fixed,
                    'duration': duration,
                })

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
                  f'LiveArchive: {sum(1 for v in videos if v["type"] == "LiveArchive")}本 / '
                  f'Pending: {sum(1 for v in videos if v["type"] == PENDING)}本 '
                  f'（うち例外設定 {sum(1 for v in videos if v["動画ID"] in channel_flags)}本）')

            gone_reasons = describe_gone(youtube, gone) if gone else {}
            for vid, why in gone_reasons.items():
                title = cached_videos.get(vid, {}).get('タイトル', '')
                print(f'  [{channel_name}] 一覧から外れた動画（収集をやめます）: {vid} {why} / {title[:40]}')
            info = {'listed': len(listed), 'total': total, 'complete': complete, 'gone': len(gone)}
            return videos, failed, info

        except HttpError as e:
            if e.status_code == 404 and attempt < 2:
                wait = 30
                print(f'  ⚠️  404 playlistNotFound、{wait}秒後にリトライ ({attempt + 1}/2)')
                time.sleep(wait)
                continue
            print(f'  ⚠️  動画取得エラー: {e}')
            return [], [], None
        except Exception as e:
            print(f'  ⚠️  動画取得エラー: {e}')
            return [], [], None

    return [], [], None

# ----------------------------------------------------------------
# データ保存
# ----------------------------------------------------------------

def snapshot_entry(v):
    entry = {
        'タイトル': v['タイトル'],
        '公開日': v['公開日'],
        '再生数': v['再生数'],
        '高評価数': v['高評価数'],
        'コメント数': v['コメント数'],
        'duration': v.get('duration', 0),
        'type': v['type'],    # 例外設定を当てた後の種別
        'auto': v['auto'],    # 自動判定の結果
        'fixed': v['fixed'],  # 自動判定が確定したか（False なら翌日も判定し直す）
    }
    if v.get(FILL_MARK):
        entry[FILL_MARK] = True  # 取り切れず、前日の値で埋めた
    return entry

def update_snapshots(channel_name, channel_id, channel_stats, videos, only_ids=None):
    """
    all_snapshots.json を更新。
    only_ids を渡したとき（予備の実行で、0時に埋めた動画だけを差し替えるとき）は、その動画の分だけ書き換える。
    """
    with _snapshot_lock:
        snapshots = load_json(SNAPSHOTS_FILE, {})

        if only_ids is None:
            snapshots[channel_name] = {
                'channel_id': channel_id,
                'channel_stats': channel_stats,
                'videos': {v['動画ID']: snapshot_entry(v) for v in videos}
            }
        else:
            current = snapshots.setdefault(channel_name, {'channel_id': channel_id, 'videos': {}})
            for v in videos:
                if v['動画ID'] in only_ids:
                    current['videos'][v['動画ID']] = snapshot_entry(v)

        save_json(SNAPSHOTS_FILE, snapshots)
        print(f'  スナップショット保存: {SNAPSHOTS_FILE}')

def carry_video(video_id, cached):
    """取り切れなかった動画を、前日のスナップショットの値でそのまま埋める"""
    return {
        '動画ID': video_id,
        'タイトル': cached.get('タイトル', ''),
        '公開日': cached.get('公開日', ''),
        '再生数': cached.get('再生数', 0),
        '高評価数': cached.get('高評価数', 0),
        'コメント数': cached.get('コメント数', 0),
        'type': cached.get('type', 'Movie'),
        'auto': cached.get('auto', cached.get('type', 'Movie')),
        'fixed': cached.get('fixed', True),
        'duration': cached.get('duration', 0),
        FILL_MARK: True,
    }

def dates_between(start, end):
    """start と end の間の日付（両端は含まない）"""
    day = datetime.strptime(start, '%Y-%m-%d') + timedelta(days=1)
    stop = datetime.strptime(end, '%Y-%m-%d')
    out = []
    while day < stop:
        out.append(day.strftime('%Y-%m-%d'))
        day += timedelta(days=1)
    return out

def fill_gaps(channel_history, on_date=None):
    """
    記録の抜けている日を、直前の記録の値で埋める（印 FILL_MARK を付ける）。埋めた日の集まりを返す。
    on_date を渡すと、その日に記録がある動画とチャンネル統計だけを見て、前の記録との間を埋める
    （一覧から外れて戻ってきた動画や、収集が動かなかった日の分）。渡さなければ、すべての抜けを埋める（過去分の是正用）。
    最後の記録より後（一覧から外れたまま戻っていない動画）は埋めない。
    埋めた日の総再生数は、その日の動画の再生数の合計に直す。3/26以降は総再生数を動画の合計で持っているため、
    埋める前に合計と一致していた日（と、チャンネル統計そのものを埋めた日）だけを直す。
    """
    stats = channel_history.setdefault('_channel_stats', {})
    video_records = [v.setdefault('records', {}) for vid, v in channel_history.items() if vid != '_channel_stats']

    def gaps_of(records):
        dates = sorted(records)
        if on_date is not None:
            if on_date not in records:
                return []
            before = [d for d in dates if d < on_date]
            pairs = [(before[-1], on_date)] if before else []
        else:
            pairs = list(zip(dates, dates[1:]))
        return [(d, prev) for prev, nxt in pairs for d in dates_between(prev, nxt)]

    video_gaps = [(records, gaps_of(records)) for records in video_records]
    stats_gaps = gaps_of(stats)
    filled = {d for _, gaps in video_gaps for d, _ in gaps} | {d for d, _ in stats_gaps}
    if not filled:
        return set()

    def video_sum(d):
        return sum((records.get(d) or {}).get('再生数', 0) for records in video_records)

    sum_rule = {d for d in filled if d in stats and stats[d].get('総再生数') == video_sum(d)}
    for records, gaps in video_gaps:
        for d, prev in gaps:
            src = records[prev]
            records[d] = {'再生数': src.get('再生数', 0), '高評価数': src.get('高評価数', 0),
                          'コメント数': src.get('コメント数', 0), FILL_MARK: True}
    for d, prev in stats_gaps:
        stats[d] = {**stats[prev], FILL_MARK: True}
        sum_rule.add(d)
    for d in sum_rule:
        stats[d]['総再生数'] = video_sum(d)
    return filled

def update_history(channel_name, videos, today_str, channel_stats=None, only_ids=None):
    """
    history_{channel_name}.json を更新（日次集約: 1日1レコード）。記録の抜けを埋めた日の集まりを返す。
    only_ids を渡したとき（予備の実行で、0時に埋めた動画だけを差し替えるとき）は、その動画の分だけ書き換え、
    今日の総再生数を動画の合計に直す。
    """
    path = history_file(channel_name)
    history = load_json(path, {})

    if channel_name not in history:
        history[channel_name] = {}

    channel_history = history[channel_name]

    # チャンネル統計の日次履歴を保存（_channel_stats キーに蓄積）
    if channel_stats and only_ids is None:
        if '_channel_stats' not in channel_history:
            channel_history['_channel_stats'] = {}
        channel_history['_channel_stats'][today_str] = {
            '登録者数': channel_stats.get('登録者数', 0),
            '総再生数': channel_stats.get('総再生数', 0),
            '動画数':   channel_stats.get('動画数', 0),
        }
        if channel_stats.get(FILL_MARK):
            channel_history['_channel_stats'][today_str][FILL_MARK] = True

    for video in videos:
        video_id = video['動画ID']
        if only_ids is not None and video_id not in only_ids:
            continue

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
        record = {
            '再生数': video['再生数'],
            '高評価数': video['高評価数'],
            'コメント数': video['コメント数']
        }
        if video.get(FILL_MARK):
            record[FILL_MARK] = True
        channel_history[video_id]['records'][today_str] = record

    stats = channel_history.get('_channel_stats', {})
    if only_ids is not None and today_str in stats:
        stats[today_str]['総再生数'] = sum(
            (v.get('records', {}).get(today_str) or {}).get('再生数', 0)
            for vid, v in channel_history.items() if vid != '_channel_stats'
        )

    # 一覧から外れて戻ってきた動画や、収集が動かなかった日の抜けを、直前の値で埋める
    filled = fill_gaps(channel_history, on_date=today_str)
    if filled:
        print(f'  記録の抜けを直前の値で埋めました: {len(filled)}日分（{min(filled)}〜{max(filled)}）')

    history[channel_name] = channel_history
    save_json(path, history)
    print(f'  履歴保存: {path}')
    return filled

# ----------------------------------------------------------------
# Dashboard用軽量集計ファイル
# ----------------------------------------------------------------

SUMMARY_FILE = 'dashboard_summary.json'
CHANNELS_CONFIG_FILE = 'channels_config.json'
DAILY_DIR = 'daily'
DAILY_FROM = '2026-03-31'  # サイトで選べる最初の日（2026-04-01）の前日比に要るぶんから作る

def daily_path(date_str):
    return os.path.join(DAILY_DIR, f'{date_str}.json')

def write_daily_files(talent_videos, dates, rewrite=()):
    """
    サイトの日付指定・期間指定のために、日ごとの全動画の累計（再生数・高評価数・コメント数）を
    daily/YYYY-MM-DD.json に1日1ファイルで書き出す（{"date": 日付, "v": {動画ID: [再生数, 高評価数, コメント数]}}）。
    どの日・どの期間も「終わりの日の累計 − 始まりの前日の累計」で出せるので、サイトは数ファイル読むだけで済む。
    過去の日の記録は変わらないので一度作れば作り直さない。同じ日に収集し直すと値が変わるため、最新の2日分だけは毎回書き直す。
    rewrite に渡した日（記録の抜けを埋めた日）も書き直す。
    """
    recent = set(dates[-2:]) | set(rewrite)
    targets = [d for d in dates if d >= DAILY_FROM and (d in recent or not os.path.exists(daily_path(d)))]
    if not targets:
        return
    wanted = set(targets)
    per_date = {d: {} for d in targets}
    for videos in talent_videos.values():
        for vid_id, v in videos.items():
            for d, r in v.get('records', {}).items():
                if d in wanted:
                    per_date[d][vid_id] = [r.get('再生数', 0) or 0, r.get('高評価数', 0) or 0, r.get('コメント数', 0) or 0]
    os.makedirs(DAILY_DIR, exist_ok=True)
    for d in targets:
        save_json(daily_path(d), {'date': d, 'v': per_date[d]})
    print(f'  日別ファイル保存: {len(targets)}日分（{targets[0]}〜{targets[-1]}）')

def load_talent_names():
    """channels_config.jsonからタレント名一覧を取得（API/環境変数なしで動作）"""
    config = load_json(CHANNELS_CONFIG_FILE, [])
    return [c['name'] for c in config if 'name' in c]

def build_dashboard_summary(rewrite_dates=()):
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

    # 読み込み済みの履歴をそのまま使って、日付指定用の日別ファイルも書く
    write_daily_files(talent_videos, sorted_dates, rewrite=rewrite_dates)

# ----------------------------------------------------------------
# チャンネル処理
# ----------------------------------------------------------------

def process_channel(channel_config, overrides, today_str, fill_only=False):
    """
    1チャンネルの処理（スレッドセーフ：APIクライアントを個別生成）。
    fill_only（1:30 の予備の実行）のときは、今日の記録が無いチャンネルと、0時に前日の値で埋めた動画だけを取り直す。
    すでに実際の値がある記録は上書きしない（同じ日に取り直すと日次の増加が歪むため）。
    """
    channel_name = channel_config['name']
    channel_url = channel_config['url']

    print(f'\n{"=" * 50}')
    print(f'処理中: {channel_name}')
    print(f'{"=" * 50}')

    only_ids = None
    if fill_only:
        history = load_json(history_file(channel_name), {}).get(channel_name, {})
        has_today = today_str in history.get('_channel_stats', {})
        filled_today = {
            vid for vid, v in history.items()
            if vid != '_channel_stats' and (v.get('records', {}).get(today_str) or {}).get(FILL_MARK)
        }
        if has_today and not filled_today:
            print(f'  今日（{today_str}）の記録は揃っています。予備の実行では何もしません')
            return True
        if has_today:
            only_ids = filled_today
            print(f'  0時に前日の値で埋めた{len(filled_today)}本を取り直します')
        else:
            print(f'  今日（{today_str}）の記録が無いため取り直します')

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
    videos, failed, info = get_all_videos(youtube, channel_id, channel_name, overrides)
    if not videos:
        print(f'  ❌ 動画を取得できませんでした')
        return False

    # 最後まで詳細が取れなかった動画は、前日の値で埋めて記録に穴を作らない。初めて見る動画は値が無いので翌日に回す
    cached = snapshots.get(channel_name, {}).get('videos', {})
    filled = [carry_video(vid, cached[vid]) for vid in failed if vid in cached]
    unknown = [vid for vid in failed if vid not in cached]
    if filled:
        print(f'  ⚠️  [{channel_name}] {len(filled)}本は詳細が取り切れなかったため、前日の値で埋めます')
    if not info['complete']:
        report('alerts', f'{channel_name}: 一覧が総件数より少ないままでした（{info["listed"]}/{info["total"]}本）')
    if unknown:
        report('alerts', f'{channel_name}: 初めて見る{len(unknown)}本の詳細が取れず、今日は記録していません（{", ".join(unknown)}）')
    all_videos = videos + filled

    if only_ids is not None:
        # 予備の実行: 0時に埋めた動画のうち、実際の値が取れたものだけ差し替える
        replace = {v['動画ID'] for v in videos} & only_ids
        update_snapshots(channel_name, channel_id, channel_stats, all_videos, only_ids=replace)
        report('filled_dates', update_history(channel_name, all_videos, today_str, only_ids=replace))
        if replace:
            report('resolved', f'{channel_name}: 0時に前日の値で埋めた{len(replace)}本を、実際の値に差し替えました')
        if only_ids - replace:
            report('alerts', f'{channel_name}: {len(only_ids - replace)}本は予備の実行でも取れず、前日の値で埋めたままです')
        print(f'  ✓ {channel_name} 完了')
        return True

    if filled:
        report('alerts', f'{channel_name}: {len(filled)}本の詳細が取り切れず、前日の値で埋めました'
                         + ('' if fill_only else '（1:30の予備の実行で取り直します）'))
    elif fill_only:
        report('resolved', f'{channel_name}: 0時に取れなかった今日の記録を取りました')

    # 総再生数 = 全動画（Movie/Short/LiveArchive）の再生数の総和（JST 00:00時点）
    channel_stats['総再生数'] = sum(v['再生数'] for v in all_videos)

    print(f'  登録者数: {channel_stats["登録者数"]:,}人 / '
          f'総再生数: {channel_stats["総再生数"]:,}回 / '
          f'動画数: {channel_stats["動画数"]:,}本')

    # 保存
    update_snapshots(channel_name, channel_id, channel_stats, all_videos)
    report('filled_dates', update_history(channel_name, all_videos, today_str, channel_stats=channel_stats))

    print(f'  ✓ {channel_name} 完了')
    return True

def fill_channel_from_snapshot(channel_name, today_str):
    """
    予備の実行でもチャンネルごと取れなかったとき、前日のスナップショットの値で今日の記録を埋める（記録に穴を作らない最後の手段）。
    今日のチャンネル統計がすでにある（0時には取れていた）ときは何もしない。埋めた日の集まりを返す。
    """
    history = load_json(history_file(channel_name), {}).get(channel_name, {})
    if today_str in history.get('_channel_stats', {}):
        return set()
    snap = load_json(SNAPSHOTS_FILE, {}).get(channel_name)
    if not snap or not snap.get('videos'):
        return set()
    videos = [carry_video(vid, c) for vid, c in snap['videos'].items()]
    stats = dict(snap.get('channel_stats') or {})
    stats['総再生数'] = sum(v['再生数'] for v in videos)
    stats[FILL_MARK] = True
    filled = update_history(channel_name, videos, today_str, channel_stats=stats)
    return filled | {today_str}

def notify(today_str, fill_only, title=None):
    """
    取り切れなかった分があれば、GitHub の Issue で知らせる（同じ日の Issue があれば追記する）。
    予備の実行で解消したときは、その日の Issue に書き添えて閉じる。GitHub Actions の上でだけ動く。
    """
    alerts, resolved = REPORT['alerts'], REPORT['resolved']
    for line in alerts:
        print(f'⚠️  {line}')
    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    if not token or not repo or not (alerts or resolved):
        return
    title = title or f'データ収集の欠け {today_str}'
    run_url = f'{os.environ.get("GITHUB_SERVER_URL", "https://github.com")}/{repo}/actions/runs/{os.environ.get("GITHUB_RUN_ID", "")}'
    when = '予備の実行（1:30）' if fill_only else '定時の実行（0:00）'
    api = f'https://api.github.com/repos/{repo}/issues'
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'}
    try:
        found = requests.get(api, params={'state': 'open', 'per_page': 100}, headers=headers, timeout=20).json()
        number = next((i['number'] for i in found if i.get('title') == title and 'pull_request' not in i), None)
        if alerts:
            body = (f'{when}で、取り切れなかった分があります。\n\n' + '\n'.join(f'- {a}' for a in alerts)
                    + (('\n\n解消した分:\n' + '\n'.join(f'- {r}' for r in resolved)) if resolved else '')
                    + f'\n\n実行の記録: {run_url}')
            if number:
                requests.post(f'{api}/{number}/comments', json={'body': body}, headers=headers, timeout=20).raise_for_status()
            else:
                requests.post(api, json={'title': title, 'body': body}, headers=headers, timeout=20).raise_for_status()
            print(f'  通知しました（Issue「{title}」）')
        elif number:
            body = f'{when}で取り直し、解消しました。\n\n' + '\n'.join(f'- {r}' for r in resolved) + f'\n\n実行の記録: {run_url}'
            requests.post(f'{api}/{number}/comments', json={'body': body}, headers=headers, timeout=20).raise_for_status()
            requests.patch(f'{api}/{number}', json={'state': 'closed'}, headers=headers, timeout=20).raise_for_status()
            print(f'  解消したため Issue「{title}」を閉じました')
    except Exception as e:
        print(f'⚠️  通知に失敗しました: {e}')

# ----------------------------------------------------------------
# メイン
# ----------------------------------------------------------------

def main(fill_only=False):
    now = datetime.now(timezone(timedelta(hours=9)))
    today_str = now.strftime('%Y-%m-%d')

    print('=' * 50)
    print('YouTube統計 自動チェック開始' + ('（予備の実行: 今日の記録が欠けている分だけ取る）' if fill_only else ''))
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
                process_channel, ch, overrides, today_str, fill_only
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
                    process_channel, ch, overrides, today_str, fill_only
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

    for name in still_failed:
        if fill_only:
            # 予備の実行でも取れなかった。前日の値で埋めて記録に穴を作らない
            filled = fill_channel_from_snapshot(name, today_str)
            report('filled_dates', filled)
            report('alerts', f'{name}: 予備の実行でもチャンネルごと取得できず'
                             + ('、今日の記録を前日の値で埋めました' if filled else 'ました'))
        else:
            report('alerts', f'{name}: チャンネルごと取得できませんでした（1:30の予備の実行で取り直します）')

    print(f'\n{"=" * 50}')
    print(f'✓ 全処理完了: {success}/{len(CHANNELS)} チャンネル成功')
    print('=' * 50)

    try:
        build_dashboard_summary(rewrite_dates=REPORT['filled_dates'])
    except Exception as e:
        print(f'⚠️  dashboard_summary.json 生成に失敗しました（本処理には影響しません）: {e}')

    notify(today_str, fill_only)

    if still_failed:
        print(f'❌ リトライ後も失敗: {", ".join(still_failed)}')
        sys.exit(1)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary-only', action='store_true',
                         help='既存のhistory_*.jsonからdashboard_summary.jsonのみ再生成（YouTube API呼び出しなし）')
    parser.add_argument('--fill-only', action='store_true',
                        help='予備の実行（1:30）。今日の記録が無いチャンネルと、0時に前日の値で埋めた動画だけを取り直す')
    parser.add_argument('--alert-test', action='store_true',
                        help='通知（GitHub の Issue）のテストだけを行う。データには触れない')
    args = parser.parse_args()

    if args.summary_only:
        build_dashboard_summary()
    elif args.alert_test:
        report('alerts', 'これは通知のテストです。データには触れていません。確認できたらこの Issue は閉じてください')
        notify(datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d'), False, title='データ収集の欠け（通知のテスト）')
    else:
        main(fill_only=args.fill_only)
