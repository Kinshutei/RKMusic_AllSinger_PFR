#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YouTube チャンネル統計ダッシュボード (Streamlit Cloud版)
"""

import streamlit as st
from datetime import datetime, timedelta, timezone
import json
import os
import io
import zipfile

# ページ設定
st.set_page_config(
    page_title="YouTube Stats Dashboard",
    page_icon="📊",
    layout="wide"
)

# セッション状態の初期化
if 'selected_talent' not in st.session_state:
    st.session_state.selected_talent = None

# タレントのバナー画像URL（固定）
TALENT_BANNERS = {
    "Dashboard": "https://yt3.googleusercontent.com/2v9rGWzb4RyFeGYm6DMYT--YVfSNvzZ8bSDKz6bGQDJfO-BQ1_9vr-Fex3M7kxs3ytyTqId7=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
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
    "Diα":       "https://yt3.googleusercontent.com/U6LeCOlVJ4m68-o30FpSEjVuwFxmPYYzDD3je0Sy_SuSYesAmoUvIkSyP81M2l73qOIcpNP7=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
    "妃玖":      "https://yt3.googleusercontent.com/u3MLvApeviPLt_-RPfqiPB1ZPeEtaBknWDv-jKyzMGEijRaireQ2zfxK1HmkuDtJpUIW_uVXxEY=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj",
}

# ==============================================================================
# CSS
# ==============================================================================
DASHBOARD_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');

html, body, [class*="css"],
h1, h2, h3, h4, h5, h6, p, span, div, button, input, select, textarea,
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
.stButton > button, .stTextInput, .stSelectbox {
    font-family: 'Noto Sans JP', sans-serif !important;
}

section[data-testid="stSidebar"] h2:first-of-type {
    margin-top: 0 !important;
}

[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarHeader"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

.block-container {
    padding-top: 4.5rem !important;
    padding-bottom: 1rem !important;
}

.main [data-testid="stVerticalBlock"] { gap: 0 !important; }
.main [data-testid="stMarkdownContainer"] > div { margin-bottom: 0 !important; }

/* ボタン共通 */
.stButton > button {
    width: 100%;
    border-radius: 8px !important;
    padding: 4px 16px !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
    margin: 3px 0 !important;
    background-color: #ffffff !important;
    color: #212529 !important;
    border: 1px solid rgba(0, 0, 0, 0.15) !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
}

.stButton > button:hover {
    transform: translateY(-2px);
    background-color: #f0f7ff !important;
    border: 1px solid #0d6efd !important;
    box-shadow: 0 4px 8px rgba(13, 110, 253, 0.15) !important;
}

/* サイドバー：バナーボタン */
section[data-testid="stSidebar"] .stButton > button {
    height: 48px !important;
    min-height: 48px !important;
    border-radius: 8px !important;
    width: 100% !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    color: #6c757d !important;
    text-shadow:
        -1px -1px 0 #fff,  1px -1px 0 #fff,
        -1px  1px 0 #fff,  1px  1px 0 #fff,
        -2px  0   0 #fff,  2px  0   0 #fff,
         0   -2px 0 #fff,  0    2px 0 #fff !important;
    background-size: cover !important;
    background-position: center top !important;
    display: flex !important;
    align-items: flex-start !important;
    justify-content: flex-start !important;
    padding: 6px 8px 0 8px !important;
}

section[data-testid="stSidebar"] .stButton > button p {
    font-size: 18px !important;
    font-weight: 700 !important;
    color: #000000 !important;
    text-align: left !important;
    width: 100% !important;
    margin: 0 !important;
    text-shadow:
        -1px -1px 0 #fff,  1px -1px 0 #fff,
        -1px  1px 0 #fff,  1px  1px 0 #fff,
        -2px  0   0 #fff,  2px  0   0 #fff,
         0   -2px 0 #fff,  0    2px 0 #fff !important;
    transition: filter 0.2s ease !important;
    box-shadow: none !important;
}

section[data-testid="stSidebar"] .stButton > button:hover {
    transform: none !important;
    filter: brightness(1.15) !important;
    color: #212529 !important;
}

section[data-testid="stSidebar"] .stButton > button:active {
    filter: brightness(0.9) !important;
}

section[data-testid="stSidebar"] .stButton { margin: 0 !important; padding: 0 !important; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0 !important; }
section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] { margin: 0 !important; padding: 0 !important; }
section[data-testid="stSidebar"] div[data-testid="element-container"] { margin: 0 !important; padding: 0 !important; }

/* ラジオボタン */
div[role="radiogroup"] { gap: 0 !important; }
div[role="radiogroup"] label {
    display: flex !important;
    align-items: center !important;
    padding: 8px 0 !important;
    margin: 0 !important;
    border-bottom: 1px solid rgba(128, 128, 128, 0.2) !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    color: #495057 !important;
}
div[role="radiogroup"] label:hover { padding-left: 4px !important; color: #212529 !important; }
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] { margin-left: 0 !important; }
div[role="radiogroup"] label > div:first-child { display: none !important; }
div[role="radiogroup"] label p { margin: 0 !important; font-size: 15px !important; }
div[role="radiogroup"] label[data-checked="true"] { color: #0d6efd !important; font-weight: 600 !important; }

/* 見出し */
h1 { margin-bottom: 0.5rem !important; padding-bottom: 0 !important; }
h2, h3 { font-weight: 700 !important; margin-top: 0.5rem !important; margin-bottom: 0.5rem !important; }
p { margin-bottom: 0.5rem !important; }
a { text-decoration: none !important; transition: all 0.2s ease !important; font-weight: 500 !important; }
a:hover { text-decoration: underline !important; }

div[data-testid="stCaption"] { font-size: 12px !important; margin-top: 0.2rem !important; margin-bottom: 0.2rem !important; }
hr { margin-top: 0.5rem !important; margin-bottom: 0.5rem !important; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { border-radius: 4px; }

/* メトリクス */
div[data-testid="stMetric"] {
    padding: 10px !important;
    border-radius: 10px;
    background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
    border: 1px solid rgba(0, 0, 0, 0.06);
}
div[data-testid="stMetricLabel"] { font-size: 13px !important; font-weight: 500 !important; }
div[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 700 !important; }

/* セレクトボックス */
div[data-baseweb="select"] { margin-bottom: 0.5rem !important; }
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
div[data-testid="stSelectbox"] label { font-weight: 600 !important; font-size: 14px !important; color: #0d6efd !important; }
div[data-testid="stSelectbox"] { margin-bottom: 8px !important; }

/* 背景 */
.stApp { background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #f0f2f6 0%, #e8eaf0 100%); }
section[data-testid="stSidebar"] > div { background: transparent; }

/* 動画カード */
.video-card {
    border: 1px solid rgba(0, 0, 0, 0.1);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    transition: all 0.2s ease;
    background: #ffffff;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.video-card:hover {
    transform: translateY(-2px);
    border-color: rgba(13, 110, 253, 0.4) !important;
    box-shadow: 0 4px 12px rgba(13, 110, 253, 0.12) !important;
}
.video-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.video-title a { color: #212529 !important; }
.video-title a:hover { color: #0d6efd !important; }

.stat-change { font-size: 14px; margin-left: 8px; }
.positive-change { color: #28a745; }
.neutral-change  { color: #6c757d; }

.divider { border-top: 1px solid rgba(0, 0, 0, 0.1); margin: 20px 0; }
.page-header { margin-bottom: 8px; }
.page-header h1 { margin-bottom: 0 !important; }

div[data-testid="column"] { padding: 0 4px !important; }
div[data-testid="column"]:first-child { padding-left: 0 !important; }
div[data-testid="column"]:last-child  { padding-right: 0 !important; }
</style>
"""

