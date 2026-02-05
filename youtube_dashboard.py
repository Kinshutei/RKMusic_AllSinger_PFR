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
    page_title="YouTube Stats Dashboard",
    page_icon="📊",
    layout="wide"
)

# セッション状態の初期化
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'  # デフォルトはライトモード
if 'selected_talent' not in st.session_state:
    st.session_state.selected_talent = None

# タレントのバナー画像URL
TALENT_BANNERS = {
    "LEWNE": "https://yt3.googleusercontent.com/TjOjwrUdPkWglNkEgvhXt8dS36kqyKB7XwjMWwnnwWg_VgrN0EMm_XXTTR_WtI18AceNz-uY=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "wouca": "https://yt3.googleusercontent.com/VIJQxQkEkRO2OqxIYlabQLRbpeyRiGdZxjLad7YzVjT3tbXkE24XKL_ZirI1RDUMHQBsY7hK=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "深影": "https://yt3.googleusercontent.com/6REyrT4s7DrjAvRL0yJUJJxi3Ahb59XtcnnDNpu7lC7sojUKthxvBIWJDVSyExFi1BOyJPzZWg=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj"
}

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
        padding: 4px 16px !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        margin: 3px 0 !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
    }
    
    /* サイドバー内のタレント選択ボタン */
    section[data-testid="stSidebar"] .stButton > button {
        padding: 4px 6px !important;
        font-size: 10px !important;
        border-radius: 4px !important;
        margin: 0 !important;
        background: transparent !important;
        border: 1px solid rgba(128, 128, 128, 0.3) !important;
        text-align: center !important;
        font-weight: 500 !important;
        box-shadow: none !important;
        height: 100% !important;
        writing-mode: vertical-rl !important;
        text-orientation: mixed !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        transform: none;
        font-weight: 600 !important;
        border-color: rgba(128, 128, 128, 0.6) !important;
    }
    
    /* サイドバーのボタンコンテナ */
    section[data-testid="stSidebar"] .stButton {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* ラジオボタンをテキストリンク風にカスタマイズ */
    div[role="radiogroup"] {
        gap: 0 !important;
    }
    
    div[role="radiogroup"] label {
        display: flex !important;
        align-items: center !important;
        padding: 8px 0 !important;
        margin: 0 !important;
        border-bottom: 1px solid rgba(128, 128, 128, 0.2) !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }
    
    div[role="radiogroup"] label:hover {
        padding-left: 4px !important;
    }
    
    /* ラジオボタンの丸を非表示 */
    div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] {
        margin-left: 0 !important;
    }
    
    div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    
    /* 選択されていないタレント */
    div[role="radiogroup"] label[data-baseweb="radio"] {
        font-weight: 400 !important;
    }
    
    /* テキスト部分 */
    div[role="radiogroup"] label p {
        margin: 0 !important;
        font-size: 15px !important;
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
    
    /* 動画カードのスタイル */
    .video-card {
        border: 1px solid;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        transition: all 0.2s ease;
    }
    
    .video-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    .video-title {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    
    .video-stats {
        display: flex;
        gap: 24px;
        flex-wrap: wrap;
    }
    
    .stat-item {
        display: flex;
        flex-direction: column;
    }
    
    .stat-label {
        font-size: 12px;
        font-weight: 500;
        margin-bottom: 4px;
        opacity: 0.7;
    }
    
    .stat-value {
        font-size: 18px;
        font-weight: 700;
    }
    
    .stat-change {
        font-size: 14px;
        margin-left: 8px;
    }
    
    .positive-change {
        color: #28a745;
    }
    
    .neutral-change {
        color: #6c757d;
    }
    
    /* 区切り線 */
    .divider {
        border-top: 1px solid;
        margin: 20px 0;
    }
    
    /* ページヘッダー */
    .page-header {
        margin-bottom: 8px;
    }
    
    .page-header h1 {
        margin-bottom: 0 !important;
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
        
        .video-card {
            border-color: rgba(255, 255, 255, 0.15);
            background: rgba(38, 39, 48, 0.5);
        }
        
        .video-card:hover {
            border-color: rgba(74, 158, 255, 0.4);
            box-shadow: 0 4px 12px rgba(74, 158, 255, 0.2);
        }
        
        .divider {
            border-color: rgba(255, 255, 255, 0.1);
        }
        
        /* タレント選択 - ラジオボタン */
        div[role="radiogroup"] label {
            color: #a0a0b0 !important;
        }
        
        div[role="radiogroup"] label:hover {
            color: #ffffff !important;
        }
        
        /* 選択されたタレント */
        div[role="radiogroup"] label[data-checked="true"] {
            color: #4a9eff !important;
            font-weight: 600 !important;
        }
        
        div[role="radiogroup"] label[data-checked="true"]:hover {
            color: #6eb5ff !important;
        }
        
        /* サイドバーのタレント選択ボタン */
        section[data-testid="stSidebar"] .stButton > button {
            color: #a0a0b0 !important;
        }
        
        section[data-testid="stSidebar"] .stButton > button:hover {
            color: #ffffff !important;
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
        
        .video-card {
            border-color: rgba(0, 0, 0, 0.12);
            background: rgba(255, 255, 255, 0.9);
        }
        
        .video-card:hover {
            border-color: rgba(13, 110, 253, 0.4);
            box-shadow: 0 4px 12px rgba(13, 110, 253, 0.15);
        }
        
        .divider {
            border-color: rgba(0, 0, 0, 0.1);
        }
        
        /* タレント選択 - ラジオボタン */
        div[role="radiogroup"] label {
            color: #6c757d !important;
        }
        
        div[role="radiogroup"] label:hover {
            color: #212529 !important;
        }
        
        /* 選択されたタレント */
        div[role="radiogroup"] label[data-checked="true"] {
            color: #0d6efd !important;
            font-weight: 600 !important;
        }
        
        div[role="radiogroup"] label[data-checked="true"]:hover {
            color: #0a58ca !important;
        }
        
        /* サイドバーのタレント選択ボタン */
        section[data-testid="stSidebar"] .stButton > button {
            color: #6c757d !important;
        }
        
        section[data-testid="stSidebar"] .stButton > button:hover {
            color: #212529 !important;
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

# サイドバー
with st.sidebar:
    st.header("🎵 RK Music")
    st.subheader("タレント")
    
    available_talents = get_available_talents()
    
    if not available_talents:
        st.warning("⚠️ データが見つかりません")
        selected_talent = None
    else:
        if st.session_state.selected_talent is None:
            st.session_state.selected_talent = available_talents[0]
        
        # 各タレントのバナー画像付きボタンを表示
        for i, talent in enumerate(available_talents):
            # バナー画像URLを辞書から取得
            banner_url = TALENT_BANNERS.get(talent)
            
            # 選択中かどうか
            is_selected = (talent == st.session_state.selected_talent)
            border_color = "#0d6efd" if is_selected else "rgba(128, 128, 128, 0.2)"
            text_color = "#0d6efd" if is_selected else "rgba(128, 128, 128, 0.7)"
            font_weight = "600" if is_selected else "400"
            
            if banner_url:
                # カード全体のコンテナ
                st.markdown(f'<div style="border: 2px solid {border_color}; border-radius: 8px; overflow: hidden; margin-bottom: 2px;">', unsafe_allow_html=True)
                
                # 画像とボタンを横並びで配置
                col_img, col_btn = st.columns([0.85, 0.15])
                
                with col_img:
                    # 画像を表示
                    st.markdown(f'<img src="{banner_url}" style="width: 100%; display: block; margin: 0;">', unsafe_allow_html=True)
                
                with col_btn:
                    # 小さな選択ボタン
                    if st.button("選択", key=f"talent_btn_{i}"):
                        st.session_state.selected_talent = talent
                        st.rerun()
                
                # タレント名を下部に表示
                st.markdown(f'<div style="padding: 4px 8px; text-align: center; font-size: 12px; font-weight: {font_weight}; color: {text_color}; margin: 0;">{talent}</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # バナー画像がない場合は普通のボタン
                if st.button(talent, key=f"talent_btn_{i}", use_container_width=True):
                    st.session_state.selected_talent = talent
                    st.rerun()
        
        selected_talent = st.session_state.selected_talent

if not selected_talent:
    st.info("📡 タレントを選択してください")
    st.stop()

history = load_history(selected_talent)
logs = load_logs(selected_talent)
video_history = load_video_daily_history(selected_talent)

if not history:
    st.error(f"❌ {selected_talent} のデータが見つかりません")
    st.stop()

channel_stats = history.get('channel_stats', {})

# ページヘッダー
st.markdown('<div class="page-header">', unsafe_allow_html=True)
st.title(f"📺 {channel_stats.get('チャンネル名', selected_talent)}")
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# チャンネル統計
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("登録者数", f"{channel_stats['登録者数']:,}人")
with col2:
    st.metric("総再生数", f"{channel_stats['総再生数']:,}回")
with col3:
    st.metric("動画数", f"{channel_stats['動画数']:,}本")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# 動画リスト
if not video_history:
    st.info("📡 動画データを蓄積中です。")
else:
    # 全動画をリストアップ
    video_list = []
    for video_id, video_data in video_history.items():
        records = video_data.get('records', [])
        if len(records) >= 1:
            current_record = records[-1]
            current_views = current_record.get('再生数', 0)
            current_likes = current_record.get('高評価数', 0)  # 新しく追加
            
            # 前日比を計算
            views_change = 0
            views_change_rate = 0.0
            likes_change = 0
            likes_change_rate = 0.0
            
            if len(records) >= 2:
                previous_record = records[-2]
                previous_views = previous_record.get('再生数', 0)
                previous_likes = previous_record.get('高評価数', 0)
                
                views_change = current_views - previous_views
                if previous_views > 0:
                    views_change_rate = (views_change / previous_views) * 100
                
                likes_change = current_likes - previous_likes
                if previous_likes > 0:
                    likes_change_rate = (likes_change / previous_likes) * 100
            
            video_list.append({
                'id': video_id,
                'タイトル': video_data['タイトル'],
                'type': video_data.get('type', 'Movie'),
                '再生数': current_views,
                '再生数増加': views_change,
                '再生数増加率': views_change_rate,
                '高評価数': current_likes,
                '高評価増加': likes_change,
                '高評価増加率': likes_change_rate
            })
    
    # 再生数でソート
    video_list.sort(key=lambda x: x['再生数'], reverse=True)
    
    # 動画カードを表示
    for video in video_list:
        video_url = f"https://www.youtube.com/watch?v={video['id']}"
        type_emoji = "📹" if video['type'] == 'Movie' else ("🎬" if video['type'] == 'Short' else "🔴")
        
        st.markdown(f'''
        <div class="video-card">
            <div class="video-title">
                {type_emoji} <a href="{video_url}" target="_blank">{video['タイトル']}</a>
            </div>
            <div class="video-stats">
                <div class="stat-item">
                    <div class="stat-label">再生数</div>
                    <div>
                        <span class="stat-value">{video['再生数']:,}</span>
                        <span class="stat-change {'positive-change' if video['再生数増加'] > 0 else 'neutral-change'}">
                            ({video['再生数増加']:,} / {video['再生数増加率']:.1f}%)
                        </span>
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">高評価数</div>
                    <div>
                        <span class="stat-value">{video['高評価数']:,}</span>
                        <span class="stat-change {'positive-change' if video['高評価増加'] > 0 else 'neutral-change'}">
                            ({video['高評価増加']:,} / {video['高評価増加率']:.1f}%)
                        </span>
                    </div>
                </div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
