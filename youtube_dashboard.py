#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube チャンネル統計ダッシュボード (Streamlit Cloud版)
動画別分析機能付き
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
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

def load_video_daily_history():
    """動画別履歴データを読み込む"""
    history_file = 'video_daily_history.json'
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def filter_data_by_period(data, period_type, period_value=None):
    """期間でデータをフィルタリング"""
    if period_type == 'ALL':
        return data
    
    now = datetime.now()
    
    if period_type == 'RELATIVE':
        if period_value == '1DAY':
            start_date = now - timedelta(days=1)
        elif period_value == '1WEEK':
            start_date = now - timedelta(days=7)
        elif period_value == '1MONTH':
            start_date = now - timedelta(days=30)
        elif period_value == '4MONTHS':
            start_date = now - timedelta(days=120)
        elif period_value == '6MONTHS':
            start_date = now - timedelta(days=180)
        else:
            return data
        
        filtered = []
        for record in data:
            try:
                record_date = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S')
                if record_date >= start_date:
                    filtered.append(record)
            except:
                continue
        return filtered
    
    elif period_type == 'YEAR':
        year = int(period_value)
        filtered = []
        for record in data:
            try:
                record_date = datetime.strptime(record['timestamp'], '%Y-%m-%d %H:%M:%S')
                if record_date.year == year:
                    filtered.append(record)
            except:
                continue
        return filtered
    
    return data

def get_available_years(video_history):
    """データがある年のリストを取得"""
    years = set()
    for video_id, video_data in video_history.items():
        for record in video_data.get('records', []):
            try:
                timestamp = record['timestamp']
                year = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').year
                years.add(year)
            except:
                continue
    return sorted(list(years), reverse=True)

# メインUI
st.title("📊 YouTube チャンネル統計ダッシュボード")
st.markdown("*自動取得データを表示中（3時間ごとに更新）*")
st.markdown("---")

# データ読み込み
history = load_history()
logs = load_logs()
video_history = load_video_daily_history()

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
    
    if video_history:
        st.caption(f"動画履歴: {len(video_history)}本")
    
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
tab1, tab2, tab3, tab4 = st.tabs(["📈 推移グラフ", "🎯 最新のキリ番", "📊 動画別分析", "📋 実行ログ"])

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
    st.subheader("📊 動画別分析")
    
    if not video_history:
        st.info("📡 動画別履歴データを蓄積中です。次回の自動実行後に表示されます。")
    else:
        # 期間選択UI
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**相対期間**")
            relative_period = st.selectbox(
                "今日から見て",
                ['ALL', '1 DAY', '1 WEEK', '1 MONTH', '4 MONTHS', '6 MONTHS'],
                key='relative'
            )
        
        with col2:
            st.markdown("**絶対期間（年）**")
            available_years = get_available_years(video_history)
            if available_years:
                year_period = st.selectbox(
                    "特定の年",
                    ['選択なし'] + [str(year) for year in available_years],
                    key='year'
                )
            else:
                year_period = '選択なし'
                st.caption("データが蓄積されると表示されます")
        
        st.markdown("---")
        
        # 期間タイプを決定
        if year_period != '選択なし':
            period_type = 'YEAR'
            period_value = year_period
            period_label = f"{year_period}年"
        elif relative_period == 'ALL':
            period_type = 'ALL'
            period_value = None
            period_label = "全期間"
        else:
            period_type = 'RELATIVE'
            period_value = relative_period.replace(' ', '')
            period_label = relative_period
        
        st.info(f"📅 表示期間: {period_label}")
        
        # 動画選択
        st.markdown("### 動画を選択")
        
        # 動画リストを作成
        video_options = []
        for video_id, video_data in video_history.items():
            title = video_data.get('タイトル', video_id)
            records = video_data.get('records', [])
            if records:
                latest_views = records[-1]['再生数']
                video_options.append({
                    'id': video_id,
                    'label': f"{title} ({latest_views:,}回)",
                    'title': title,
                    'views': latest_views
                })
        
        # 再生数でソート
        video_options.sort(key=lambda x: x['views'], reverse=True)
        
        # TOP10を選択
        selected_videos = st.multiselect(
            "分析する動画を選択（複数選択可）",
            options=[v['id'] for v in video_options],
            format_func=lambda x: next(v['label'] for v in video_options if v['id'] == x),
            default=[v['id'] for v in video_options[:5]] if len(video_options) >= 5 else [v['id'] for v in video_options]
        )
        
        if selected_videos:
            st.markdown("---")
            st.markdown("### 📈 再生数推移グラフ")
            
            # グラフデータを作成
            plot_data = []
            for video_id in selected_videos:
                video_data = video_history[video_id]
                title = video_data.get('タイトル', video_id)
                records = video_data.get('records', [])
                
                # 期間でフィルタ
                filtered_records = filter_data_by_period(records, period_type, period_value)
                
                for record in filtered_records:
                    plot_data.append({
                        '日時': record['timestamp'],
                        '動画': title[:50] + '...' if len(title) > 50 else title,
                        '再生数': record['再生数']
                    })
            
            if plot_data:
                df_plot = pd.DataFrame(plot_data)
                
                # グラフ作成
                fig = px.line(
                    df_plot,
                    x='日時',
                    y='再生数',
                    color='動画',
                    title=f'再生数推移（{period_label}）',
                    markers=True
                )
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
                
                # 伸び率ランキング
                st.markdown("---")
                st.markdown("### 📊 期間内伸び率ランキング")
                
                growth_data = []
                for video_id in selected_videos:
                    video_data = video_history[video_id]
                    title = video_data.get('タイトル', video_id)
                    records = video_data.get('records', [])
                    
                    filtered_records = filter_data_by_period(records, period_type, period_value)
                    
                    if len(filtered_records) >= 2:
                        start_views = filtered_records[0]['再生数']
                        end_views = filtered_records[-1]['再生数']
                        growth = end_views - start_views
                        growth_rate = (growth / start_views * 100) if start_views > 0 else 0
                        
                        growth_data.append({
                            '動画': title,
                            '開始時': start_views,
                            '終了時': end_views,
                            '増加数': growth,
                            '伸び率': f"{growth_rate:.1f}%"
                        })
                
                if growth_data:
                    growth_df = pd.DataFrame(growth_data)
                    growth_df = growth_df.sort_values('増加数', ascending=False)
                    
                    st.dataframe(growth_df, use_container_width=True, height=400)
                else:
                    st.info("期間内のデータが不足しています。")
            else:
                st.warning("選択した期間にデータがありません。")
        else:
            st.info("👆 動画を選択してください")

with tab4:
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
