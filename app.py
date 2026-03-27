import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from streamlit_gsheets import GSheetsConnection
import base64
import os
import urllib.parse

# 1. ページ設定
st.set_page_config(
    layout="wide", 
    page_title="オフィス座席マップ",
    initial_sidebar_state="expanded" 
)

# --- 環境判定 ---
is_test_env = st.secrets.get("env", {}).get("is_test", False)
JST = timezone(timedelta(hours=9))

# 2. Google Sheets 接続
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 定数
FILENAME = "office_layout_with_islands.png"
if is_test_env:
    CURRENT_URL = "https://office-map001-develop.streamlit.app/"
else:
    CURRENT_URL = "https://office-map001-main.streamlit.app/"

# 4. 座標生成
def generate_coords():
    coords = {}
    top_gap = 1.6 
    islands_top = {"A": 18.2, "B": 23.5, "C": 28.9, "D": 34.8, "E": 40.2}
    for label, left_base in islands_top.items():
        for i in range(12):
            coords[f"{label}-{i+1}"] = {"top": 28.5 + (i%6)*6.6, "left": left_base - top_gap if i < 6 else left_base + top_gap}
    islands_mid = {"F": 50.4, "G": 55.9, "H": 61.2, "I": 66.7, "J": 73.8, "K": 79.2}
    for label, left_base in islands_mid.items():
        for i in range(10):
            coords[f"{label}-{i+1}"] = {"top": 28.5 + (i%5)*6.6, "left": left_base - top_gap if i < 5 else left_base + top_gap}
    islands_bottom = {"M": 50.4, "N": 55.9, "O": 61.2, "P": 66.7, "Q": 73.8, "R": 79.2}
    for label, left_base in islands_bottom.items():
        for i in range(8):
            coords[f"{label}-{i+1}"] = {"top": 66.5 + (i%4)*6.6, "left": left_base - top_gap if i < 4 else left_base + top_gap}
    for i in range(5): coords[f"L-{i+1}"] = {"top": 28.5 + i*6.6, "left": 83.0}
    for i in range(4): coords[f"S-{i+1}"] = {"top": 66.5 + i*6.6, "left": 83.0}
    coords["支社長席"] = {"top": 23.5, "left": 12.0}
    for i in range(5): coords[f"集中ブース-{i+1}"] = {"top": 72.5, "left": 3.2 + i*2.1}
    return coords

seat_coords = generate_coords()

def load_data():
    try:
        return conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

# --- 登録コールバック ---
def register_and_clear():
    u_name = st.session_state.get("u_name_input")
    s_id_raw = st.session_state.get("seat_box")
    s_id = s_id_raw.split('（')[0] if s_id_raw else None
    
    if u_name and s_id:
        df_logic = load_data()
        today_str = datetime.now(JST).strftime("%m/%d")
        new_df = df_logic[(df_logic["更新日時"].str.startswith(today_str)) & (df_logic["担当者"] != u_name)].copy()
        new_row = pd.DataFrame([[datetime.now(JST).strftime("%m/%d %H:%M"), u_name, s_id]], columns=["更新日時", "担当者", "座席番号"])
        conn.update(worksheet="Sheet1", data=pd.concat([new_df, new_row], ignore_index=True))
        st.session_state["u_name_input"] = ""
        st.session_state["island_box"] = "未選択"
        if "seat_box" in st.session_state: del st.session_state["seat_box"]

# --- サイドバー：検索 ---
if is_test_env:
    st.sidebar.warning("🛠️ テスト環境実行中")
st.sidebar.header("🔍 担当者検索")
search_query = st.sidebar.text_input("名前を入力", key="search_input")

