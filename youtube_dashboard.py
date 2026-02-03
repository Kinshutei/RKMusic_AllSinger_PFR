#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube チャンネル統計ダッシュボード (Streamlit Cloud版)
自動取得されたデータを表示
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import json
import os

# ページ設定
st.set_page_config(
    page_title="YouTube統計ダッシュボード",
    page_icon="📊",
    layout="wide"
)

# キリ番のリスト
MILESTONES = [5000, 10000, 50000, 100000, 500000, 1000000, 5000000, 10000000]

def load_history():
    """履歴データを読み込む"""
    history_file = 'video_history.json'
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None

def load_logs():
    """ログデータを読み込む"""
    log_file = 'check_log.json'
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

# メインUI
st.title("📊 YouTube チャンネル統計ダッシュボード")
st.markdown("*自動取得データを表示中（3時間ごとに更新）*")
st.markdown("---")

# データ読み込み
history = load_history()
logs = load_logs()

# サイドバー
with st.sidebar:
    st.header("📊 統計情報")
    
    if history:
        st.success("✓ データ読み込み完了")
        st.caption(f"最終更新: {history.get('timestamp', 'N/A')}")
        
        if 'channel_stats' in history:
            stats = history['channel_stats']
            st.metric("登録者数", f"{stats['登録者数']:,}人")
            st.metric("総再生数", f"{stats['総再生数']:,}回")
            st.metric("動画数", f"{stats['動画数']:,}本")
    else:
        st.warning("⚠️ データが見つかりません")
        st.info("初回の自動実行を待っています...")
    
    st.markdown("---")
    
    if logs:
        st.caption(f"ログ件数: {len(logs)}件")
    
    st.markdown("---")
    st.caption("🔄 自動更新: 3時間ごと")

# メインコンテンツ
if not history:
    st.info("📡 データを取得中です。初回の自動実行（GitHub Actions）を待っています。")
    st.markdown("""
    ### システム情報
    
    - **自動実行頻度**: 3時間ごと
    - **データソース**: GitHub Actions
    - **次回更新**: 次の実行タイミングまでお待ちください
    
    初回実行後、このページを更新してデータを確認できます。
    """)
    st.stop()

# チャンネル情報表示
if 'channel_stats' in history:
    stats = history['channel_stats']
    
    st.header(f"📺 {stats['チャンネル名']}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("登録者数", f"{stats['登録者数']:,}人")
    with col2:
        st.metric("総再生数", f"{stats['総再生数']:,}回")
    with col3:
        st.metric("動画数", f"{stats['動画数']:,}本")
    with col4:
        st.metric("最終更新", stats.get('取得日時', 'N/A'))
    
    st.markdown("---")

# タブ表示
tab1, tab2, tab3 = st.tabs(["📈 推移グラフ", "🎯 最新のキリ番", "📋 実行ログ"])

with tab1:
    st.subheader("登録者数・総再生数の推移")
    
    if logs and len(logs) > 1:
        # ログから推移データを作成
        log_df = pd.DataFrame([
            {
                '日時': log['timestamp'],
                '登録者数': log['channel_stats']['登録者数'],
                '総再生数': log['channel_stats']['総再生数'],
                '動画数': log['channel_stats']['動画数']
            }
            for log in logs if 'channel_stats' in log
        ])
        
        # 登録者数推移
        fig1 = px.line(
            log_df,
            x='日時',
            y='登録者数',
            title='登録者数の推移',
            markers=True
        )
        fig1.update_layout(height=400)
        st.plotly_chart(fig1, use_container_width=True)
        
        # 総再生数推移
        fig2 = px.line(
            log_df,
            x='日時',
            y='総再生数',
            title='総再生数の推移',
            markers=True
        )
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
        
        # 統計表示
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "登録者増加",
                f"+{log_df['登録者数'].iloc[-1] - log_df['登録者数'].iloc[0]:,}人",
                f"過去{len(logs)}回の実行"
            )
        with col2:
            st.metric(
                "再生数増加",
                f"+{log_df['総再生数'].iloc[-1] - log_df['総再生数'].iloc[0]:,}回",
                f"過去{len(logs)}回の実行"
            )
    else:
        st.info("📊 推移データを蓄積中です。数回の自動実行後にグラフが表示されます。")

with tab2:
    st.subheader("🎉 最近達成したキリ番")
    
    # ログから最近のキリ番達成を表示
    recent_achievements = []
    for log in reversed(logs[-20:]):  # 最新20件
        if 'achievements' in log and log['achievements']:
            for achievement in log['achievements']:
                recent_achievements.append({
                    '日時': log['timestamp'],
                    'タイトル': achievement['タイトル'],
                    'キリ番': achievement['キリ番'],
                    '再生数': achievement['現在の再生数'],
                    '動画ID': achievement['動画ID']
                })
    
    if recent_achievements:
        for i, ach in enumerate(recent_achievements[:10], 1):
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{ach['タイトル']}**")
                    st.caption(f"🎯 {ach['キリ番']:,}回突破 - {ach['日時']}")
                with col2:
                    st.metric("現在", f"{ach['再生数']:,}回")
                    video_url = f"https://www.youtube.com/watch?v={ach['動画ID']}"
                    st.markdown(f"[▶️ 動画を見る]({video_url})")
                st.markdown("---")
    else:
        st.info("まだキリ番達成はありません。次回の自動チェックをお待ちください！")

with tab3:
    st.subheader("📋 自動実行ログ")
    
    if logs:
        # ログを表として表示
        log_display = []
        for log in reversed(logs[-20:]):  # 最新20件
            achievements_count = len(log.get('achievements', []))
            log_display.append({
                '実行日時': log['timestamp'],
                'チャンネル名': log['channel_stats']['チャンネル名'],
                '登録者数': f"{log['channel_stats']['登録者数']:,}人",
                '総再生数': f"{log['channel_stats']['総再生数']:,}回",
                '動画数': f"{log['channel_stats']['動画数']:,}本",
                'キリ番達成': f"{achievements_count}件" if achievements_count > 0 else "-"
            })
        
        log_df = pd.DataFrame(log_display)
        st.dataframe(log_df, use_container_width=True, height=600)
        
        # ダウンロードボタン
        csv = log_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 ログをダウンロード",
            data=csv,
            file_name=f"execution_log_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("まだ実行ログがありません。")

# フッター
st.markdown("---")
st.caption("Powered by GitHub Actions + Streamlit Cloud | 自動更新: 3時間ごと")
