#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube チャンネル統計 自動チェックスクリプト（複数チャンネル対応・並列処理版）
GitHub Actionsで定期実行される
Movie/Short/LiveArchive判別機能付き（Short判定は並列処理で高速化）
タイプ自動修正機能付き
"""

import os
import json
import requests
from datetime import datetime
from googleapiclient.discovery import build
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import isodate

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

# 並列処理の設定
MAX_WORKERS = 10  # Short判定の同時実行数

def generate_view_milestones(max_value=100000000):
    """再生数のキリ番を生成"""
    milestones = [500]  # 最初のキリ番
    
    # 1,000～9,000（1,000刻み）
    for i in range(1000, 10000, 1000):
        milestones.append(i)
    
    # 10,000以降（5,000刻み）
    current = 10000
    while current <= max_value:
        milestones.append(current)
        current += 5000
    
    return milestones

def generate_like_milestones(max_value=1000000):
    """高評価数のキリ番を生成"""
    milestones = []
    
    # 100刻み
    current = 100
    while current <= max_value:
        milestones.append(current)
        current += 100
    
    return milestones

def get_duration_minutes(video):
    """動画の長さを分単位で取得"""
    try:
        duration_str = video['contentDetails']['duration']
        duration = isodate.parse_duration(duration_str)
        return duration.total_seconds() / 60
    except:
        return 0

def load_video_type_overrides():
    """例外設定ファイルを読み込む"""
    override_file = 'video_type_overrides.json'
    if os.path.exists(override_file):
        try:
            with open(override_file, 'r', encoding='utf-8') as f:
                overrides = json.load(f)
                print(f"✓ 例外設定を読み込みました: {sum(len(v) for v in overrides.values())}件")
                return overrides
        except Exception as e:
            print(f"⚠️ 例外設定の読み込みエラー: {str(e)}")
            return {}
    return {}

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

def check_shorts_batch(video_ids):
    """複数の動画IDを並列でShortチェック"""
    results = {}
    
    if not video_ids:
        return results
    
    print(f"  並列Short判定開始: {len(video_ids)}本 (最大{MAX_WORKERS}並列)")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 全ての動画IDに対してShortチェックを投入
        future_to_id = {
            executor.submit(is_short_video, vid): vid 
            for vid in video_ids
        }
        
        # 完了したものから結果を取得
        completed = 0
        for future in as_completed(future_to_id):
            video_id = future_to_id[future]
            try:
                results[video_id] = future.result()
                completed += 1
                if completed % 20 == 0:
                    print(f"    → {completed}/{len(video_ids)}本完了")
            except Exception as e:
                print(f"  ⚠️ Short判定エラー [{video_id}]: {str(e)}")
                results[video_id] = False
    
    elapsed = time.time() - start_time
    short_count = sum(1 for v in results.values() if v)
    print(f"  並列Short判定完了: {elapsed:.1f}秒 ({short_count}本がShort)")
    
    return results

def determine_video_type(video, short_cache=None, overrides=None, channel_name=None):
    """動画タイプを判定（例外設定優先）
    
    判定順序：
    1. 例外設定（video_type_overrides.json）← 最優先
    2. Short: キャッシュから判定（事前に並列取得済み）またはURL判定
    3. LiveArchive/Movie: duration（5分未満=Movie, 5分以上=LiveArchive）
    4. Movie: それ以外
    
    Args:
        video: YouTube API からの動画データ
        short_cache: 事前に取得したShort判定結果のキャッシュ（dict）
        overrides: 例外設定（dict）
        channel_name: チャンネル名
    """
    video_id = video['id']
    
    # 1. 例外設定をチェック（最優先）
    if overrides and channel_name and channel_name in overrides:
        if video_id in overrides[channel_name]:
            override_type = overrides[channel_name][video_id]
            print(f"  ⚙️ 例外設定適用: [{video['snippet']['title'][:40]}...] → {override_type}")
            return override_type
    
    # 2. Shortかどうかを判定
    if short_cache is not None:
        # キャッシュから判定（並列処理済み）
        if short_cache.get(video_id, False):
            return 'Short'
    else:
        # キャッシュがない場合は直接判定（フォールバック）
        if is_short_video(video_id):
            return 'Short'
    
    # 3. ライブ配信のアーカイブかチェック
    live_broadcast_content = video['snippet'].get('liveBroadcastContent', 'none')
    if live_broadcast_content == 'completed':
        # 動画の長さで判定（5分未満=Movie, 5分以上=LiveArchive）
        duration_minutes = get_duration_minutes(video)
        if duration_minutes < 5:
            return 'Movie'  # プレミア公開のMV
        else:
            return 'LiveArchive'  # 通常の配信
    
    # liveStreamingDetailsがある場合も念のためチェック（フォールバック）
    if 'liveStreamingDetails' in video:
        if 'actualStartTime' in video['liveStreamingDetails']:
            duration_minutes = get_duration_minutes(video)
            if duration_minutes < 5:
                return 'Movie'
            else:
                return 'LiveArchive'
    
    # 4. それ以外はMovie（通常動画、プレミア公開含む）
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
            metric_type = achievement['タイプ']
            emoji = "📺" if metric_type == "再生数" else "👍"
            unit = "回" if metric_type == "再生数" else "件"
            
            body += f"【{i}】{achievement['タイトル']}\n"
            body += f"   {emoji} {metric_type}: {achievement['キリ番']:,}{unit}を突破！\n"
            body += f"   現在の{metric_type}: {achievement['現在の値']:,}{unit}\n"
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
    """チャンネルの統計情報を取得（バナー画像URLも含む）"""
    try:
        request = youtube.channels().list(
            part='statistics,snippet,brandingSettings',
            id=channel_id
        )
        response = request.execute()
        
        if response['items']:
            item = response['items'][0]
            
            # バナー画像URLを取得（存在しない場合はNone）
            banner_url = None
            try:
                banner_url = item['brandingSettings']['image']['bannerExternalUrl']
            except:
                pass
            
            return {
                'チャンネル名': item['snippet']['title'],
                '登録者数': int(item['statistics']['subscriberCount']),
                '総再生数': int(item['statistics']['viewCount']),
                '動画数': int(item['statistics']['videoCount']),
                'バナー画像URL': banner_url,
                '取得日時': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    except Exception as e:
        print(f"エラー: {str(e)}")
    return None

def get_all_videos(youtube, channel_id, channel_name, overrides):
    """チャンネルの全動画情報を取得（並列Short判定版・例外設定対応）"""
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
            
            # 動画の詳細情報を取得（contentDetails追加）
            videos_request = youtube.videos().list(
                part='snippet,statistics,liveStreamingDetails,contentDetails',
                id=','.join(video_ids)
            )
            videos_response = videos_request.execute()
            
            print(f"取得中... {len(videos)}本の動画を取得しました")
            
            # Short判定を並列実行（ここが改善点！）
            short_cache = check_shorts_batch(video_ids)
            
            # 各動画のタイプを判定（キャッシュ・例外設定使用）
            for video in videos_response['items']:
                video_type = determine_video_type(video, short_cache, overrides, channel_name)
                
                video_data = {
                    '動画ID': video['id'],
                    'タイトル': video['snippet']['title'],
                    '公開日': video['snippet']['publishedAt'][:10],
                    '再生数': int(video['statistics'].get('viewCount', 0)),
                    '高評価数': int(video['statistics'].get('likeCount', 0)),
                    'コメント数': int(video['statistics'].get('commentCount', 0)),
                    'type': video_type
                }
                videos.append(video_data)
            
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
    """現在のデータを保存（タイプ自動修正機能付き）"""
    history_file = f'video_history_{channel_name}.json'
    
    # 既存データを読み込んでタイプ変更を検出
    old_data = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                old_history = json.load(f)
                old_data = old_history.get('videos', {})
        except:
            pass
    
    # 新しいデータを作成
    history_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'channel_stats': channel_stats,
        'videos': {video['動画ID']: {
            '再生数': video['再生数'],
            '高評価数': video['高評価数'],
            'type': video['type']
        } for video in videos}
    }
    
    # タイプ変更をカウント（video_daily_historyと重複するが、整合性のため）
    type_changes = 0
    for video in videos:
        video_id = video['動画ID']
        if video_id in old_data:
            old_type = old_data[video_id].get('type', 'Unknown')
            new_type = video['type']
            if old_type != new_type and old_type != 'Unknown':
                type_changes += 1
    
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)
    
    if type_changes > 0:
        print(f"履歴を保存しました: {history_file} ({type_changes}件のタイプ修正)")
    else:
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
    """動画ごとの履歴を保存（タイプ自動修正機能付き）"""
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
    
    # タイプ変更のカウンター
    type_changes = {'Movie': 0, 'Short': 0, 'LiveArchive': 0}
    type_change_details = []
    
    # 各動画の履歴を追加
    for video in videos:
        video_id = video['動画ID']
        new_type = video['type']
        
        if video_id not in history:
            # 新規動画
            history[video_id] = {
                'タイトル': video['タイトル'],
                '公開日': video['公開日'],
                'type': new_type,
                'records': []
            }
        else:
            # 既存動画：タイプをチェック
            old_type = history[video_id].get('type', 'Unknown')
            
            if old_type != new_type:
                # タイプが変更された
                print(f"  🔄 タイプ修正: [{video['タイトル'][:40]}...] {old_type} → {new_type}")
                type_changes[new_type] += 1
                type_change_details.append({
                    'タイトル': video['タイトル'],
                    '動画ID': video_id,
                    '旧タイプ': old_type,
                    '新タイプ': new_type
                })
                # タイプを更新
                history[video_id]['type'] = new_type
        
        # 新しいレコードを追加
        history[video_id]['records'].append({
            'timestamp': timestamp,
            '再生数': video['再生数'],
            '高評価数': video['高評価数'],
            'コメント数': video['コメント数']
        })
        
        # タイトルを更新（変更された場合に対応）
        history[video_id]['タイトル'] = video['タイトル']
    
    # 保存
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    print(f"動画別履歴を保存しました: {history_file}")
    
    # タイプ変更があった場合は集計を表示
    if any(count > 0 for count in type_changes.values()):
        total_changes = sum(type_changes.values())
        print(f"\n📝 タイプ修正サマリー: {total_changes}件")
        if type_changes['Movie'] > 0:
            print(f"  → Movie: {type_changes['Movie']}件")
        if type_changes['Short'] > 0:
            print(f"  → Short: {type_changes['Short']}件")
        if type_changes['LiveArchive'] > 0:
            print(f"  → LiveArchive: {type_changes['LiveArchive']}件")

def check_milestones(current_videos, history):
    """キリ番達成をチェック（再生数・高評価数）"""
    achievements = []
    
    if not history or 'videos' not in history:
        return achievements
    
    old_data = history['videos']
    
    # キリ番リストを生成
    view_milestones = generate_view_milestones()
    like_milestones = generate_like_milestones()
    
    for video in current_videos:
        video_id = video['動画ID']
        current_views = video['再生数']
        current_likes = video['高評価数']
        
        if video_id in old_data:
            old_views = old_data[video_id].get('再生数', 0)
            old_likes = old_data[video_id].get('高評価数', 0)
            
            # 再生数のキリ番チェック
            for milestone in view_milestones:
                if old_views < milestone <= current_views:
                    achievements.append({
                        'タイプ': '再生数',
                        'タイトル': video['タイトル'],
                        'キリ番': milestone,
                        '現在の値': current_views,
                        '動画ID': video_id,
                        'type': video['type']
                    })
            
            # 高評価数のキリ番チェック
            for milestone in like_milestones:
                if old_likes < milestone <= current_likes:
                    achievements.append({
                        'タイプ': '高評価数',
                        'タイトル': video['タイトル'],
                        'キリ番': milestone,
                        '現在の値': current_likes,
                        '動画ID': video_id,
                        'type': video['type']
                    })
    
    return achievements

def process_channel(youtube, channel_config, overrides):
    """1つのチャンネルを処理（例外設定対応）"""
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
    
    # 全動画情報を取得（例外設定を渡す）
    print("\n全動画情報を取得中...")
    videos = get_all_videos(youtube, channel_id, channel_name, overrides)
    
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
            metric_type = achievement['タイプ']
            unit = "回" if metric_type == "再生数" else "件"
            print(f"  - {achievement['タイトル']}: {metric_type} {achievement['キリ番']:,}{unit}突破 [{achievement['type']}]")
        
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
    
    # 例外設定を読み込み
    print("\n例外設定を読み込み中...")
    overrides = load_video_type_overrides()
    
    # YouTube API クライアントを作成
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    # 各チャンネルを処理
    success_count = 0
    for channel_config in CHANNELS:
        if process_channel(youtube, channel_config, overrides):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"✓ 全処理完了: {success_count}/{len(CHANNELS)} チャンネル成功")
    print("=" * 50)

if __name__ == '__main__':
    main()
