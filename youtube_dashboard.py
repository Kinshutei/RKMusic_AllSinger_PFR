#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube チャンネル統計ダッシュボード (Streamlit Cloud版)
ライトモード/ダークモード切り替え対応
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

# セッション状態の初期化
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'  # デフォルトはライトモード
if 'selected_talent' not in st.session_state:
    st.session_state.selected_talent = None

# テーマに応じたCSS
def get_theme_css(theme):
    """テーマに応じたCSSを返す"""
    
    base_css = """
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Noto Sans JP', sans-serif !important;
    }
    
    /* 全体的なスペーシングを圧縮 */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* タブ */
    button[data-baseweb="tab"] {
        background: transparent !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
    }
    
    button[data-baseweb="tab"]:hover {
        font-weight: 600 !important;
    }
    
    button[data-baseweb="tab"][aria-selected="true"] {
        font-weight: 700 !important;
    }
    
    /* ボタン */
    .stButton > button {
        width: 100%;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        margin: 2px 0 !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
    }
    
    /* サブヘッダー */
    h1 {
        margin-bottom: 0.5rem !important;
        padding-bottom: 0 !important;
    }
    
    h2, h3 {
        font-weight: 700 !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* 段落とテキスト */
    p {
        margin-bottom: 0.5rem !important;
    }
    
    /* リンク */
    a {
        text-decoration: none !important;
        transition: all 0.2s ease !important;
        font-weight: 500 !important;
    }
    
    a:hover {
        text-decoration: underline !important;
    }
    
    /* キャプション */
    div[data-testid="stCaption"] {
        font-size: 12px !important;
        margin-top: 0.2rem !important;
        margin-bottom: 0.2rem !important;
    }
    
    /* 区切り線 */
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* スクロールバー */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-thumb {
        border-radius: 4px;
    }
    
    /* メトリクス */
    div[data-testid="stMetric"] {
        padding: 10px !important;
        border-radius: 10px;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        font-weight: 500 !important;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: 700 !important;
    }
    
    /* セレクトボックス */
    div[data-baseweb="select"] {
        margin-bottom: 0.5rem !important;
    }
    
    /* コンテンツブロックの罫線とスペーシング */
    .content-block {
        border: 1px solid;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    /* カラム間の間隔を詰める */
    div[data-testid="column"] {
        padding: 0 4px !important;
    }
    
    div[data-testid="column"]:first-child {
        padding-left: 0 !important;
    }
    
    div[data-testid="column"]:last-child {
        padding-right: 0 !important;
    }
    
    /* サブヘッダーのマージンを調整 */
    .content-block h3 {
        margin-top: 0 !important;
        margin-bottom: 12px !important;
    }
    """
    
    if theme == 'dark':
        theme_css = """
        /* ダークモード */
        .stApp {
            background: linear-gradient(135deg, #0E1117 0%, #1a1d29 100%);
        }
        
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        }
        
        section[data-testid="stSidebar"] > div {
            background: transparent;
        }
        
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
            background: rgba(38, 39, 48, 0.6);
            border-radius: 12px;
            padding: 12px !important;
            margin: 5px 0 !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #1e2330 0%, #262730 100%);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        
        div[data-testid="stMetricLabel"] {
            color: #a0a0b0 !important;
        }
        
        div[data-testid="stMetricValue"] {
            color: #ffffff !important;
        }
        
        button[data-baseweb="tab"] {
            color: #a0a0b0 !important;
            border-bottom: 2px solid transparent !important;
        }
        
        button[data-baseweb="tab"]:hover {
            color: #ffffff !important;
            border-bottom: 2px solid #4a9eff !important;
        }
        
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #4a9eff !important;
            border-bottom: 2px solid #4a9eff !important;
        }
        
        .stButton > button {
            background: #1e2330 !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
        }
        
        .stButton > button:hover {
            background: #262730 !important;
            border: 1px solid #4a9eff !important;
            box-shadow: 0 4px 8px rgba(74, 158, 255, 0.2) !important;
        }
        
        h2, h3 {
            color: #ffffff !important;
        }
        
        p, span, div {
            color: #d0d0d8 !important;
        }
        
        a {
            color: #4a9eff !important;
        }
        
        a:hover {
            color: #6eb5ff !important;
        }
        
        div[data-testid="stCaption"] {
            color: #8a8a9a !important;
        }
        
        ::-webkit-scrollbar-track {
            background: #1a1d29;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #4a4a5a;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #5a5a6a;
        }
        
        .content-block {
            border-color: rgba(255, 255, 255, 0.1);
            background: rgba(38, 39, 48, 0.4);
        }
        """
    
    else:  # light mode
        theme_css = """
        /* ライトモード */
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
        }
        
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
        }
        
        section[data-testid="stSidebar"] > div {
            background: transparent;
        }
        
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 12px;
            padding: 12px !important;
            margin: 5px 0 !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(0, 0, 0, 0.05);
        }
        
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
            border: 1px solid rgba(0, 0, 0, 0.06);
        }
        
        div[data-testid="stMetricLabel"] {
            color: #6c757d !important;
        }
        
        div[data-testid="stMetricValue"] {
            color: #212529 !important;
        }
        
        button[data-baseweb="tab"] {
            color: #6c757d !important;
            border-bottom: 2px solid transparent !important;
        }
        
        button[data-baseweb="tab"]:hover {
            color: #212529 !important;
            border-bottom: 2px solid #0d6efd !important;
        }
        
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #0d6efd !important;
            border-bottom: 2px solid #0d6efd !important;
        }
        
        .stButton > button {
            background: #ffffff !important;
            color: #212529 !important;
            border: 1px solid #dee2e6 !important;
        }
        
        .stButton > button:hover {
            background: #f8f9fa !important;
            border: 1px solid #0d6efd !important;
            box-shadow: 0 4px 8px rgba(13, 110, 253, 0.15) !important;
        }
        
        h2, h3 {
            color: #212529 !important;
        }
        
        p, span, div {
            color: #495057 !important;
        }
        
        a {
            color: #0d6efd !important;
        }
        
        a:hover {
            color: #0a58ca !important;
        }
        
        div[data-testid="stCaption"] {
            color: #6c757d !important;
        }
        
        ::-webkit-scrollbar-track {
            background: #f8f9fa;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #dee2e6;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #adb5bd;
        }
        
        .content-block {
            border-color: rgba(0, 0, 0, 0.1);
            background: rgba(255, 255, 255, 0.8);
        }
        """
    
    # 最後に一つの<style>タグで囲んで返す
    return f"<style>{base_css}{theme_css}</style>"

