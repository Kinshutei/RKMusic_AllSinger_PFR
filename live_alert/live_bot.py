#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord Bot: /check コマンドで4名のライブ・見逃し配信を確認する
"""

import json
import os
import discord
from discord import app_commands
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build

# ----------------------------------------------------------------
# 設定読み込み
# ----------------------------------------------------------------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

with open(CONFIG_PATH, encoding='utf-8') as f:
    config = json.load(f)

YOUTUBE_API_KEY = config['youtube_api_key']
DISCORD_TOKEN = config['discord_token']

# ----------------------------------------------------------------
# 監視対象シンガー
# ----------------------------------------------------------------
SINGERS = [
    {'name': '深影', 'channel_id': 'UC2daHxnuJJBM5NWci1RRkeA'},
    {'name': '妃玖',  'channel_id': 'UCFBc8kuCtTwmtdsBcJoZ3qA'},
    {'name': 'Diα',  'channel_id': 'UC80TduEq6Sp4n2DkiUH2eLQ'},
    {'name': 'wouca', 'channel_id': 'UC8TVZmQuOl0GNbpvThwwSdQ'},
]

JST = timezone(timedelta(hours=9))

# ----------------------------------------------------------------
# YouTube API
# ----------------------------------------------------------------
def get_youtube():
    return build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def jst_today_midnight_utc() -> str:
    """今日のJST 0:00 をUTC ISO形式で返す"""
    now_jst = datetime.now(JST)
    midnight_jst = now_jst.replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight_jst.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def check_channel(youtube, channel_id: str) -> dict:
    """
    1チャンネルについて現在ライブ中と今日のアーカイブを取得する。
    Returns:
        {
            'live': [{'title': ..., 'video_id': ...}],
            'archives': [{'title': ..., 'video_id': ..., 'started_at': ...}],
        }
    """
    result = {'live': [], 'archives': []}

    # 現在ライブ中
    live_res = youtube.search().list(
        channelId=channel_id,
        eventType='live',
        type='video',
        part='id,snippet',
        maxResults=3,
    ).execute()
    for item in live_res.get('items', []):
        result['live'].append({
            'title': item['snippet']['title'],
            'video_id': item['id']['videoId'],
        })

    # 今日のアーカイブ（配信終了分）
    archive_res = youtube.search().list(
        channelId=channel_id,
        eventType='completed',
        type='video',
        part='id,snippet',
        publishedAfter=jst_today_midnight_utc(),
        maxResults=5,
        order='date',
    ).execute()
    for item in archive_res.get('items', []):
        started_at = item['snippet'].get('publishedAt', '')
        if started_at:
            dt = datetime.fromisoformat(started_at.replace('Z', '+00:00')).astimezone(JST)
            started_str = dt.strftime('%H:%M')
        else:
            started_str = '--:--'
        result['archives'].append({
            'title': item['snippet']['title'],
            'video_id': item['id']['videoId'],
            'started_at': started_str,
        })

    return result

# ----------------------------------------------------------------
# Discord Bot
# ----------------------------------------------------------------
class LiveCheckerBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print('スラッシュコマンド同期完了')

    async def on_ready(self):
        print(f'Bot起動: {self.user}')

client = LiveCheckerBot()

@client.tree.command(name='check', description='4名のライブ・見逃し配信を確認する')
async def check(interaction: discord.Interaction):
    await interaction.response.defer()

    youtube = get_youtube()
    today_str = datetime.now(JST).strftime('%Y/%m/%d')
    lines = [f'📅 **{today_str} 配信チェック**\n']

    for singer in SINGERS:
        data = check_channel(youtube, singer['channel_id'])
        name = singer['name']

        if data['live']:
            for v in data['live']:
                url = f"https://www.youtube.com/watch?v={v['video_id']}"
                lines.append(f"🔴 **{name}さん ライブ中！**")
                lines.append(f"　{v['title']}")
                lines.append(f"　{url}")
        elif data['archives']:
            lines.append(f"📼 **{name}さん** 今日の配信:")
            for v in data['archives']:
                url = f"https://www.youtube.com/watch?v={v['video_id']}"
                lines.append(f"　{v['started_at']}〜 {v['title']}")
                lines.append(f"　{url}")
        else:
            lines.append(f"✅ **{name}さん**: 今日は配信なし")

        lines.append('')

    await interaction.followup.send('\n'.join(lines))

# ----------------------------------------------------------------
# 起動
# ----------------------------------------------------------------
client.run(DISCORD_TOKEN)
