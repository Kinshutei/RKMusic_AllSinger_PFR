#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
動画履歴データを日次集約するスクリプト

6時間ごとに収集されたデータを、1日1レコードに集約します。
各日の最終記録（その日の最も遅い時刻のデータ）を採用します。
"""

import json
import os
from datetime import datetime
from collections import defaultdict

def aggregate_daily_data(input_file, output_file):
    """
    生データを日次集約する
    
    Args:
        input_file: 入力ファイル（video_daily_history_*.json）
        output_file: 出力ファイル（video_daily_aggregated_*.json）
    """
    print(f"📊 処理開始: {input_file}")
    
    # データ読み込み
    if not os.path.exists(input_file):
        print(f"⚠️  ファイルが見つかりません: {input_file}")
        return
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    aggregated_data = {}
    total_videos = len(data)
    processed_videos = 0
    
    # 動画ごとに処理
    for video_id, video_info in data.items():
        records = video_info.get('records', [])
        
        if not records:
            continue
        
        # 日付ごとにグループ化
        daily_records = defaultdict(list)
        
        for record in records:
            timestamp_str = record.get('timestamp', '')
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                date_key = timestamp.strftime('%Y-%m-%d')  # 日付のみ
                daily_records[date_key].append({
                    'timestamp': timestamp,
                    'record': record
                })
            except ValueError:
                print(f"⚠️  無効なタイムスタンプをスキップ: {timestamp_str}")
                continue
        
        # 各日付の最終レコードを選択
        aggregated_records = []
        for date_key in sorted(daily_records.keys()):
            # その日の最も遅い時刻のレコードを取得
            latest = max(daily_records[date_key], key=lambda x: x['timestamp'])
            aggregated_records.append(latest['record'])
        
        # 集約データに追加
        aggregated_data[video_id] = {
            'タイトル': video_info.get('タイトル', ''),
            '公開日': video_info.get('公開日', ''),
            'type': video_info.get('type', 'Movie'),
            'records': aggregated_records
        }
        
        processed_videos += 1
        
        # 進捗表示
        if processed_videos % 10 == 0 or processed_videos == total_videos:
            print(f"  処理中... {processed_videos}/{total_videos} 動画")
    
    # 保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(aggregated_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 完了: {output_file}")
    print(f"   - 処理した動画数: {processed_videos}")
    
    # 統計情報
    total_records_before = sum(len(v.get('records', [])) for v in data.values())
    total_records_after = sum(len(v.get('records', [])) for v in aggregated_data.values())
    print(f"   - レコード数: {total_records_before} → {total_records_after}")
    print(f"   - 削減率: {(1 - total_records_after/total_records_before)*100:.1f}%")
    print()

def main():
    """メイン処理"""
    print("=" * 60)
    print("📅 動画履歴データ日次集約スクリプト")
    print("=" * 60)
    print()
    
    # タレントリストを取得
    talents = []
    for file in os.listdir('.'):
        if file.startswith('video_daily_history_') and file.endswith('.json'):
            talent_name = file.replace('video_daily_history_', '').replace('.json', '')
            talents.append(talent_name)
    
    if not talents:
        print("⚠️  処理対象のファイルが見つかりません。")
        print("   video_daily_history_*.json ファイルをカレントディレクトリに配置してください。")
        return
    
    print(f"🎯 処理対象タレント: {', '.join(talents)}")
    print()
    
    # 各タレントのデータを集約
    for talent in talents:
        input_file = f'video_daily_history_{talent}.json'
        output_file = f'video_daily_aggregated_{talent}.json'
        aggregate_daily_data(input_file, output_file)
    
    print("=" * 60)
    print("🎉 すべての処理が完了しました！")
    print("=" * 60)

if __name__ == '__main__':
    main()
