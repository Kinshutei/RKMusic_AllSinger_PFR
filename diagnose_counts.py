#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
収集の欠けを防ぐ改修の前に、YouTube API の数え方を確かめるための確認用スクリプト（データには書き込まない）。
diagnose.yml から手動で1回だけ実行し、結果はログに出す。

確かめること:
  1. 一覧のAPI（playlistItems）が返す総件数 pageInfo.totalResults は、実際に一覧から受け取れたIDの数と合うか。
     全体（UU）とタブ別（動画 UULF / ショート UUSH / ライブ UULV）のそれぞれで見る。
     あわせて、ページごとに「一覧から受け取ったID数」と「動画の詳細（videos.list）で返ってきた数」を突き合わせる。
  2. 収集から外れた動画（履歴にはあるが最新のスナップショットに無いもの）は、IDを指定すれば videos.list で取れるか。
     取れる場合の公開状態（status.privacyStatus）と、埋め込み情報（oEmbed）の応答コードも並べる。
"""

import os
import sys
import json
from collections import Counter

import requests
from googleapiclient.discovery import build

from auto_check import execute_with_retry, load_json, history_file, SNAPSHOTS_FILE

API_KEY = os.environ.get('YOUTUBE_API_KEY')
CHANNELS = json.loads(os.environ.get('CHANNELS', '[]') or '[]')
DROPPED_SINCE = '2026-06-01'   # これ以降まで記録があって、今は収集から外れている動画を調べる
PLAYLISTS = (('UU', '全体'), ('UULF', '動画'), ('UUSH', 'ショート'), ('UULV', 'ライブ'))


def list_playlist(youtube, playlist_id, with_details=False):
    """一覧を最後まで読み、総件数・ページ数・受け取ったID、（with_details なら）ページごとの詳細の返り数を返す"""
    total_results = None
    ids = []
    pages = []
    token = None
    while True:
        resp = execute_with_retry(youtube.playlistItems().list(
            part='contentDetails', playlistId=playlist_id, maxResults=50, pageToken=token))
        if total_results is None:
            total_results = resp.get('pageInfo', {}).get('totalResults')
        page_ids = [it['contentDetails']['videoId'] for it in resp.get('items', [])]
        ids += page_ids
        page = {'listed': len(page_ids)}
        if with_details and page_ids:
            vresp = execute_with_retry(youtube.videos().list(part='id', id=','.join(page_ids)))
            got = {it['id'] for it in vresp.get('items', [])}
            page['returned'] = len(got)
            page['missing'] = [v for v in page_ids if v not in got]
        pages.append(page)
        token = resp.get('nextPageToken')
        if not token:
            break
    return total_results, ids, pages


def oembed_status(video_id):
    try:
        return requests.get('https://www.youtube.com/oembed',
                            params={'url': f'https://www.youtube.com/watch?v={video_id}', 'format': 'json'},
                            timeout=10).status_code
    except Exception:
        return 'ERR'


def main():
    if not API_KEY or not CHANNELS:
        print('❌ YOUTUBE_API_KEY または CHANNELS が設定されていません')
        sys.exit(1)
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    snapshots = load_json(SNAPSHOTS_FILE, {})
    summary = {}

    print('=' * 60)
    print('1. 一覧の総件数と、実際に受け取れた本数')
    print('=' * 60)
    for ch in CHANNELS:
        name = ch['name']
        snap = snapshots.get(name, {})
        cid = snap.get('channel_id')
        if not cid:
            print(f'\n■ {name}: チャンネルIDがスナップショットに無いため飛ばします')
            continue
        stats = execute_with_retry(youtube.channels().list(part='statistics', id=cid))
        video_count = int(stats['items'][0]['statistics'].get('videoCount', 0)) if stats.get('items') else None

        print(f'\n■ {name}（チャンネル情報の動画数 {video_count} / 最新のスナップショット {len(snap.get("videos", {}))}本）')
        row = {'videoCount': video_count, 'snapshot': len(snap.get('videos', {}))}
        tab_ids = {}
        uu_ids = None
        for prefix, label in PLAYLISTS:
            try:
                total, ids, pages = list_playlist(youtube, prefix + cid[2:], with_details=(prefix == 'UU'))
            except Exception as e:
                print(f'  {label}（{prefix}）: 読めませんでした: {e}')
                row[prefix] = {'error': str(e)}
                continue
            uniq = set(ids)
            line = (f'  {label}（{prefix}）: 総件数 {total} / 受け取ったID {len(ids)}'
                    f'（重複を除くと {len(uniq)}） / {len(pages)}ページ')
            if total != len(uniq):
                line += f'  ← 差 {total - len(uniq)}'
            print(line)
            row[prefix] = {'totalResults': total, 'listed': len(ids), 'unique': len(uniq), 'pages': len(pages)}
            if prefix == 'UU':
                short_pages = [(i + 1, p['listed'], p['returned']) for i, p in enumerate(pages)
                               if p.get('returned') is not None and p['returned'] != p['listed']]
                for no, listed, returned in short_pages:
                    print(f'    {no}ページ目: 一覧から{listed}本、詳細で返ってきたのは{returned}本')
                row['UU']['detail_short_pages'] = short_pages
                row['UU']['detail_missing'] = sum(len(p.get('missing', [])) for p in pages)
                uu_ids = uniq
                snap_ids = set(snap.get('videos', {}))
                print(f'    スナップショットにあって一覧に無い {len(snap_ids - uniq)}本 / '
                      f'一覧にあってスナップショットに無い {len(uniq - snap_ids)}本（スナップショット後の新着を含む）')
                row['UU']['snap_not_listed'] = len(snap_ids - uniq)
                row['UU']['listed_not_snap'] = len(uniq - snap_ids)
            else:
                tab_ids[prefix] = uniq
        if tab_ids and uu_ids is not None:
            in_tabs = set().union(*tab_ids.values())
            print(f'  タブの合計 {sum(len(v) for v in tab_ids.values())}本 / 全体にあってどのタブにも無い '
                  f'{len(uu_ids - in_tabs)}本 / タブにあって全体に無い {len(in_tabs - uu_ids)}本')
            row['tabs_sum'] = sum(len(v) for v in tab_ids.values())
            row['uu_not_in_tabs'] = len(uu_ids - in_tabs)
            row['tabs_not_in_uu'] = len(in_tabs - uu_ids)
        summary[name] = row

    print('\n' + '=' * 60)
    print(f'2. 収集から外れた動画（{DROPPED_SINCE}以降まで記録があり、最新のスナップショットに無いもの）')
    print('=' * 60)
    dropped = []
    for ch in CHANNELS:
        name = ch['name']
        hist = load_json(history_file(name), {}).get(name, {})
        snap_ids = set(snapshots.get(name, {}).get('videos', {}))
        for vid, v in hist.items():
            if vid.startswith('_') or vid in snap_ids:
                continue
            ds = sorted(v.get('records', {}))
            if ds and ds[-1] >= DROPPED_SINCE:
                dropped.append((name, vid, ds[-1], v.get('タイトル', '')))
    print(f'対象 {len(dropped)}本')

    found = {}
    for i in range(0, len(dropped), 50):
        batch = [d[1] for d in dropped[i:i + 50]]
        resp = execute_with_retry(youtube.videos().list(part='status,snippet', id=','.join(batch)))
        for it in resp.get('items', []):
            found[it['id']] = {'privacy': it.get('status', {}).get('privacyStatus'),
                               'channel': it.get('snippet', {}).get('channelTitle')}
    tally = Counter()
    rows = []
    for name, vid, last, title in dropped:
        code = oembed_status(vid)
        f = found.get(vid)
        key = (('IDで取れる', f['privacy']) if f else ('IDで取れない', '-'), code)
        tally[key] += 1
        if f or code == 200:
            rows.append(f'  {name} {vid} 最終記録 {last} / IDで{"取れる(" + str(f["privacy"]) + ")" if f else "取れない"}'
                        f' / oEmbed {code} / {title[:40]}')
    for (got, code), n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f'  {got[0]}（公開状態: {got[1]}）・oEmbed {code}: {n}本')
    if rows:
        print('  --- IDで取れる、または oEmbed が200のもの')
        print('\n'.join(rows))
    summary['_dropped'] = {f'{g[0]}|{g[1]}|{c}': n for (g, c), n in tally.items()}

    print('\nDIAG_JSON:' + json.dumps(summary, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    main()
