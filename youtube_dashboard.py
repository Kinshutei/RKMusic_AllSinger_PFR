#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube チャンネル統計ダッシュボード (Streamlit Cloud版)
複数チャンネル対応 + Movie/Archive分類
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import glob

# ページ設定
st.set_page_config(
    page_title="RK Music 統計ダッシュボード",
    page_icon="🎵",
    layout="wide"
)

# キリ番のリスト
MILESTONES = [5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 10000000]

# タレント一覧を取得
def get_available_talents():
    """利用可能なタレント（チャンネル）のリストを取得"""
    talents = []
    
    # video_history_{name}.jsonファイルからタレント名を取得
    history_files = glob.glob('video_history_*.json')
    
    for file in history_files:
        # ファイル名からタレント名を抽出
        name = file.replace('video_history_', '').replace('.json', '')
        talents.append(name)
    
    return sorted(talents)

def load_history(talent_name):
    """履歴データを読み込む"""
    history_file = f'video_history_{talent_name}.json'
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None

def load_logs(talent_name):
    """ログデータを読み込む"""
    log_file = f'check_log_{talent_name}.json'
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def load_video_daily_history(talent_name):
    """動画別履歴データを読み込む"""
    history_file = f'video_daily_history_{talent_name}.json'
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def filter_videos_by_type(video_history, video_type):
    """動画を種類でフィルタリング"""
    if video_type == 'ALL':
        return video_history
    
    filtered = {}
    for video_id, video_data in video_history.items():
        if video_data.get('type') == video_type:
            filtered[video_id] = video_data
    
    return filtered

def calculate_growth(records, period='1DAY'):
    """指定期間の増加数を計算"""
    if len(records) < 2:
        return 0
    
    now = datetime.now()
    
    if period == '1DAY':
        cutoff = now - timedelta(days=1)
    elif period == '1WEEK':
        cutoff = now - timedelta(days=7)
    elif period == '1MONTH':
        cutoff = now - timedelta(days=30)
    else:
        return 0
    
    # 期間内の最古のレコードを探す
    old_record = None
    for record in records:
        try:
            record_date = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S')
            if record_date >= cutoff:
                if old_record is None or record_date < datetime.strptime(old_record['timestamp'], '%Y-%m-%d %H:%M:%S'):
                    old_record = record
        except:
            continue
    
    if old_record:
        return records[-1]['再生数'] - old_record['再生数']
    
    return 0

# メインUI
st.title("🎵 RK Music 統計ダッシュボード")
st.markdown("*自動取得データを表示中（3時間ごとに更新）*")
st.markdown("---")

# サイドバー
with st.sidebar:
    st.header("🎵 RK Music")
    st.markdown("---")
    
    # タレント一覧
    st.subheader("タレント")
    
    available_talents = get_available_talents()
    
    if not available_talents:
        st.warning("⚠️ データが見つかりません")
        st.info("初回の自動実行を待っています...")
        selected_talent = None
    else:
        selected_talent = st.radio(
            "",
            available_talents,
            index=0
        )
        
        # 選択されたタレントの情報を表示
        if selected_talent:
            history = load_history(selected_talent)
            if history and 'channel_stats' in history:
                stats = history['channel_stats']
                st.markdown("---")
                st.metric("登録者数", f"{stats['登録者数']:,}人")
                st.metric("総再生数", f"{stats['総再生数']:,}回")
                st.metric("動画数", f"{stats['動画数']:,}本")
                st.caption(f"最終更新: {history.get('timestamp', 'N/A')}")
    
    st.markdown("---")
    st.caption("🔄 自動更新: 3時間ごと")

# タレントが選択されていない場合
if not selected_talent:
    st.info("📡 データを取得中です。初回の自動実行（GitHub Actions）を待っています。")
    st.stop()

# データ読み込み
history = load_history(selected_talent)
logs = load_logs(selected_talent)
video_history = load_video_daily_history(selected_talent)

if not history:
    st.error(f"❌ {selected_talent} のデータが見つかりません")
    st.stop()

# チャンネル情報
channel_stats = history.get('channel_stats', {})

# タブ表示
tab1, tab2, tab3 = st.tabs(["🏠 General", "📹 動画", "🔴 Archive"])