# CSSを適用
st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)


# ==============================================================================
# 定数
# ==============================================================================
TALENT_ORDER = [
    "Dashboard",
    "焔魔るり", "HACHI", "瀬戸乃とと", "水瀬凪",
    "KMNZ", "VESPERBELL", "CULUA", "NEUN", "MEDA", "CONA",
    "IMI", "XIDEN", "ヨノ", "LEWNE", "羽緒", "Cil", "深影", "wouca",
    "Diα", "妃玖"
]

# ==============================================================================
# データ読み込み
# ==============================================================================
def _load_snapshots():
    """all_snapshots.json を読み込んで返す（失敗時は None）"""
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, 'all_snapshots.json')
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _load_history_year():
    """all_history_{year}.json を読み込んで返す（失敗時は None）"""
    year = datetime.now(timezone(timedelta(hours=9))).strftime('%Y')
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, f'all_history_{year}.json')
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_csv_data():
    """
    全タレントのデータからチャンネル統計・動画統計CSVのバイト列を返す。
    エンコード: Shift-JIS (cp932)
    戻り値: (ch_bytes, vid_bytes, error_message)
    """
    snapshots = _load_snapshots() or {}
    history   = _load_history_year() or {}

    # 対象タレント（Dashboard除く・snapshotsに存在するもの）
    talents = [t for t in TALENT_ORDER if t != "Dashboard" and t in snapshots]

    # 全履歴から最新日(N日)を確定
    all_dates = set()
    for talent in talents:
        ch_stats = history.get(talent, {}).get('_channel_stats', {})
        all_dates.update(ch_stats.keys())
    if not all_dates:
        return None, None, "履歴データが見つかりません（all_history_{year}.json）"

    n_date = sorted(all_dates)[-1]
    n_dates = [
        (datetime.strptime(n_date, '%Y-%m-%d') - timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(1, 6)
    ]

    # ── チャンネル統計CSV ──────────────────────────
    ch_header = ['タレント', '登録者数(N)']
    for i in range(1, 6):
        ch_header.append(f'登録者増({i}D前)')
    ch_header += ['総再生数(N)']
    for i in range(1, 6):
        ch_header.append(f'総再生増({i}D前)')
    ch_header.append('動画数(N)')

    ch_rows = [ch_header]
    for talent in talents:
        snap_ch = snapshots.get(talent, {}).get('channel_stats', {})
        hist_ch = history.get(talent, {}).get('_channel_stats', {})

        subs_diffs, views_diffs = [], []
        prev = n_date
        for d in n_dates:
            p, c = hist_ch.get(prev, {}), hist_ch.get(d, {})
            subs_diffs.append(p.get('登録者数', 0) - c.get('登録者数', 0) if p and c else '')
            views_diffs.append(p.get('総再生数', 0) - c.get('総再生数', 0) if p and c else '')
            prev = d

        ch_rows.append(
            [talent, snap_ch.get('登録者数', 0)]
            + subs_diffs
            + [snap_ch.get('総再生数', 0)]
            + views_diffs
            + [snap_ch.get('動画数', 0)]
        )

    # ── 動画統計CSV ────────────────────────────────
    vid_header = ['タレント', '動画ID', 'タイトル', 'type', '再生数(N)']
    for i in range(1, 6):
        vid_header.append(f'再生増({i}D前)')
    vid_header.append('高評価数(N)')
    for i in range(1, 6):
        vid_header.append(f'高評価増({i}D前)')

    vid_rows = [vid_header]
    for talent in talents:
        snap_videos = snapshots.get(talent, {}).get('videos', {})
        hist_talent = history.get(talent, {})

        for vid_id, vid_snap in snap_videos.items():
            if not isinstance(vid_snap, dict):
                continue
            hist_records = hist_talent.get(vid_id, {})
            hist_records = hist_records.get('records', {}) if isinstance(hist_records, dict) else {}

            views_diffs, likes_diffs = [], []
            prev = n_date
            for d in n_dates:
                p, c = hist_records.get(prev, {}), hist_records.get(d, {})
                views_diffs.append(p.get('再生数', 0) - c.get('再生数', 0) if p and c else '')
                likes_diffs.append(p.get('高評価数', 0) - c.get('高評価数', 0) if p and c else '')
                prev = d

            vid_rows.append(
                [talent, vid_id, vid_snap.get('タイトル', vid_id), vid_snap.get('type', ''),
                 vid_snap.get('再生数', 0)]
                + views_diffs
                + [vid_snap.get('高評価数', 0)]
                + likes_diffs
            )

    # ── CSV → Shift-JIS バイト列 ──────────────────
    def rows_to_sjis(rows):
        buf = io.StringIO()
        for row in rows:
            buf.write(','.join(
                f'"{str(v)}"' if ',' in str(v) else str(v)
                for v in row
            ) + '\r\n')
        return buf.getvalue().encode('cp932', errors='replace')

    return rows_to_sjis(ch_rows), rows_to_sjis(vid_rows), None


def get_available_talents():
    """all_snapshots.json に存在するタレントを固定順で返す。Dashboardは常に先頭"""
    snapshots = _load_snapshots()
    existing = set(snapshots.keys()) if snapshots else set()
    ordered = [t for t in TALENT_ORDER if t in existing or t == "Dashboard"]
    extras  = sorted(t for t in existing if t not in TALENT_ORDER)
    return ordered + extras


def build_dashboard_data():
    """
    Dashboardページ用のデータを組み立てる。
    all_history_{year}.json から最新日(N)と前日(N-1)を取得して前日比を計算。
    戻り値:
        singer_data  : [{talent, subs_n, subs_diff, views_n, views_diff}, ...]
        video_data   : {
            'Movie':       [{talent, vid_id, title, views_n, views_diff, views_rate,
                             likes_n, likes_diff, comments_n, comments_diff}, ...],
            'Short':       [...],
            'LiveArchive': [...]
        }
        n_date       : str  基準日 (YYYY-MM-DD)
        error        : str or None
    """
    history   = _load_history_year() or {}
    snapshots = _load_snapshots()    or {}

    talents = [t for t in TALENT_ORDER if t != "Dashboard" and t in snapshots]
    if not talents:
        return None, None, None, "スナップショットデータが見つかりません"

    # N日を確定
    all_dates = set()
    for talent in talents:
        all_dates.update(history.get(talent, {}).get('_channel_stats', {}).keys())
    if not all_dates:
        return None, None, None, "履歴データが見つかりません（all_history_{year}.json）"

    sorted_dates = sorted(all_dates)
    n_date = sorted_dates[-1]
    p_date = sorted_dates[-2] if len(sorted_dates) >= 2 else None

    # ── Singer部門 ──────────────────────────────
    singer_data = []
    for talent in talents:
        # 現在値はsnapshotsから取得（確実に存在する）
        snap_ch = snapshots.get(talent, {}).get('channel_stats', {})
        subs_n  = snap_ch.get('登録者数', 0)
        views_n = snap_ch.get('総再生数', 0)

        # 前日比はhistoryから計算
        ch     = history.get(talent, {}).get('_channel_stats', {})
        n_rec  = ch.get(n_date, {})
        p_rec  = ch.get(p_date, {}) if p_date else {}

        subs_diff  = (n_rec.get('登録者数', 0) - p_rec.get('登録者数', 0)) if n_rec and p_rec else None
        views_diff = (n_rec.get('総再生数', 0) - p_rec.get('総再生数', 0)) if n_rec and p_rec else None

        def rate(val, diff):
            if diff is None or val is None:
                return None
            base = val - diff
            return round(diff / base * 100, 1) if base > 0 else None

        singer_data.append({
            'talent':      talent,
            'subs_n':      subs_n,
            'subs_diff':   subs_diff,
            'subs_rate':   rate(subs_n, subs_diff),
            'views_n':     views_n,
            'views_diff':  views_diff,
            'views_rate':  rate(views_n, views_diff),
        })

    # ── 動画部門 ────────────────────────────────
    video_data = {'Movie': [], 'Short': [], 'LiveArchive': []}

    for talent in talents:
        talent_hist = history.get(talent, {})
        snap_videos = snapshots.get(talent, {}).get('videos', {})

        for vid_id, snap in snap_videos.items():
            if not isinstance(snap, dict):
                continue
            vtype = snap.get('type', 'Movie')
            if vtype not in video_data:
                continue

            hist_vid = talent_hist.get(vid_id, {})
            records  = hist_vid.get('records', {}) if isinstance(hist_vid, dict) else {}
            title    = snap.get('タイトル') or (hist_vid.get('タイトル') if isinstance(hist_vid, dict) else None) or vid_id

            n_rec = records.get(n_date, {})
            p_rec = records.get(p_date, {}) if p_date else {}

            views_n    = n_rec.get('再生数', 0)
            likes_n    = n_rec.get('高評価数', 0)
            comments_n = n_rec.get('コメント数', 0)

            views_diff    = (views_n    - p_rec.get('再生数', 0))    if p_rec else None
            likes_diff    = (likes_n    - p_rec.get('高評価数', 0))  if p_rec else None
            comments_diff = (comments_n - p_rec.get('コメント数', 0)) if p_rec else None

            def vrate(val, diff):
                if diff is None or val is None:
                    return None
                base = val - diff
                return round(diff / base * 100, 1) if base > 0 else None

            video_data[vtype].append({
                'talent':        talent,
                'vid_id':        vid_id,
                'title':         title,
                'views_n':       views_n,
                'views_diff':    views_diff,
                'views_rate':    vrate(views_n, views_diff),
                'likes_n':       likes_n,
                'likes_diff':    likes_diff,
                'comments_n':    comments_n,
                'comments_diff': comments_diff,
            })

    return singer_data, video_data, n_date, None



    """all_snapshots.json に存在するタレントを固定順で返す。総合ダッシュボードは常に先頭"""
    snapshots = _load_snapshots()
    existing = set(snapshots.keys()) if snapshots else set()
    ordered = [t for t in TALENT_ORDER if t in existing or t == "Dashboard"]
    extras  = sorted(t for t in existing if t not in TALENT_ORDER)
    return ordered + extras


def load_channel_stats(talent_name):
    """チャンネル統計を返す。日付ネスト形式なら最新日付分を、フラットならそのまま返す"""
    snapshots = _load_snapshots()
    if not snapshots:
        return {}
    raw_ch = snapshots.get(talent_name, {}).get('channel_stats', {})
    if not raw_ch:
        return {}
    # 値がdictなら日付ネスト形式 → 最新日付を返す
    first_val = next(iter(raw_ch.values()))
    if isinstance(first_val, dict):
        latest_date = sorted(raw_ch.keys())[-1]
        return raw_ch[latest_date]
    # フラット形式（{"登録者数": X, ...}）ならそのまま返す
    return raw_ch


def load_video_history(talent_name):
    """動画履歴を返す（videosキー配下）"""
    snapshots = _load_snapshots()
    if not snapshots:
        return {}
    videos = snapshots.get(talent_name, {}).get('videos', {})
    return {k: v for k, v in videos.items() if isinstance(v, dict)}


def get_channel_stats_diff(talent_name):
    """チャンネル統計の前日比を返す。データ不足時は None"""
    snapshots = _load_snapshots()
    if not snapshots:
        return None
    ch_stats = snapshots.get(talent_name, {}).get('channel_stats', {})
    if not ch_stats:
        return None
    # フラット形式（日次1レコードのみ）の場合は前日比なし
    first_val = next(iter(ch_stats.values()))
    if not isinstance(first_val, dict):
        return None
    # 日付ネスト形式
    sorted_dates = sorted(ch_stats.keys())
    if len(sorted_dates) < 2:
        return None
    today     = ch_stats[sorted_dates[-1]]
    yesterday = ch_stats[sorted_dates[-2]]
    return {
        '登録者数': today['登録者数'] - yesterday['登録者数'],
        '総再生数': today['総再生数'] - yesterday['総再生数'],
        '動画数':   today['動画数']   - yesterday['動画数'],
    }


# ==============================================================================
# サイドバー
# ==============================================================================
selected_talent = None  # フォールバック用に先に初期化

with st.sidebar:
    st.header("+++ RK Music All Singer+++")

    try:
        available_talents = get_available_talents()
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        available_talents = []

    if not available_talents:
        st.warning("⚠️ データが見つかりません")
        selected_talent = None
    else:
        if st.session_state.selected_talent is None:
            st.session_state.selected_talent = available_talents[0]

        selected_talent = st.session_state.selected_talent

        # バナーボタン用CSS（markerセレクタ方式）
        css_rules = []
        for talent in available_talents:
            banner_url = TALENT_BANNERS.get(talent, "")
            is_selected = (talent == selected_talent)
            key    = f"talent_btn_{talent}"
            border = "3px solid #0d6efd" if is_selected else "1px solid rgba(128,128,128,0.3)"

            bg_rule = f"background-image: url('{banner_url}') !important;" if banner_url else "background-image: none !important;"
            css_rules.append(f"""
            section[data-testid="stSidebar"] div:has(> #marker_{key}) ~ div div[data-testid="stButton"] button,
            section[data-testid="stSidebar"] div:has(#marker_{key}) + div div[data-testid="stButton"] button {{
                {bg_rule}
                background-color: transparent !important;
                border: {border} !important;
            }}
            """)

        if css_rules:
            st.markdown(f"<style>{''.join(css_rules)}</style>", unsafe_allow_html=True)

        # マーカー + ボタンを描画
        for talent in available_talents:
            key = f"talent_btn_{talent}"
            st.markdown(
                f'<div id="marker_{key}" style="display:none;height:0;margin:0;padding:0;"></div>',
                unsafe_allow_html=True
            )
            if st.button(talent, key=key, use_container_width=True):
                st.session_state.selected_talent = talent
                st.rerun()

# ==============================================================================
# メインエリア
# ==============================================================================
if not selected_talent:
    st.info("📡 タレントを選択してください")
    st.stop()

# 総合ダッシュボード
if selected_talent == "Dashboard":
    banner_url = TALENT_BANNERS.get("Dashboard", "")
    if banner_url:
        st.markdown(f"""
        <div style="width:100%; height:200px; border-radius:12px; overflow:hidden; margin-bottom:0;">
            <img src="{banner_url}" style="width:100%; height:100%; object-fit:cover; object-position:center top;">
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr style="margin:10px 0 16px 0; border:none; border-top:1px solid rgba(128,128,128,0.2);">', unsafe_allow_html=True)
    st.markdown(
        '<span style="font-size:16px; font-weight:700;">📥 CSVエクスポート</span> <span style="font-size:13px; color:#888; margin-left:12px;">2ファイル（チャンネル統計・動画統計）をZIP（Shift-JIS形式）にてDL。</span>',
        unsafe_allow_html=True
    )

    if st.button("CSVを生成してダウンロード", type="primary"):
        with st.spinner("データを集計中..."):
            ch_bytes, vid_bytes, err = build_csv_data()

        if err:
            st.error(f"❌ {err}")
        else:
            today_str = datetime.now().strftime('%Y%m%d')
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f'channel_stats_{today_str}.csv', ch_bytes)
                zf.writestr(f'video_stats_{today_str}.csv',   vid_bytes)
            zip_buf.seek(0)
            st.download_button(
                label="⬇️ ZIPをダウンロード",
                data=zip_buf,
                file_name=f'rkmusic_stats_{today_str}.zip',
                mime='application/zip'
            )
            st.success("✅ 生成完了！ボタンをクリックしてダウンロードしてください。")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── データ取得 ──────────────────────────────────
    singer_data, video_data, n_date, err = build_dashboard_data()
    if err:
        st.error(f"❌ {err}")
        st.stop()

    st.markdown(f'<div style="font-size:12px; color:#888; margin-bottom:8px;">集計基準日: {n_date}（前日比）</div>', unsafe_allow_html=True)

    # ── ヘルパー ────────────────────────────────────
    def diff_html(diff, show_rate=False, rate=None):
        if diff is None:
            return '<span style="color:#aaa;">—</span>'
        color = '#28a745' if diff > 0 else ('#dc3545' if diff < 0 else '#888')
        sign  = '+' if diff >= 0 else ''
        rate_str = ''
        if show_rate and rate is not None:
            rate_str = f' <span style="font-size:11px; opacity:0.8;">({rate:+.1f}%)</span>'
        return f'<span style="color:{color};">{sign}{diff:,}{rate_str}</span>'

    def rank_table(rows, value_key, diff_key, rate_key=None, top_n=None):
        """ランキングテーブルHTMLを生成"""
        if top_n:
            rows = sorted(rows, key=lambda x: (x[diff_key] or -999999), reverse=True)[:top_n]
        html = '<table style="width:100%; border-collapse:collapse; font-size:12px;">'
        for i, r in enumerate(rows):
            bg = 'rgba(13,110,253,0.04)' if i % 2 == 0 else 'transparent'
            val  = r.get(value_key, 0)
            diff = r.get(diff_key)
            rate = r.get(rate_key) if rate_key else None
            show_rate = rate_key is not None
            html += f'''
            <tr style="background:{bg};">
                <td style="padding:4px 6px; font-weight:600; white-space:nowrap;">{i+1}.</td>
                <td style="padding:4px 6px; max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"
                    title="{r.get("talent","")}">{r.get("talent","")}</td>
                <td style="padding:4px 6px; text-align:right; white-space:nowrap;">{val:,}</td>
                <td style="padding:4px 6px; text-align:right; white-space:nowrap;">{diff_html(diff, show_rate, rate)}</td>
            </tr>'''
        html += '</table>'
        return html

    def video_rank_table(rows, value_key, diff_key, rate_key=None, top_n=10):
        """動画ランキングテーブルHTML"""
        rows = sorted(rows, key=lambda x: (x[diff_key] or -999999), reverse=True)[:top_n]
        html = '<table style="width:100%; border-collapse:collapse; font-size:12px;">'
        for i, r in enumerate(rows):
            bg = 'rgba(13,110,253,0.04)' if i % 2 == 0 else 'transparent'
            val  = r.get(value_key, 0)
            diff = r.get(diff_key)
            rate = r.get(rate_key) if rate_key else None
            show_rate = rate_key is not None
            vid_url = f"https://www.youtube.com/watch?v={r['vid_id']}"
            title   = r.get('title', r['vid_id'])
            short_title = title[:22] + '…' if len(title) > 22 else title
            html += f'''
            <tr style="background:{bg};">
                <td style="padding:4px 4px; font-weight:600; white-space:nowrap;">{i+1}.</td>
                <td style="padding:4px 4px; max-width:160px;">
                    <div style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                        <span style="font-size:10px; color:#888;">{r.get("talent","")}</span><br>
                        <a href="{vid_url}" target="_blank" style="font-size:12px;" title="{title}">{short_title}</a>
                    </div>
                </td>
                <td style="padding:4px 4px; text-align:right; white-space:nowrap; font-size:12px;">{val:,}</td>
                <td style="padding:4px 4px; text-align:right; white-space:nowrap;">{diff_html(diff, show_rate, rate)}</td>
            </tr>'''
        html += '</table>'
        return html

    # ── Singer部門 ──────────────────────────────────
    st.markdown('### 🎤 Singer部門')
    col_subs, col_views = st.columns(2)

    subs_sorted  = sorted(singer_data, key=lambda x: (x['subs_diff']  or -999999), reverse=True)
    views_sorted = sorted(singer_data, key=lambda x: (x['views_diff'] or -999999), reverse=True)

    with col_subs:
        st.markdown('**登録者数**')
        st.markdown(rank_table(subs_sorted, 'subs_n', 'subs_diff', 'subs_rate'), unsafe_allow_html=True)

    with col_views:
        st.markdown('**総再生数**')
        st.markdown(rank_table(views_sorted, 'views_n', 'views_diff', 'views_rate'), unsafe_allow_html=True)

    # ── 動画部門 ────────────────────────────────────
    section_labels = {
        'Movie':       '🎬 Movie部門',
        'Short':       '📱 Short部門',
        'LiveArchive': '🔴 LiveArchive部門',
    }

    for vtype, label in section_labels.items():
        rows = video_data.get(vtype, [])
        if not rows:
            continue
        st.markdown(f'### {label}')
        col_v, col_l, col_c = st.columns(3)

        with col_v:
            st.markdown('**再生数**')
            st.markdown(video_rank_table(rows, 'views_n', 'views_diff', 'views_rate'), unsafe_allow_html=True)
        with col_l:
            st.markdown('**高評価数**')
            st.markdown(video_rank_table(rows, 'likes_n', 'likes_diff'), unsafe_allow_html=True)
        with col_c:
            st.markdown('**コメント数**')
            st.markdown(video_rank_table(rows, 'comments_n', 'comments_diff'), unsafe_allow_html=True)

    st.stop()

try:
    channel_stats = load_channel_stats(selected_talent)
    video_history = load_video_history(selected_talent)
    diff          = get_channel_stats_diff(selected_talent)
except Exception as e:
    st.error(f"❌ データ読み込みエラー: {e}")
    st.stop()

if not channel_stats and not video_history:
    st.error(f"❌ {selected_talent} のデータが見つかりません")
    st.stop()

# デバッグ削除済み

# --- バナー＋チャンネル統計 ---
banner_url = TALENT_BANNERS.get(selected_talent, "")
subs  = channel_stats.get('登録者数', 0)
views = channel_stats.get('総再生数', 0)
vids  = channel_stats.get('動画数',   0)

if banner_url:
    st.markdown(f"""
    <div style="width:100%; height:200px; border-radius:12px; overflow:hidden; margin-bottom:0;">
        <img src="{banner_url}" style="width:100%; height:100%; object-fit:cover; object-position:center top;">
    </div>
    """, unsafe_allow_html=True)
else:
    st.subheader(selected_talent)


def _fmt_diff(val):
    """前日比を (+123) / (-45) / (±0) 形式のHTMLで返す"""
    if val is None:
        return ""
    if val > 0:
        return f'<span style="font-size:14px; color:#28a745;"> (+{val:,})</span>'
    elif val < 0:
        return f'<span style="font-size:14px; color:#dc3545;"> ({val:,})</span>'
    else:
        return f'<span style="font-size:14px; opacity:0.5;"> (±0)</span>'


_d = diff or {}
st.markdown(f"""
<div style="display:flex; gap:32px; align-items:baseline; margin:10px 0 6px 4px;">
    <span style="font-size:16px;">登録者数：<strong style="font-size:20px;">{subs:,}</strong>{_fmt_diff(_d.get('登録者数'))}</span>
    <span style="font-size:16px;">総再生数：<strong style="font-size:20px;">{views:,}</strong>{_fmt_diff(_d.get('総再生数'))}</span>
    <span style="font-size:16px;">動画数：<strong style="font-size:20px;">{vids:,}</strong>{_fmt_diff(_d.get('動画数'))}</span>
</div>
<hr style="margin:6px 0 8px 0; border:none; border-top:1px solid rgba(128,128,128,0.2);">
""", unsafe_allow_html=True)

# --- 動画リスト ---
if not video_history:
    st.info("📡 動画データを蓄積中です。")
    st.stop()

# 動画データを整形
video_list = []
for video_id, video_data in video_history.items():
    records = video_data.get('records', {})

    if records:
        # 日付別履歴あり → 最新レコードを使用
        sorted_dates   = sorted(records.keys())
        current_record = records[sorted_dates[-1]]
        current_views  = current_record.get('再生数', 0)
        current_likes  = current_record.get('高評価数', 0)

        # 1D〜5D の前日比
        daily_views, daily_likes = [], []
        for i in range(1, 6):
            if len(sorted_dates) > i:
                dv = records[sorted_dates[-i]].get('再生数', 0)   - records[sorted_dates[-(i+1)]].get('再生数', 0)
                dl = records[sorted_dates[-i]].get('高評価数', 0) - records[sorted_dates[-(i+1)]].get('高評価数', 0)
            else:
                dv, dl = None, None
            daily_views.append(dv)
            daily_likes.append(dl)
    else:
        # フラット形式（スナップショット）
        current_views = video_data.get('再生数', 0)
        current_likes = video_data.get('高評価数', 0)
        daily_views   = [None] * 5
        daily_likes   = [None] * 5

    video_list.append({
        'id':           video_id,
        'タイトル':     video_data.get('タイトル', video_id),
        'type':         video_data.get('type', 'Movie'),
        '再生数':       current_views,
        '再生数5d増加': sum(v for v in daily_views if v is not None),
        '高評価数':     current_likes,
        '高評価5d増加': sum(v for v in daily_likes if v is not None),
        '再生数daily':  daily_views,
        '高評価daily':  daily_likes,
    })

# ソート選択
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
col_label, col_select = st.columns([1, 5], vertical_alignment="center")
with col_label:
    st.markdown("**🔽 並び替え**")
with col_select:
    sort_option = st.selectbox(
        "並び替え",
        ["📊 再生数TOP", "👍 高評価TOP", "📊📈 [再]5日増加TOP", "👍💹 [高]5日増加TOP"],
        label_visibility="collapsed"
    )

sort_key_map = {
    "📊 再生数TOP":      '再生数',
    "👍 高評価TOP":      '高評価数',
    "📊📈 [再]5日増加TOP": '再生数5d増加',
    "👍💹 [高]5日増加TOP": '高評価5d増加',
}
video_list.sort(key=lambda x: x[sort_key_map[sort_option]], reverse=True)

# 動画カードを表示
def fmt_diff(v):
    if v is None:
        return "—"
    return f"+{v:,}" if v >= 0 else f"{v:,}"

for video in video_list:
    video_url  = f"https://www.youtube.com/watch?v={video['id']}"
    type_emoji = "📹" if video['type'] == 'Movie' else ("🎬" if video['type'] == 'Short' else "🔴")

    v1d = video['再生数daily'][0]
    l1d = video['高評価daily'][0]

    # 2D〜5D テーブル
    day_headers, view_vals, like_vals = [], [], []
    for i in range(1, 5):
        v = video['再生数daily'][i]
        l = video['高評価daily'][i]
        if v is None:
            break
        day_headers.append(f"{i+1}D")
        view_vals.append(fmt_diff(v))
        like_vals.append(fmt_diff(l))

    header_cells = '<td style="padding:2px 12px 2px 0; font-size:11px; color:#aaa;"></td>' + "".join(
        f'<td style="padding:2px 16px 2px 0; font-size:11px; color:#aaa; font-weight:500;">{d}</td>'
        for d in day_headers
    )
    view_row_cells = '<td style="padding:2px 12px 2px 0; font-size:11px; color:#888;">再生</td>' + "".join(
        f'<td style="padding:2px 16px 2px 0; font-size:12px; font-weight:600;">{v}</td>'
        for v in view_vals
    )
    like_row_cells = '<td style="padding:2px 12px 2px 0; font-size:11px; color:#888;">高評価</td>' + "".join(
        f'<td style="padding:2px 16px 2px 0; font-size:12px; font-weight:600;">{v}</td>'
        for v in like_vals
    )

    day_table = f"""
    <table style="border-collapse:collapse; margin-top:6px;">
        <tr>{header_cells}</tr>
        <tr>{view_row_cells}</tr>
        <tr>{like_row_cells}</tr>
    </table>
    """ if day_headers else ""

    st.markdown(f'''
    <div class="video-card">
        <div class="video-title">
            {type_emoji} <a href="{video_url}" target="_blank">{video['タイトル']}</a>
        </div>
        <div style="margin-top:6px; font-size:13px;">
            <span style="margin-right:24px;">
                再生数：<strong>{video['再生数']:,}</strong>
                <span class="stat-change {'positive-change' if v1d and v1d > 0 else 'neutral-change'}" style="font-size:12px;">
                    ({fmt_diff(v1d)})
                </span>
            </span>
            <span>
                高評価：<strong>{video['高評価数']:,}</strong>
                <span class="stat-change {'positive-change' if l1d and l1d > 0 else 'neutral-change'}" style="font-size:12px;">
                    ({fmt_diff(l1d)})
                </span>
            </span>
        </div>
        {day_table}
    </div>
    ''', unsafe_allow_html=True)
