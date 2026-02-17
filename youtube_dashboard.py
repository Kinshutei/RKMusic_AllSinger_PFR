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
if 'selected_videos' not in st.session_state:
    st.session_state.selected_videos = []
if 'show_views_graph' not in st.session_state:
    st.session_state.show_views_graph = True
if 'show_likes_graph' not in st.session_state:
    st.session_state.show_likes_graph = True

# タレントのバナー画像URL（固定）
TALENT_BANNERS = {
    "焔魔るり":   "https://yt3.googleusercontent.com/Sjt4hfgnhyLYngZTGuYb3cGKfqMdVL79wrto3PcjvxaZiirEoa-Cn_0q9UgZOMarKWGwd_hLn_o=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "HACHI":     "https://yt3.googleusercontent.com/gOqLGXVHj4l1-548h0H_GsH6ZRuDFTuzJye5MawZm0GohZ_1edqU4_Sd-Px7tw4fMsXSbz4tKA=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "瀬戸乃とと": "https://yt3.googleusercontent.com/8mHCpdJXkzkfGTz7N_Z5O_4xmkMnb8td3zYe1AIxOdKtO8WTpP44DHuchzpUubitCxHE1SyU=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "水瀬凪":    "https://yt3.googleusercontent.com/CpGbPRFm_tT618nWpvh0_U3sIctl4-3hNycqAV70ydq0kUIBUtPnUCe_LdtWlAM2r_QRsEhdgg=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "KMNZ":      "https://yt3.googleusercontent.com/4Z4kNGIXFCU1vgZpOh1LcNv4vKoQyHMgpmsgVMY6I3fy-d9oNoRMeqfALcSZVJKcTLd_5ktK2Q=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "VESPERBELL":"https://yt3.googleusercontent.com/MUU0223P2Ck50rNH0geqrg3SsJrLTrQmlG5on9JdoSzVFCtiIBwFuHQtyJRCdOP9YWSehcUY=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "CULUA":     "https://yt3.googleusercontent.com/YE8Y6f6yB_YsmNvPiJmQIrX01vB6_JigcocQH4c2tDMKw4g1_InZ_xU6V4ip0GTo_koNuVtttA=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "NEUN":      "https://yt3.googleusercontent.com/92FhDNKbUc5YMZPDE1FpTI7TzWWap9vEyVCDAW0DbKDfGifCxrrYKb7e0eqGxDoCzJs4VnYS=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "MEDA":      "https://yt3.googleusercontent.com/BjhJaO8s00ICRRos5sMhN-uLvU_OLUQ0GaNc6UKBSuEHFrK0qiUxY4UjmuNtUlKLb_dLwAmXI5s=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "CONA":      "https://yt3.googleusercontent.com/Q0tNjasT6PWnov1ddaIc57unKiD1-6ecRoNOERV-yiGBVdOaCwE5VA2IzEaGeiK36z4JabqjP5U=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "IMI":       "https://yt3.googleusercontent.com/aZTkCpaTRHpZhvhXOca7LYwJuCD0kh_fk6QKyTvS8ZMjT8dX7Soiv2k3L3HqlWVreZoFc0lb1w=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "XIDEN":     "https://yt3.googleusercontent.com/JIzwr_xsRzmL4vdr63a9IkmzCVlVpamZ3bPvZxiSnS-HUz_VoeqIrzPLlE0Xkh9Oq6B66Cz1nFE=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "ヨノ":      "https://yt3.googleusercontent.com/dx7U88GkoPj5IrNNGoXHNKWWzIqRsYhIuBYSZNp8Xlh9dJ34UzOCc3YafVLs4Mbo1nIsUfjIvg=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "LEWNE":     "https://yt3.googleusercontent.com/TjOjwrUdPkWglNkEgvhXt8dS36kqyKB7XwjMWwnnwWg_VgrN0EMm_XXTTR_WtI18AceNz-uY=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "羽緒":      "https://yt3.googleusercontent.com/IwgIc2L5HabEWLCkJ0tqTfZ5qaME9AM5QWYEgdwzjJM-peacKVl0dzDYB9kG5osRBIpn8unOgOs=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "Cil":       "https://yt3.googleusercontent.com/mmDg12VBINfcBTBCq-wS6tA4fF7UVDZn6HsLhHvXuAgTBZzmAgFOaZeeQQYDjc_Vmv0tpgxZ5Q=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "深影":      "https://yt3.googleusercontent.com/6REyrT4s7DrjAvRL0yJUJJxi3Ahb59XtcnnDNpu7lC7sojUKthxvBIWJDVSyExFi1BOyJPzZWg=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "wouca":     "https://yt3.googleusercontent.com/VIJQxQkEkRO2OqxIYlabQLRbpeyRiGdZxjLad7YzVjT3tbXkE24XKL_ZirI1RDUMHQBsY7hK=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
}