with tab1:
    st.header(f"📺 {channel_stats.get('チャンネル名', selected_talent)}")
    
    # 田の字レイアウト
    col1, col2 = st.columns(2)
    
    with col1:
        # 左上：チャンネル概要
        st.subheader("📊 チャンネル概要")
        
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            st.metric("登録者数", f"{channel_stats['登録者数']:,}人")
        with metric_col2:
            st.metric("総再生数", f"{channel_stats['総再生数']:,}回")
        with metric_col3:
            st.metric("動画数", f"{channel_stats['動画数']:,}本")
        
        st.caption(f"最終更新: {history.get('timestamp', 'N/A')}")
    
    with col2:
        # 右上：再生数TOP5
        st.subheader("🏆 再生数TOP5")
        
        if video_history:
            # 全動画から再生数TOP5を取得
            video_list = []
            for video_id, video_data in video_history.items():
                records = video_data.get('records', [])
                if records:
                    video_list.append({
                        'タイトル': video_data['タイトル'],
                        '再生数': records[-1]['再生数'],
                        'type': video_data.get('type', 'Movie')
                    })
            
            video_list.sort(key=lambda x: x['再生数'], reverse=True)
            top5 = video_list[:5]
            
            for i, video in enumerate(top5, 1):
                type_emoji = "📹" if video['type'] == 'Movie' else "🔴"
                st.markdown(f"{i}. {type_emoji} {video['タイトル'][:40]}... - **{video['再生数']:,}回**")
        else:
            st.info("データを蓄積中...")
    
    # 下段
    col3, col4 = st.columns(2)
    
    with col3:
        # 左下：急上昇Movie
        st.subheader("📈 急上昇 Movie")
        
        if video_history:
            movie_growth = []
            for video_id, video_data in video_history.items():
                if video_data.get('type') == 'Movie':
                    records = video_data.get('records', [])
                    if len(records) >= 2:
                        growth = calculate_growth(records, '1WEEK')
                        if growth > 0:
                            start_views = records[0]['再生数']
                            end_views = records[-1]['再生数']
                            growth_rate = (growth / start_views * 100) if start_views > 0 else 0
                            
                            movie_growth.append({
                                'タイトル': video_data['タイトル'],
                                '増加数': growth,
                                '伸び率': growth_rate
                            })
            
            movie_growth.sort(key=lambda x: x['増加数'], reverse=True)
            
            for i, video in enumerate(movie_growth[:5], 1):
                st.markdown(f"{i}. {video['タイトル'][:40]}... - **+{video['増加数']:,}回** ({video['伸び率']:.1f}%)")
        else:
            st.info("データを蓄積中...")
    
    with col4:
        # 右下：急上昇Archive
        st.subheader("🔴 急上昇 Archive")
        
        if video_history:
            archive_growth = []
            for video_id, video_data in video_history.items():
                if video_data.get('type') == 'LiveArchive':
                    records = video_data.get('records', [])
                    if len(records) >= 2:
                        growth = calculate_growth(records, '1WEEK')
                        if growth > 0:
                            start_views = records[0]['再生数']
                            end_views = records[-1]['再生数']
                            growth_rate = (growth / start_views * 100) if start_views > 0 else 0
                            
                            archive_growth.append({
                                'タイトル': video['タイトル'],
                                '増加数': growth,
                                '伸び率': growth_rate
                            })
            
            archive_growth.sort(key=lambda x: x['増加数'], reverse=True)
            
            for i, video in enumerate(archive_growth[:5], 1):
                st.markdown(f"{i}. {video['タイトル'][:40]}... - **+{video['増加数']:,}回** ({video['伸び率']:.1f}%)")
        else:
            st.info("データを蓄積中...")

