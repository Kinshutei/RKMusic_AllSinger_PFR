#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
既存の all_history_{year}.json に duration（秒）フィールドを追記する一回限りのスクリプト

使い方:
    YOUTUBE_API_KEY=<your_key> python backfill_duration.py [--year 2026]
"""

import os
import json
import sys
import argparse
from googleapiclient.discovery import build
import isodate


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', default='2026')
    args = parser.parse_args()

    api_key = os.environ.get('YOUTUBE_API_KEY')
    if not api_key:
        print('❌ YOUTUBE_API_KEY が設定されていません')
        sys.exit(1)

    history_file = f'all_history_{args.year}.json'
    if not os.path.exists(history_file):
        print(f'❌ ファイルが見つかりません: {history_file}')
        sys.exit(1)

    print(f'読み込み中: {history_file}')
    history = load_json(history_file)

    # duration未設定の動画IDを収集
    missing_ids = []
    for singer, data in history.items():
        for vid_id, entry in data.items():
            if vid_id == '_channel_stats':
                continue
            if isinstance(entry, dict) and 'duration' not in entry:
                missing_ids.append(vid_id)

    print(f'duration未設定: {len(missing_ids)}件')
    if not missing_ids:
        print('✓ 全件設定済みです')
        return

    youtube = build('youtube', 'v3', developerKey=api_key)

    # バッチ取得（50件ずつ）
    duration_map = {}
    for i in range(0, len(missing_ids), 50):
        batch = missing_ids[i:i + 50]
        resp = youtube.videos().list(
            part='contentDetails',
            id=','.join(batch)
        ).execute()
        for item in resp.get('items', []):
            try:
                d = isodate.parse_duration(item['contentDetails']['duration'])
                duration_map[item['id']] = int(d.total_seconds())
            except Exception:
                duration_map[item['id']] = 0
        done = min(i + 50, len(missing_ids))
        print(f'  取得済み: {done}/{len(missing_ids)}件')

    # 書き込み
    updated = 0
    not_found = 0
    for singer, data in history.items():
        for vid_id, entry in data.items():
            if vid_id == '_channel_stats':
                continue
            if not isinstance(entry, dict):
                continue
            if 'duration' not in entry:
                if vid_id in duration_map:
                    entry['duration'] = duration_map[vid_id]
                    updated += 1
                else:
                    entry['duration'] = 0
                    not_found += 1

    save_json(history_file, history)
    print(f'✓ 完了: {updated}件更新 / {not_found}件はAPIで見つからず0を設定')


if __name__ == '__main__':
    main()