# テーマに応じたCSS
def get_theme_css(theme):
    """テーマに応じたCSSを返す"""
    
    base_css = """
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Noto Sans JP', sans-serif !important;
    }
    
    /* 英字はCentury Gothic系 */
    h1, h2, h3,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-family: 'Century Gothic', 'Futura', 'Trebuchet MS', 'Noto Sans JP', sans-serif !important;
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
    
    /* サイドバー内のタレント選択ボタン（バナー画像ボタン） */
    section[data-testid="stSidebar"] .stButton > button {
        height: 72px !important;
        min-height: 72px !important;
        border-radius: 8px !important;
        margin-bottom: 4px !important;
        width: 100% !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        color: #000000 !important;
        text-shadow:
            -1px -1px 0 #fff,
             1px -1px 0 #fff,
            -1px  1px 0 #fff,
             1px  1px 0 #fff,
            -2px  0   0 #fff,
             2px  0   0 #fff,
             0   -2px 0 #fff,
             0    2px 0 #fff !important;
        background-size: cover !important;
        background-position: center top !important;
        display: flex !important;
        align-items: flex-end !important;
        justify-content: center !important;
        padding-bottom: 6px !important;
        transition: filter 0.2s ease !important;
        box-shadow: none !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        transform: none !important;
        filter: brightness(1.15) !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:active {
        filter: brightness(0.9) !important;
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
    
    /* 動画ソート用セレクトボックス */
    div[data-testid="stSelectbox"] > div {
        background: rgba(13, 110, 253, 0.05) !important;
        border: 2px solid rgba(13, 110, 253, 0.3) !important;
        border-radius: 8px !important;
        padding: 4px 8px !important;
    }
    
    div[data-testid="stSelectbox"] > div:hover {
        border-color: rgba(13, 110, 253, 0.6) !important;
        background: rgba(13, 110, 253, 0.08) !important;
    }
    
    div[data-testid="stSelectbox"] label {
        font-weight: 600 !important;
        font-size: 14px !important;
        color: #0d6efd !important;
    }
    
    div[data-testid="stSelectbox"] {
        margin-bottom: 8px !important;
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
            background-color: #1e2330 !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
        }
        
        .stButton > button:hover {
            background-color: #262730 !important;
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
            background-color: #ffffff !important;
            color: #212529 !important;
            border: 1px solid #dee2e6 !important;
        }
        
        .stButton > button:hover {
            background-color: #f8f9fa !important;
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

# タレント表示順（固定）
TALENT_ORDER = [
    "焔魔るり", "HACHI", "瀬戸乃とと", "水瀬凪",
    "KMNZ", "VESPERBELL", "CULUA", "NEUN", "MEDA", "CONA",
    "IMI", "XIDEN", "ヨノ", "LEWNE", "羽緒", "Cil", "深影", "wouca"
]

# タレント一覧を取得
def get_available_talents():
    """all_snapshots.jsonに存在するタレントを固定順で返す"""
    if not os.path.exists('all_snapshots.json'):
        return []
    try:
        with open('all_snapshots.json', 'r', encoding='utf-8') as f:
            snapshots = json.load(f)
        existing = set(snapshots.keys())
        # 固定順でフィルタ
        ordered = [t for t in TALENT_ORDER if t in existing]
        # 固定順にないタレントは末尾に追加
        extras = [t for t in existing if t not in TALENT_ORDER]
        return ordered + sorted(extras)
    except:
        return []

def load_history(talent_name):
    """all_snapshots.jsonから指定タレントのデータを読み込む"""
    if not os.path.exists('all_snapshots.json'):
        return None
    try:
        with open('all_snapshots.json', 'r', encoding='utf-8') as f:
            snapshots = json.load(f)
        data = snapshots.get(talent_name)
        if data:
            # 旧形式と互換性を持たせるため channel_stats と videos を返す
            return {
                'channel_stats': data.get('channel_stats', {}),
                'videos': data.get('videos', {})
            }
    except:
        pass
    return None

def load_logs(talent_name):
    """新構造ではログは別管理しないため空を返す（前日比は履歴から計算）"""
    return []

def load_video_daily_history(talent_name):
    """all_history_{year}.jsonから指定タレントの動画履歴を読み込む"""
    # 今年と去年のファイルを確認
    years = [datetime.now().strftime('%Y'), str(int(datetime.now().strftime('%Y')) - 1)]
    for year in years:
        path = f'all_history_{year}.json'
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                if talent_name in history:
                    return history[talent_name]
            except:
                pass
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
    """指定期間の増加数を計算（recordsはdateキーのdict）"""
    if not records or len(records) < 2:
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

    sorted_dates = sorted(records.keys())
    latest_views = records[sorted_dates[-1]].get('再生数', 0)

    cutoff_str = cutoff.strftime('%Y-%m-%d')
    old_views = None
    for date in sorted_dates:
        if date >= cutoff_str:
            old_views = records[date].get('再生数', 0)
            break

    if old_views is not None:
        return latest_views - old_views
    return 0

def get_sorted_records_list(records):
    """recordsのdictを日付順のリストに変換"""
    if not records:
        return []
    return [{'date': d, **v} for d, v in sorted(records.items())]

# サイドバー
with st.sidebar:
    st.header("+++ RK Music All Singer+++")
    
    available_talents = get_available_talents()
    
    if not available_talents:
        st.warning("⚠️ データが見つかりません")
        selected_talent = None
    else:
        if st.session_state.selected_talent is None:
            st.session_state.selected_talent = available_talents[0]

        selected_talent = st.session_state.selected_talent

        # 全タレントのバナーボタン用CSSを一括注入（markerセレクタ方式）
        css_rules = []
        for talent in available_talents:
            banner_url = TALENT_BANNERS.get(talent, "")
            is_selected = (talent == selected_talent)
            key = f"talent_btn_{talent}"
            border = "3px solid #0d6efd" if is_selected else "1px solid rgba(128,128,128,0.3)"

            if banner_url:
                # ~ (一般兄弟) + :has() で DOM ラッパーを透過して対象ボタンを特定
                css_rules.append(f"""
                section[data-testid="stSidebar"] div:has(> #marker_{key}) ~ div div[data-testid="stButton"] button,
                section[data-testid="stSidebar"] div:has(#marker_{key}) + div div[data-testid="stButton"] button {{
                    background-image: url('{banner_url}') !important;
                    background-color: transparent !important;
                    border: {border} !important;
                }}
                """)
            else:
                css_rules.append(f"""
                section[data-testid="stSidebar"] div:has(> #marker_{key}) ~ div div[data-testid="stButton"] button,
                section[data-testid="stSidebar"] div:has(#marker_{key}) + div div[data-testid="stButton"] button {{
                    background-image: none !important;
                    border: {border} !important;
                }}
                """)

        if css_rules:
            st.markdown(f"<style>{''.join(css_rules)}</style>", unsafe_allow_html=True)

        # 各タレントのマーカー + ボタンを描画
        for talent in available_talents:
            key = f"talent_btn_{talent}"
            st.markdown(
                f'<div id="marker_{key}" style="display:none;height:0;margin:0;padding:0;"></div>',
                unsafe_allow_html=True
            )
            if st.button(talent, key=key, use_container_width=True):
                st.session_state.selected_talent = talent
                st.session_state.selected_videos = []
                st.rerun()

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

# 前日比計算（logsから取得）
subscribers_change = 0
subscribers_change_rate = 0.0
total_views_change = 0
total_views_change_rate = 0.0
video_count_change = 0
video_count_change_rate = 0.0

if len(logs) >= 2:
    current_log = logs[-1]
    previous_log = logs[-2]
    
    # 登録者数の変化
    current_subs = current_log.get('登録者数', 0)
    previous_subs = previous_log.get('登録者数', 0)
    subscribers_change = current_subs - previous_subs
    if previous_subs > 0:
        subscribers_change_rate = (subscribers_change / previous_subs) * 100
    
    # 総再生数の変化
    current_views = current_log.get('総再生数', 0)
    previous_views = previous_log.get('総再生数', 0)
    total_views_change = current_views - previous_views
    if previous_views > 0:
        total_views_change_rate = (total_views_change / previous_views) * 100
    
    # 動画数の変化
    current_videos = current_log.get('動画数', 0)
    previous_videos = previous_log.get('動画数', 0)
    video_count_change = current_videos - previous_videos
    if previous_videos > 0:
        video_count_change_rate = (video_count_change / previous_videos) * 100

with col1:
    st.metric(
        "登録者数", 
        f"{channel_stats['登録者数']:,}人",
        f"{subscribers_change:+,} ({subscribers_change_rate:+.1f}%)" if subscribers_change != 0 else None
    )
with col2:
    st.metric(
        "総再生数", 
        f"{channel_stats['総再生数']:,}回",
        f"{total_views_change:+,} ({total_views_change_rate:+.1f}%)" if total_views_change != 0 else None
    )
with col3:
    st.metric(
        "動画数", 
        f"{channel_stats['動画数']:,}本",
        f"{video_count_change:+,}" if video_count_change != 0 else None
    )

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# グラフエリア（選択された動画がある場合のみ表示）
if st.session_state.selected_videos and video_history:
    st.subheader("📈 選択動画の推移")
    
    # グラフ表示内容選択
    col_graph1, col_graph2 = st.columns([1, 4])
    with col_graph1:
        show_views = st.checkbox("📊 再生数", value=st.session_state.show_views_graph, key="views_check")
        show_likes = st.checkbox("👍 高評価数", value=st.session_state.show_likes_graph, key="likes_check")
        st.session_state.show_views_graph = show_views
        st.session_state.show_likes_graph = show_likes
    
    # グラフ作成
    if show_views or show_likes:
        fig = go.Figure()
        
        for video_id in st.session_state.selected_videos:
            if video_id not in video_history:
                continue
            
            video_data = video_history[video_id]
            video_title = video_data.get('タイトル', '')
            records = video_data.get('records', {})
            
            if not records:
                continue
            
            # データを日付順にソート
            sorted_records = get_sorted_records_list(records)
            
            dates = []
            views = []
            likes = []
            
            for record in sorted_records:
                dates.append(record.get('date', ''))
                views.append(record.get('再生数', 0))
                likes.append(record.get('高評価数', 0))
            
            # 短いタイトルを作成（最初の30文字）
            short_title = video_title[:30] + '...' if len(video_title) > 30 else video_title
            
            # 再生数のグラフ
            if show_views and dates:
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=views,
                    mode='lines+markers',
                    name=f"{short_title} (再生数)",
                    line=dict(width=2),
                    marker=dict(size=6)
                ))
            
            # 高評価数のグラフ
            if show_likes and dates:
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=likes,
                    mode='lines+markers',
                    name=f"{short_title} (高評価)",
                    line=dict(width=2, dash='dot'),
                    marker=dict(size=6, symbol='diamond')
                ))
        
        # レイアウト設定
        fig.update_layout(
            height=400,
            xaxis_title="日付",
            yaxis_title="数値",
            hovermode='x unified',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            ),
            margin=dict(l=50, r=150, t=30, b=50)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 グラフに表示する項目を選択してください")
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# 動画リスト
if not video_history:
    st.info("📡 動画データを蓄積中です。")
else:
    # 全動画をリストアップ
    video_list = []
    for video_id, video_data in video_history.items():
        records = video_data.get('records', {})
        if not records:
            continue

        sorted_dates = sorted(records.keys())
        current_record = records[sorted_dates[-1]]
        current_views = current_record.get('再生数', 0)
        current_likes = current_record.get('高評価数', 0)

        views_change = 0
        views_change_rate = 0.0
        likes_change = 0
        likes_change_rate = 0.0

        if len(sorted_dates) >= 2:
            previous_record = records[sorted_dates[-2]]
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
    
    # ソート選択
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    sort_option = st.selectbox(
        "🔽 並び替え",
        ["📊 再生数TOP", "👍 高評価TOP", "📊📈 [再]増加率TOP", "👍💹 [高]増加率TOP"]
    )
    
    # ソート適用
    if sort_option == "📊 再生数TOP":
        video_list.sort(key=lambda x: x['再生数'], reverse=True)
    elif sort_option == "👍 高評価TOP":
        video_list.sort(key=lambda x: x['高評価数'], reverse=True)
    elif sort_option == "📊📈 [再]増加率TOP":
        video_list.sort(key=lambda x: x['再生数増加率'], reverse=True)
    elif sort_option == "👍💹 [高]増加率TOP":
        video_list.sort(key=lambda x: x['高評価増加率'], reverse=True)
    
    # 動画カードを表示
    for idx, video in enumerate(video_list):
        video_url = f"https://www.youtube.com/watch?v={video['id']}"
        type_emoji = "📹" if video['type'] == 'Movie' else ("🎬" if video['type'] == 'Short' else "🔴")
        
        # チェックボックスとカードを横並び
        col_check, col_card = st.columns([0.05, 0.95])
        
        with col_check:
            is_selected = video['id'] in st.session_state.selected_videos
            if st.checkbox("", value=is_selected, key=f"video_check_{idx}_{video['id']}"):
                if video['id'] not in st.session_state.selected_videos:
                    st.session_state.selected_videos.append(video['id'])
            else:
                if video['id'] in st.session_state.selected_videos:
                    st.session_state.selected_videos.remove(video['id'])
        
        with col_card:
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