# CSSを適用
st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)

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

def aggregate_records_by_date(records):
    """同じ日付のレコードは最新のみを使用"""
    date_records = {}
    
    for record in records:
        try:
            timestamp = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S')
            date_key = timestamp.strftime('%Y-%m-%d')  # 日付のみ
            
            # 既存データがないか、より新しいタイムスタンプなら更新
            if date_key not in date_records:
                date_records[date_key] = record
            else:
                existing_time = datetime.strptime(date_records[date_key]['timestamp'], '%Y-%m-%d %H:%M:%S')
                if timestamp > existing_time:
                    date_records[date_key] = record  # より新しい方を採用
        except:
            continue
    
    # タイムスタンプでソートして返す
    return sorted(date_records.values(), key=lambda x: x['timestamp'])

# メインUI
st.title("🎵 RK Music 統計ダッシュボード")
st.markdown("*自動取得データを表示中（JST 0, 6, 12, 18, 21時更新）*")

# サイドバー
with st.sidebar:
    # テーマ切り替えボタン
    if st.session_state.theme == 'light':
        if st.button("🌙 ダークモードに切り替え", use_container_width=True):
            st.session_state.theme = 'dark'
            st.rerun()
    else:
        if st.button("☀️ ライトモードに切り替え", use_container_width=True):
            st.session_state.theme = 'light'
            st.rerun()
    
    st.markdown("---")
    st.header("🎵 RK Music")
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