with tab2:
    st.header("📹 動画（Movie）")
    
    if not video_history:
        st.info("📡 動画別履歴データを蓄積中です。")
        st.stop()
    
    # Movieのみフィルター
    movie_history = filter_videos_by_type(video_history, 'Movie')
    
    if not movie_history:
        st.warning("Movieデータがありません")
        st.stop()
    
    # 期間選択
    period_col1, period_col2 = st.columns([1, 3])
    
    with period_col1:
        period = st.selectbox(
            "期間",
            ['1DAY', '1WEEK', '1MONTH'],
            index=1
        )
    
    st.markdown("---")
    
    # 上段：折れ線グラフ
    st.subheader("📈 再生数推移")
    
    # TOP5の動画の推移をグラフ化
    plot_data = []
    video_list = []
    
    for video_id, video_data in movie_history.items():
        records = video_data.get('records', [])
        if records:
            video_list.append({
                'id': video_id,
                'タイトル': video_data['タイトル'],
                '再生数': records[-1]['再生数']
            })
    
    video_list.sort(key=lambda x: x['再生数'], reverse=True)
    top5_ids = [v['id'] for v in video_list[:5]]
    
    for video_id in top5_ids:
        video_data = movie_history[video_id]
        records = video_data.get('records', [])
        
        for record in records:
            plot_data.append({
                '日時': record['timestamp'],
                '動画': video_data['タイトル'][:30] + '...',
                '再生数': record['再生数']
            })
    
    if plot_data:
        df_plot = pd.DataFrame(plot_data)
        fig = px.line(
            df_plot,
            x='日時',
            y='再生数',
            color='動画',
            title='再生数推移 TOP5',
            markers=True
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    # 中段：動画リスト（表形式）
    st.subheader("📋 動画リスト")
    
    table_data = []
    for video_id, video_data in movie_history.items():
        records = video_data.get('records', [])
        if records:
            current_views = records[-1]['再生数']
            growth = calculate_growth(records, period)
            
            table_data.append({
                'タイトル': video_data['タイトル'],
                '再生数': current_views,
                f'増加数({period})': f"+{growth:,}" if growth > 0 else "0"
            })
    
    # 再生数でソート
    table_df = pd.DataFrame(table_data)
    table_df = table_df.sort_values('再生数', ascending=False)
    
    st.dataframe(table_df, use_container_width=True, height=500)

with tab3:
    st.header("🔴 アーカイブ（LiveArchive）")
    
    if not video_history:
        st.info("📡 動画別履歴データを蓄積中です。")
        st.stop()
    
    # LiveArchiveのみフィルター
    archive_history = filter_videos_by_type(video_history, 'LiveArchive')
    
    if not archive_history:
        st.warning("LiveArchiveデータがありません")
        st.stop()
    
    # 期間選択
    period_col1, period_col2 = st.columns([1, 3])
    
    with period_col1:
        period_archive = st.selectbox(
            "期間 ",
            ['1DAY', '1WEEK', '1MONTH'],
            index=1,
            key='archive_period'
        )
    
    st.markdown("---")
    
    # 上段：折れ線グラフ
    st.subheader("📈 再生数推移")
    
    # TOP5のアーカイブの推移をグラフ化
    plot_data_archive = []
    archive_list = []
    
    for video_id, video_data in archive_history.items():
        records = video_data.get('records', [])
        if records:
            archive_list.append({
                'id': video_id,
                'タイトル': video_data['タイトル'],
                '再生数': records[-1]['再生数']
            })
    
    archive_list.sort(key=lambda x: x['再生数'], reverse=True)
    top5_archive_ids = [v['id'] for v in archive_list[:5]]
    
    for video_id in top5_archive_ids:
        video_data = archive_history[video_id]
        records = video_data.get('records', [])
        
        for record in records:
            plot_data_archive.append({
                '日時': record['timestamp'],
                'アーカイブ': video_data['タイトル'][:30] + '...',
                '再生数': record['再生数']
            })
    
    if plot_data_archive:
        df_plot_archive = pd.DataFrame(plot_data_archive)
        fig_archive = px.line(
            df_plot_archive,
            x='日時',
            y='再生数',
            color='アーカイブ',
            title='再生数推移 TOP5',
            markers=True
        )
        fig_archive.update_layout(height=500)
        st.plotly_chart(fig_archive, use_container_width=True)
    
    # 中段：アーカイブリスト（表形式）
    st.subheader("📋 アーカイブリスト")
    
    table_data_archive = []
    for video_id, video_data in archive_history.items():
        records = video_data.get('records', [])
        if records:
            current_views = records[-1]['再生数']
            growth = calculate_growth(records, period_archive)
            
            table_data_archive.append({
                'タイトル': video_data['タイトル'],
                '再生数': current_views,
                f'増加数({period_archive})': f"+{growth:,}" if growth > 0 else "0"
            })
    
    # 再生数でソート
    table_df_archive = pd.DataFrame(table_data_archive)
    table_df_archive = table_df_archive.sort_values('再生数', ascending=False)
    
    st.dataframe(table_df_archive, use_container_width=True, height=500)

# フッター
st.markdown("---")
st.caption("Powered by GitHub Actions + Streamlit Cloud | 自動更新: 3時間ごと")