# --- 自動更新フラグメント ---
@st.fragment(run_every=120)
def main_display(selected_group):
    df_now = load_data()
    if is_test_env:
        st.warning("⚠️ 現在は **テスト環境 (develop)** です。")
    st.title("📍 事務所リアルタイム座席図")

    # CSS設定：常時表示しつつホバーで強調
    st.markdown("""
        <style>
        .seat-container {
            position: absolute;
            width: 1.5%;
            aspect-ratio: 1/1;
            transform: translate(-50%, -50%);
            z-index: 10;
        }
        .seat-dot {
            width: 100%;
            height: 100%;
            border-radius: 50%;
            border: 1px solid white;
            transition: transform 0.2s ease;
        }
        .seat-label {
            position: absolute;
            top: 0;
            left: 50%;
            transform: translate(-50%, -140%);
            font-size: min(1.0vw, 9px);
            padding: 1px 4px;
            border-radius: 2px;
            white-space: nowrap;
            font-weight: bold;
            opacity: 1; /* 【重要】常時表示 */
            transition: all 0.2s;
            pointer-events: none;
            z-index: 100;
        }
        /* ホバー時の強調設定 */
        .seat-container:hover {
            z-index: 500 !important; /* 隣と重なっても一番前に出す */
        }
        .seat-container:hover .seat-dot {
            transform: scale(1.8);
        }
        .seat-container:hover .seat-label {
            font-size: 14px !important; /* ホバー時に文字を大きく */
            background: #000 !important;
            color: #fff !important;
            transform: translate(-50%, -180%);
            z-index: 510;
            box-shadow: 0 4px 8px rgba(0,0,0,0.5);
        }
        /* 検索点滅 */
        @keyframes blink { 0% { box-shadow: 0 0 0 0px rgba(255, 215, 0, 0.7); } 70% { box-shadow: 0 0 0 8px rgba(255, 215, 0, 0); } 100% { box-shadow: 0 0 0 0px rgba(255, 215, 0, 0); } }
        .blinking-dot { 
            animation: blink 1.0s infinite !important;
            background-color: #FFD700 !important;
        }
        .label-highlight {
            background: rgba(255, 215, 0, 0.95) !important;
            color: black !important;
            z-index: 200;
        }
        </style>
        """, unsafe_allow_html=True)

    if os.path.exists(FILENAME):
        with open(FILENAME, "rb") as img_file:
            b64_string = base64.b64encode(img_file.read()).decode()
        
        map_html = f'<div style="position: relative; width:100%; max-width:1200px; margin: auto;"><img src="data:image/png;base64,{b64_string}" style="width:100%; display: block; opacity:0.8;">'
        
        for seat_id, pos in seat_coords.items():
            occ = df_now[df_now["座席番号"] == seat_id]
            label = occ.iloc[0]["担当者"] if not occ.empty else ""
            is_highlight = (search_query and label and search_query in label) or \
                           (selected_group != "未選択" and seat_id.startswith(f"{selected_group}-")) or \
                           (selected_group == seat_id)
            
            dot_color = "#FF4B4B" if label else "#28a745"
            dot_class = "seat-dot blinking-dot" if is_highlight else "seat-dot"
            highlight_class = "label-highlight" if is_highlight else ""
            display_text = label if label else seat_id

            if label or is_highlight:
                map_html += f'''
                <div class="seat-container" style="top:{pos["top"]}%; left:{pos["left"]}%;">
                    <div class="{dot_class}" style="background-color:{dot_color};"></div>
                    <div class="seat-label {highlight_class}" style="background:rgba(0,0,0,0.7); color:white;">{display_text}</div>
                </div>
                '''
            else:
                # 空席はドットのみ（ホバーで座席番号が出る）
                map_html += f'''
                <div class="seat-container" style="top:{pos["top"]}%; left:{pos["left"]}%;">
                    <div class="{dot_class}" style="background-color:{dot_color};"></div>
                    <div class="seat-label" style="background:rgba(0,0,0,0.7); color:white;">{seat_id}</div>
                </div>
                '''
            
        map_html += '</div>'
        st.markdown(map_html, unsafe_allow_html=True)

    if not df_now.empty:
        latest = df_now.sort_values("更新日時", ascending=False).iloc[0]
        st.info(f"🕒 最終更新: **{str(latest['更新日時']).split(' ')[-1]}** ({latest['担当者']}さん)")
    st.caption(f"🔄 最終同期: {datetime.now(JST).strftime('%H:%M:%S')}")

# --- サイドバー：入退室 ---
st.sidebar.markdown("---")
st.sidebar.header("📝 入退室・移動")
df_logic = load_data()
current_members = df_logic["担当者"].unique().tolist()
mode = st.sidebar.radio("操作を選択", ["新しく座る・移動する", "退席する"])

selected_group = "未選択"
if mode == "新しく座る・移動する":
    u_name = st.sidebar.text_input("👤 名前を入力", placeholder="例：田中 太郎", key="u_name_input")
    all_seats = list(seat_coords.keys())
    island_list = sorted(list(set([s.split('-')[0] for s in all_seats if '-' in s])))
    special_list = sorted([s for s in all_seats if '-' not in s])
    selected_group = st.sidebar.selectbox("🏝️ 島・エリアを選択", ["未選択"] + island_list + special_list, key="island_box")
    if selected_group != "未選択":
        if selected_group in special_list: st.session_state["seat_box"] = selected_group
        else:
            raw_seats = [s for s in all_seats if s.startswith(f"{selected_group}-")]
            island_seats = sorted(raw_seats, key=lambda x: int(x.split('-')[1]))
            seat_options = [f"{s}（{'👤 ' + df_logic[df_logic['座席番号']==s].iloc[0]['担当者'] if not df_logic[df_logic['座席番号']==s].empty else '✅ 空席'}）" for s in island_seats]
            st.sidebar.selectbox("📍 座席番号を選択", seat_options, key="seat_box")
        st.sidebar.button("✅ 登録・移動", use_container_width=True, type="primary", on_click=register_and_clear)
elif mode == "退席する" and current_members:
    target_name = st.sidebar.selectbox("👤 誰が退席しますか？", current_members)
    if st.sidebar.button("退席する", use_container_width=True):
        conn.update(worksheet="Sheet1", data=df_logic[df_logic["担当者"] != target_name])
        st.rerun()

main_display(selected_group)

# QRコード
st.sidebar.markdown("---")
encoded_url = urllib.parse.quote(CURRENT_URL)
qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={encoded_url}"
st.sidebar.image(qr_url, caption="スマホで登録・確認", use_container_width=False)
