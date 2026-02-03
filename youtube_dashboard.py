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

# テーマに応じたCSS - HTMLとして直接埋め込む
def apply_theme_css(theme):
    """テーマに応じたCSSを適用"""
    
    base_css = """
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Noto Sans JP', sans-serif !important;
    }
    
    /* タブ */
    button[data-baseweb="tab"] {
        background: transparent !important;
        font-weight: 500 !important;
        padding: 12px 24px !important;
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
        padding: 12px 20px !important;
        font-size: 16px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
        margin: 4px 0 !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
    }
    
    /* サブヘッダー */
    h2, h3 {
        font-weight: 700 !important;
        margin-bottom: 16px !important;
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
        padding: 16px;
        border-radius: 10px;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 14px !important;
        font-weight: 500 !important;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 700 !important;
    }
    """
    
    if theme == 'dark':
        theme_css = base_css + """
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
            padding: 20px;
            margin: 10px 0;
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
        """
    else:  # light mode
        theme_css = base_css + """
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
            padding: 20px;
            margin: 10px 0;
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
        """
    
    # HTMLコンポーネントとして埋め込み（表示されないように）
    st.components.v1.html(
        f"<style>{theme_css}</style>",
        height=0,
    )

# CSSを適用（画面に表示されない）
apply_theme_css(st.session_state.theme)

# 以下、元のコードと同じ...
# （キリ番のリスト以降は変更なし）
