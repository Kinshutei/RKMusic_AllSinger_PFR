#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube チャンネル統計ダッシュボード (Streamlit Cloud版)
Playboard風ダークモードデザイン
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

# Playboard風ダークモードCSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');

/* ベース設定 */
html, body, [class*="css"]  {
    font-family: 'Noto Sans JP', sans-serif !important;
}

/* メイン背景 */
.stApp {
    background: linear-gradient(135deg, #0E1117 0%, #1a1d29 100%);
}

/* サイドバー */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
}

section[data-testid="stSidebar"] > div {
    background: transparent;
}

/* カード型コンテナ */
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
    background: rgba(38, 39, 48, 0.6);
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.05);
}

/* メトリクスカード */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1e2330 0%, #262730 100%);
    padding: 16px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.08);
}

div[data-testid="stMetricLabel"] {
    color: #a0a0b0 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}

div[data-testid="stMetricValue"] {
    color: #ffffff !important;
    font-size: 28px !important;
    font-weight: 700 !important;
}

/* タブ */
button[data-baseweb="tab"] {
    background: transparent !important;
    color: #a0a0b0 !important;
    border-bottom: 2px solid transparent !important;
    font-weight: 500 !important;
    padding: 12px 24px !important;
}

button[data-baseweb="tab"]:hover {
    color: #ffffff !important;
    border-bottom: 2px solid #4a9eff !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #4a9eff !important;
    border-bottom: 2px solid #4a9eff !important;
    font-weight: 700 !important;
}

/* タレント選択ボタン */
.stButton > button {
    width: 100%;
    background: #1e2330 !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 8px !important;
    padding: 12px 20px !important;
    font-size: 16px !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
    margin: 4px 0 !important;
}

.stButton > button:hover {
    background: #262730 !important;
    border: 1px solid #4a9eff !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(74, 158, 255, 0.2) !important;
}

/* サブヘッダー */
h2, h3 {
    color: #ffffff !important;
    font-weight: 700 !important;
    margin-bottom: 16px !important;
}

/* テキスト */
p, span, div {
    color: #d0d0d8 !important;
}

/* リンク */
a {
    color: #4a9eff !important;
    text-decoration: none !important;
    transition: all 0.2s ease !important;
    font-weight: 500 !important;
}

a:hover {
    color: #6eb5ff !important;
    text-decoration: underline !important;
}

/* プログレスバー等 */
div[data-testid="stCaption"] {
    color: #8a8a9a !important;
    font-size: 12px !important;
}

/* スクロールバー */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #1a1d29;
}

::-webkit-scrollbar-thumb {
    background: #4a4a5a;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #5a5a6a;
}

/* グラフ背景 */
.js-plotly-plot {
    background: rgba(38, 39, 48, 0.3) !important;
    border-radius: 8px;
}

