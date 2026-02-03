#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube チャンネル統計 自動チェックスクリプト（複数チャンネル対応版）
GitHub Actionsで定期実行される
Movie/Short/LiveArchive判別機能付き（ShortはURL判定）
"""

import os
import json
import requests
from datetime import datetime
from googleapiclient.discovery import build
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 環境変数から設定を読み込み
API_KEY = os.environ.get('YOUTUBE_API_KEY')
CHANNELS_JSON = os.environ.get('CHANNELS', '[]')
EMAIL_ENABLED = os.environ.get('EMAIL_ENABLED', 'false').lower() == 'true'
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', '')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL', '')

# チャンネル設定をパース
try:
    CHANNELS = json.loads(CHANNELS_JSON)
except:
    CHANNELS = []

# キリ番のリスト
MILESTONES = [5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 10000000]

def is_short_video(video_id):
    """動画IDがShortsかどうかをURLで判別"""
    try:
        shorts_url = f"https://www.youtube.com/shorts/{video_id}"
        response = requests.head(shorts_url, allow_redirects=True, timeout=5)
        # Shortsページが存在すればShort
        return 'shorts' in response.url.lower()
    except Exception as e:
        # エラーの場合はShortではないと判断
        return False

def determine_video_type(video):
    """動画タイプを判定（Movie/Short/LiveArchive）"""
    # liveStreamingDetailsがあればLiveArchive
    if 'liveStreamingDetails' in video:
        return 'LiveArchive'
    
    # liveBroadcastContentで判定
    live_broadcast = video.get('snippet', {}).get('liveBroadcastContent', 'none')
    if live_broadcast in ['live', 'upcoming']:
        return 'LiveArchive'
    
    # ShortかどうかをURLで判定
    video_id = video['id']
    if is_short_video(video_id):
        return 'Short'
    
    # デフォルトはMovie
    return 'Movie'

def send_email_notification(achievements, channel_name):
    """キリ番達成をメールで通知"""
    if not EMAIL_ENABLED or not achievements:
        return False
    
    try:
        # メール本文を作成
        subject = f"🎉 [{channel_name}] YouTubeキリ番達成通知 - {len(achievements)}件"
        
        body = f"[{channel_name}] YouTubeチャンネルでキリ番を達成しました！\n\n"
        body += "=" * 50 + "\n\n"
        
        for i, achievement in enumerate(achievements, 1):
            body += f"【{i}】{achievement['タイトル']}\n"
            body += f"   🎯 {achievement['キリ番']:,}回再生を突破！\n"
            body += f"   現在の再生数: {achievement['現在の再生数']:,}回\n"
            body += f"   タイプ: {achievement.get('type', 'N/A')}\n"
            body += f"   動画URL: https://www.youtube.com/watch?v={achievement['動画ID']}\n\n"
        
        body += "=" * 50 + "\n"
        body += f"通知日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n"
        
        # MIMEメッセージを作成
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Gmailサーバーに接続して送信
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        
        return True
    
    except Exception as e:
        print(f"メール送信エラー: {str(e)}")
        return False

def get_channel_id(youtube, channel_url):
    """チャンネルURLからチャンネルIDを取得"""
    try:
        if '@' in channel_url:
            handle = channel_url.split('@')[-1]
            request = youtube.search().list(
                part='snippet',
                q=handle,
                type='channel',
                maxResults=1
            )
            response = request.execute()
            if response['items']:
                return response['items'][0]['snippet']['channelId']
    except Exception as e:
        print(f"エラー: {str(e)}")
    return None

def get_channel_stats(youtube, channel_id):
    """チャンネルの統計情報を取得"""
    try:
        request = youtube.channels().list(
            part='statistics,snippet',
            id=channel_id
        )
        response = request.execute()
        
        if response['items']:
            item = response['items'][0]
            return {
                'チャンネル名': item['snippet']['title'],
                '登録者数': int(item['statistics']['subscriberCount']),
                '総再生数': int(item['statistics']['viewCount']),
                '動画数': int(item['statistics']['videoCount']),
                '取得日時': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    except Exception as e:
        print(f"エラー: {str(e)}")
    return None

def get_all_videos(youtube, channel_id):
    """チャンネルの全動画情報を取得（Movie/Short/LiveArchive判別付き）"""
    videos = []
    
    try:
        # アップロードプレイリストIDを取得
        request = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        )
        response = request.execute()
        
        if not response['items']:
            return videos
        
        playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        next_page_token = None
        
        while True:
            playlist_request = youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            playlist_response = playlist_request.execute()
            
            video_ids = [item['snippet']['resourceId']['videoId'] 
                        for item in playlist_response['items']]
            
            # 動画の詳細情報を取得
            videos_request = youtube.videos().list(
                part='snippet,statistics,liveStreamingDetails',
                id=','.join(video_ids)
            )
            videos_response = videos_request.execute()
            
            print(f"取得中... {len(videos)}本の動画を取得しました")
            
            for video in videos_response['items']:
                video_type = determine_video_type(video)
                
                video_data = {
                    '動画ID': video['id'],
                    'タイトル': video['snippet']['title'],
                    '公開日': video['snippet']['publishedAt'][:10],
                    '再生数': int(video['statistics'].get('viewCount', 0)),
                    'いいね数': int(video['statistics'].get('likeCount', 0)),
                    'コメント数': int(video['statistics'].get('commentCount', 0)),
                    'type': video_type
                }
                videos.append(video_data)
                
                # 進捗表示
                if len(videos) % 10 == 0:
                    print(f"  判別中... {len(videos)}本完了")
            
            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                break
        
        print(f"✓ 完了: {len(videos)}本の動画を取得しました")
        print(f"  - Movie: {sum(1 for v in videos if v['type'] == 'Movie')}本")
        print(f"  - Short: {sum(1 for v in videos if v['type'] == 'Short')}本")
        print(f"  - LiveArchive: {sum(1 for v in videos if v['type'] == 'LiveArchive')}本")
        
    except Exception as e:
        print(f"エラー: {str(e)}")
    
    return videos

def load_history(channel_name):
    """過去のデータを読み込む"""
    history_file = f'video_history_{channel_name}.json'
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_history(videos, channel_stats, channel_name):
    """現在のデータを保存"""
    history_file = f'video_history_{channel_name}.json'
    history_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'channel_stats': channel_stats,
        'videos': {video['動画ID']: {
            '再生数': video['再生数'],
            'type': video['type']
        } for video in videos}
    }
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)
    print(f"履歴を保存しました: {history_file}")

def save_log(videos, channel_stats, achievements, channel_name):
    """ログファイルに追記"""
    log_file = f'check_log_{channel_name}.json'
    
    # 既存ログを読み込み
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except:
            logs = []
    else:
        logs = []
    
    # 新しいログエントリを追加
    log_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'channel_stats': channel_stats,
        'total_videos': len(videos),
        'movie_count': sum(1 for v in videos if v['type'] == 'Movie'),
        'short_count': sum(1 for v in videos if v['type'] == 'Short'),
        'archive_count': sum(1 for v in videos if v['type'] == 'LiveArchive'),
        'achievements': achievements
    }
    logs.append(log_entry)
    
    # 最新100件のみ保持
    logs = logs[-100:]
    
    # 保存
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)
    print(f"ログを保存しました: {log_file}")

def save_video_daily_history(videos, channel_name):
    """動画ごとの履歴を保存"""
    history_file = f'video_daily_history_{channel_name}.json'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 既存履歴を読み込み
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = {}
    else:
        history = {}
    
    # 各動画の履歴を追加
    for video in videos:
        video_id = video['動画ID']
        
        if video_id not in history:
            history[video_id] = {
                'タイトル': video['タイトル'],
                '公開日': video['公開日'],
                'type': video['type'],
                'records': []
            }
        
        # 新しいレコードを追加
        history[video_id]['records'].append({
            'timestamp': timestamp,
            '再生数': video['再生数'],
            'いいね数': video['いいね数'],
            'コメント数': video['コメント数']
        })
        
        # タイトルとタイプを更新
        history[video_id]['タイトル'] = video['タイトル']
        history[video_id]['type'] = video['type']
    
    # 保存
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    print(f"動画別履歴を保存しました: {history_file}")

def check_milestones(current_videos, history):
    """キリ番達成をチェック"""
    achievements = []
    
    if not history or 'videos' not in history:
        return achievements
    
    old_data = history['videos']
    
    for video in current_videos:
        video_id = video['動画ID']
        current_views = video['再生数']
        
        if video_id in old_data:
            old_views = old_data[video_id]['再生数']
            
            # 突破したキリ番を検出
            for milestone in MILESTONES:
                if old_views < milestone <= current_views:
                    achievements.append({
                        'タイトル': video['タイトル'],
                        'キリ番': milestone,
                        '現在の再生数': current_views,
                        '動画ID': video_id,
                        'type': video['type']
                    })
    
    return achievements

def process_channel(youtube, channel_config):
    """1つのチャンネルを処理"""
    channel_name = channel_config['name']
    channel_url = channel_config['url']
    
    print("\n" + "=" * 50)
    print(f"処理中: {channel_name}")
    print("=" * 50)
    
    # チャンネルIDを取得
    print(f"\nチャンネルURL: {channel_url}")
    channel_id = get_channel_id(youtube, channel_url)
    
    if not channel_id:
        print(f"❌ エラー: {channel_name} のチャンネルが見つかりませんでした")
        return False
    
    print(f"チャンネルID: {channel_id}")
    
    # チャンネル統計を取得
    print("\nチャンネル情報を取得中...")
    channel_stats = get_channel_stats(youtube, channel_id)
    
    if not channel_stats:
        print(f"❌ エラー: {channel_name} のチャンネル情報を取得できませんでした")
        return False
    
    print(f"チャンネル名: {channel_stats['チャンネル名']}")
    print(f"登録者数: {channel_stats['登録者数']:,}人")
    print(f"総再生数: {channel_stats['総再生数']:,}回")
    print(f"動画数: {channel_stats['動画数']:,}本")
    
    # 全動画情報を取得
    print("\n全動画情報を取得中...")
    videos = get_all_videos(youtube, channel_id)
    
    if not videos:
        print(f"❌ エラー: {channel_name} の動画情報を取得できませんでした")
        return False
    
    # 履歴を読み込み
    history = load_history(channel_name)
    
    # キリ番チェック
    achievements = check_milestones(videos, history)
    
    if achievements:
        print(f"\n🎉 キリ番達成: {len(achievements)}件")
        for achievement in achievements:
            print(f"  - {achievement['タイトル']}: {achievement['キリ番']:,}回突破 [{achievement['type']}]")
        
        # メール通知
        if EMAIL_ENABLED:
            if send_email_notification(achievements, channel_name):
                print("✉️ メール通知を送信しました")
    else:
        print("\n新しいキリ番達成はありませんでした")
    
    # データを保存
    save_history(videos, channel_stats, channel_name)
    save_log(videos, channel_stats, achievements, channel_name)
    save_video_daily_history(videos, channel_name)
    
    print(f"\n✓ {channel_name} の処理完了")
    return True

def main():
    """メイン処理"""
    print("=" * 50)
    print("YouTube統計 自動チェック開始（複数チャンネル対応）")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    if not API_KEY:
        print("❌ エラー: YouTube API キーが設定されていません")
        return
    
    if not CHANNELS:
        print("❌ エラー: チャンネル設定が見つかりません")
        return
    
    print(f"\n処理対象チャンネル数: {len(CHANNELS)}")
    for ch in CHANNELS:
        print(f"  - {ch['name']}")
    
    # YouTube API クライアントを作成
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    # 各チャンネルを処理
    success_count = 0
    for channel_config in CHANNELS:
        if process_channel(youtube, channel_config):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"✓ 全処理完了: {success_count}/{len(CHANNELS)} チャンネル成功")
    print("=" * 50)

if __name__ == '__main__':
    main()