# グラフのテーマ設定
def get_plot_theme():
    """グラフのテーマを返す"""
    if st.session_state.theme == 'dark':
        return {
            'plot_bgcolor': 'rgba(30, 35, 48, 0.3)',
            'paper_bgcolor': 'rgba(38, 39, 48, 0.3)',
            'font_color': '#d0d0d8'
        }
    else:
        return {
            'plot_bgcolor': 'rgba(255, 255, 255, 0.8)',
            'paper_bgcolor': 'rgba(255, 255, 255, 0.8)',
            'font_color': '#495057'
        }

# タブ表示
tab1, tab2, tab3, tab4 = st.tabs(["🏠 General", "📹 Movie", "🎬 Short", "🔴 Archive"])

with tab1:
    st.header(f"📺 {channel_stats.get('チャンネル名', selected_talent)}")
    
    # 1行目: チャンネル概要（全幅）
    st.markdown('<div class="content-block">', unsafe_allow_html=True)
    st.subheader("📊 チャンネル概要")
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric("登録者数", f"{channel_stats['登録者数']:,}人")
    with metric_col2:
        st.metric("総再生数", f"{channel_stats['総再生数']:,}回")
    with metric_col3:
        st.metric("動画数", f"{channel_stats['動画数']:,}本")
    st.caption(f"最終更新: {history.get('timestamp', 'N/A')}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 2行目: 再生数TOP5（全幅）
    st.markdown('<div class="content-block">', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 3行目: 急上昇セクション（3カラム）
    col3, col4, col5 = st.columns(3)
    
    for col, video_type, title, emoji in [
        (col3, 'Movie', '急上昇 Movie', '📈'),
        (col4, 'Short', '急上昇 Short', '🎬'),
        (col5, 'LiveArchive', '急上昇 Archive', '🔴')
    ]:
        with col:
            st.markdown('<div class="content-block">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

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
    
    st.subheader("📈 再生数推移")
    
    # 期間のカットオフ時刻を計算
    now = datetime.now()
    if period == '1DAY':
        cutoff = now - timedelta(days=1)
    elif period == '1WEEK':
        cutoff = now - timedelta(days=7)
    elif period == '1MONTH':
        cutoff = now - timedelta(days=30)
    else:
        cutoff = now - timedelta(days=7)  # デフォルト
    
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
        
        # 日付で集約（同じ日は最新のみ）
        records = aggregate_records_by_date(records)
        
        # 期間でフィルタリング
        for record in records:
            try:
                record_date = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S')
                if record_date >= cutoff:
                    plot_data.append({
                        '日時': record['timestamp'][:10],  # 日付のみ表示
                        '動画': video_data['タイトル'][:30] + '...',
                        '再生数': record['再生数']
                    })
            except:
                continue
    
    if plot_data:
        df_plot = pd.DataFrame(plot_data)
        fig = px.line(df_plot, x='日時', y='再生数', color='動画', title=f'再生数推移 TOP5', markers=True)
        theme = get_plot_theme()
        fig.update_layout(
            height=400,
            font_family='Noto Sans JP',
            plot_bgcolor=theme['plot_bgcolor'],
            paper_bgcolor=theme['paper_bgcolor'],
            font_color=theme['font_color'],
            margin=dict(l=40, r=40, t=40, b=40)
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
        
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"[{row['タイトル']}]({video_url})")
        with col2:
            st.text(f"{row['再生数']:,}回")
        with col3:
            st.text(growth_text)

with tab2:
    render_video_tab(video_history, 'Movie', '動画（Movie）', '📹')

with tab3:
    render_video_tab(video_history, 'Short', 'Short動画', '🎬')

with tab4:
    render_video_tab(video_history, 'LiveArchive', 'アーカイブ（LiveArchive）', '🔴')

st.caption("Powered by GitHub Actions + Streamlit Cloud | 自動更新: JST 0, 6, 12, 18, 21時")