/* 統計情報ボックス */
.stat-box {
    background: linear-gradient(135deg, #1e2330 0%, #262730 100%);
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* 動画リストのカラム */
.video-row {
    background: rgba(30, 35, 48, 0.5);
    border-radius: 8px;
    padding: 12px;
    margin: 6px 0;
    border-left: 3px solid #4a9eff;
    transition: all 0.2s ease;
}

.video-row:hover {
    background: rgba(38, 39, 48, 0.8);
    transform: translateX(4px);
    box-shadow: 0 2px 8px rgba(74, 158, 255, 0.2);
}
</style>
""", unsafe_allow_html=True)

# キリ番のリスト
MILESTONES = [5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 10000000]

# タレント一覧を取得
def get_available_talents():
    """利用可能なタレント（チャンネル）のリストを取得"""
    talents = []
    history_files = glob.glob('video_history_*.json')
    for file in history_files:
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

# セッション状態の初期化
if 'selected_talent' not in st.session_state:
    st.session_state.selected_talent = None

# メインUI
st.title("🎵 RK Music 統計ダッシュボード")
st.markdown("*自動取得データを表示中（JST 0, 6, 12, 18, 21時更新）*")
st.markdown("---")

# サイドバー
with st.sidebar:
    st.header("🎵 RK Music")
    st.markdown("---")
    st.subheader("タレント")
    
    available_talents = get_available_talents()
    
    if not available_talents:
        st.warning("⚠️ データが見つかりません")
        st.info("初回の自動実行を待っています...")
        selected_talent = None
    else:
        if st.session_state.selected_talent is None:
            st.session_state.selected_talent = available_talents[0]
        
        for talent in available_talents:
            if st.button(talent, key=f"talent_{talent}"):
                st.session_state.selected_talent = talent
                st.rerun()
        
        selected_talent = st.session_state.selected_talent
        
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
    st.caption("🔄 自動更新: JST 0, 6, 12, 18, 21時")

if not selected_talent:
    st.info("📡 データを取得中です。初回の自動実行（GitHub Actions）を待っています。")
    st.stop()

history = load_history(selected_talent)
logs = load_logs(selected_talent)
video_history = load_video_daily_history(selected_talent)

if not history:
    st.error(f"❌ {selected_talent} のデータが見つかりません")
    st.stop()

channel_stats = history.get('channel_stats', {})

# タブ表示
tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "📹 Movie", "🎬 Short", "🔴 Archive"])

with tab1:
    st.header(f"📺 {channel_stats.get('チャンネル名', selected_talent)}")
    
    col1, col2 = st.columns(2)
    
    with col1:
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
        st.subheader("🏆 再生数TOP5")
        if video_history:
            video_list = []
            for video_id, video_data in video_history.items():
                records = video_data.get('records', [])
                if records:
                    video_type = video_data.get('type', 'Movie')
                    emoji = "📹" if video_type == 'Movie' else ("🎬" if video_type == 'Short' else "🔴")
                    video_list.append({
                        'タイトル': video_data['タイトル'],
                        '再生数': records[-1]['再生数'],
                        'emoji': emoji
                    })
            video_list.sort(key=lambda x: x['再生数'], reverse=True)
            for i, video in enumerate(video_list[:5], 1):
                st.markdown(f"{i}. {video['emoji']} {video['タイトル'][:40]}... - **{video['再生数']:,}回**")
        else:
            st.info("データを蓄積中...")
    
    col3, col4, col5 = st.columns(3)
    
    for col, video_type, title, emoji in [
        (col3, 'Movie', '急上昇 Movie', '📈'),
        (col4, 'Short', '急上昇 Short', '🎬'),
        (col5, 'LiveArchive', '急上昇 Archive', '🔴')
    ]:
        with col:
            st.subheader(f"{emoji} {title}")
            if video_history:
                growth_list = []
                for video_id, video_data in video_history.items():
                    if video_data.get('type') == video_type:
                        records = video_data.get('records', [])
                        if len(records) >= 2:
                            growth = calculate_growth(records, '1WEEK')
                            if growth > 0:
                                start_views = records[0]['再生数']
                                growth_rate = (growth / start_views * 100) if start_views > 0 else 0
                                growth_list.append({
                                    'タイトル': video_data['タイトル'],
                                    '増加数': growth,
                                    '伸び率': growth_rate
                                })
                growth_list.sort(key=lambda x: x['増加数'], reverse=True)
                for i, video in enumerate(growth_list[:5], 1):
                    st.markdown(f"{i}. {video['タイトル'][:30]}... - **+{video['増加数']:,}回** ({video['伸び率']:.1f}%)")
            else:
                st.info("データを蓄積中...")

def render_video_tab(video_history, video_type, type_name, emoji):
    """動画タブの共通レンダリング"""
    st.header(f"{emoji} {type_name}")
    
    if not video_history:
        st.info("📡 動画別履歴データを蓄積中です。")
        return
    
    filtered_history = filter_videos_by_type(video_history, video_type)
    
    if not filtered_history:
        st.warning(f"{type_name}データがありません")
        return
    
    period = st.selectbox("期間", ['1DAY', '1WEEK', '1MONTH'], index=1, key=f'period_{video_type}')
    st.markdown("---")
    
    st.subheader("📈 再生数推移")
    
    plot_data = []
    video_list = []
    
    for video_id, video_data in filtered_history.items():
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
        video_data = filtered_history[video_id]
        records = video_data.get('records', [])
        for record in records:
            plot_data.append({
                '日時': record['timestamp'],
                '動画': video_data['タイトル'][:30] + '...',
                '再生数': record['再生数']
            })
    
    if plot_data:
        df_plot = pd.DataFrame(plot_data)
        fig = px.line(df_plot, x='日時', y='再生数', color='動画', title=f'再生数推移 TOP5', markers=True)
        fig.update_layout(
            height=500,
            font_family='Noto Sans JP',
            plot_bgcolor='rgba(30, 35, 48, 0.3)',
            paper_bgcolor='rgba(38, 39, 48, 0.3)',
            font_color='#d0d0d8'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader(f"📋 {type_name}リスト")
    st.markdown("クリックして動画を視聴できます")
    
    table_data = []
    for video_id, video_data in filtered_history.items():
        records = video_data.get('records', [])
        if records:
            current_views = records[-1]['再生数']
            growth = calculate_growth(records, period)
            table_data.append({
                'タイトル': video_data['タイトル'],
                '再生数': current_views,
                '増加数': growth,
                '動画ID': video_id
            })
    
    table_df = pd.DataFrame(table_data)
    table_df = table_df.sort_values('再生数', ascending=False)
    
    for idx, row in table_df.iterrows():
        video_url = f"https://www.youtube.com/watch?v={row['動画ID']}"
        growth_text = f"+{row['増加数']:,}" if row['増加数'] > 0 else "0"
        
        st.markdown(f'<div class="video-row">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"[{row['タイトル']}]({video_url})")
        with col2:
            st.text(f"{row['再生数']:,}回")
        with col3:
            st.text(growth_text)
        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    render_video_tab(video_history, 'Movie', '動画（Movie）', '📹')

with tab3:
    render_video_tab(video_history, 'Short', 'Short動画', '🎬')

with tab4:
    render_video_tab(video_history, 'LiveArchive', 'アーカイブ（LiveArchive）', '🔴')

st.markdown("---")
st.caption("Powered by GitHub Actions + Streamlit Cloud | 自動更新: JST 0, 6, 12, 18, 21時")
