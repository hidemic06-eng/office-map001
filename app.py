import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from streamlit_gsheets import GSheetsConnection
import base64
import os
import qrcode
from io import BytesIO
import time

# 1. ページ設定
st.set_page_config(layout="wide", page_title="オフィス座席マップ", initial_sidebar_state="expanded")

# --- 【重要】日本時間を強制設定 ---
JST = timezone(timedelta(hours=9))

# 2. Google Sheets 接続
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 定数・座標設定
FILENAME = "office_layout_with_islands.png"
APP_URL = "https://office-map001-d7unukgvvdas4njkzblvyv.streamlit.app/"

@st.cache_data
def get_coords():
    # (中略: 以前と同じ座標ロジックを保持)
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

seat_coords = get_coords()

# 4. データ読み込み
def load_data():
    try:
        return conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

df_now = load_data()

# --- CSS設定（スマホ対応強化） ---
st.markdown("""
    <style>
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    .blinking-dot { animation: blink 1s infinite; z-index: 30; }
    .main .block-container { padding-top: 0.5rem; }
    
    /* 更新情報ボックス：スマホではシンプルに表示 */
    .info-box {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        border-left: 5px solid #FF4B4B;
        margin-bottom: 10px;
    }
    @media (min-width: 768px) {
        .info-box { position: absolute; top: 10px; right: 20px; width: 220px; z-index: 100; }
    }
    </style>
    """, unsafe_allow_html=True)

# 5. 【修正】秒刻みで動くカウントダウン & 日本時間表示
# st.emptyを使って、この部分だけを書き換えます
info_placeholder = st.empty()

with info_placeholder.container():
    if not df_now.empty:
        # 最新の行を取得
        latest_row = df_now.sort_values("更新日時", ascending=False).iloc[0]
        # 保存された時間がUTC(9時間前)の場合を考慮し、強制的にJSTへ調整
        raw_val = latest_row["更新日時"]
        # 表示側でもHH:MMをしっかり出す
        display_time = str(raw_val).split(" ")[-1][:5]
        user_name = latest_row["担当者"]
        
        st.markdown(f"""
            <div class="info-box">
                <div style="font-size: 0.8em; color: #555;">最終更新: {user_name}さん</div>
                <div style="font-size: 1.6em; font-weight: bold; color: #FF4B4B;">{display_time}</div>
                <div style="font-size: 0.75em; color: #888;">🔃 次回更新まであと <span id='cd'>--</span>秒</div>
            </div>
        """, unsafe_allow_html=True)

# --- サイドバー ---
st.sidebar.header("🔍 検索・操作")
search_query = st.sidebar.text_input("名前検索")

mode = st.sidebar.radio("モード", ["チェックイン", "退席"])
if mode == "チェックイン":
    u_name = st.sidebar.text_input("👤 お名前")
    all_seats = list(seat_coords.keys())
    island_list = sorted(list(set([s.split('-')[0] for s in all_seats if '-' in s])))
    selected_group = st.sidebar.selectbox("🏝️ エリア", ["未選択"] + island_list + ["支社長席", "集中ブース"])
    
    if selected_group != "未選択":
        target_seats = [s for s in all_seats if s.startswith(selected_group)] if selected_group != "集中ブース" else [s for s in all_seats if "集中ブース" in s]
        s_id = st.sidebar.selectbox("📍 座席番号", target_seats)
        
        if st.sidebar.button("確定", use_container_width=True, type="primary"):
            if u_name:
                # 【修正】保存時に確実に日本時間を文字列で送る
                now_jst_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
                new_df = df_now[df_now["担当者"] != u_name].copy()
                new_row = pd.DataFrame([[now_jst_str, u_name, s_id]], columns=["更新日時", "担当者", "座席番号"])
                conn.update(worksheet="Sheet1", data=pd.concat([new_df, new_row], ignore_index=True))
                st.rerun()

elif mode == "退席":
    current_members = df_now["担当者"].unique().tolist()
    if current_members:
        target = st.sidebar.selectbox("👤 誰が退席しますか？", current_members)
        if st.sidebar.button("退席確定", use_container_width=True):
            conn.update(worksheet="Sheet1", data=df_now[df_now["担当者"] != target])
            st.rerun()

# 6. マップ描画
st.subheader("📍 座席マップ")
if os.path.exists(FILENAME):
    with open(FILENAME, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    map_html = f'''<div style="position: relative; width:100%;"><img src="data:image/png;base64,{b64_string}" style="width:100%; border-radius:10px;">'''
    for seat_id, pos in seat_coords.items():
        occ = df_now[df_now["座席番号"] == seat_id]
        label = occ.iloc[0]["担当者"] if not occ.empty else ""
        is_highlight = (search_query and label and search_query in label)
        dot_color = "#FFD700" if is_highlight else ("#FF4B4B" if label else "#28a745")
        
        map_html += f'''<div class="{"blinking-dot" if is_highlight else ""}" style="position: absolute; width:1.2%; height:1.2%; border-radius: 50%; top:{pos["top"]}%; left:{pos["left"]}%; background-color:{dot_color}; border:1px solid white; transform:translate(-50%, -50%); z-index:20;"></div>'''
        if label or is_highlight:
            map_html += f'''<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:min(1.5vw, 10px); background:rgba(0,0,0,0.7); color:white; padding:1px 3px; border-radius:2px; transform:translate(-50%, -150%); white-space:nowrap; z-index:15;">{label if label else seat_id}</div>'''
    map_html += '</div>'
    st.markdown(map_html, unsafe_allow_html=True)

# 7. JavaScriptによる「本物のカウントダウン」
st.components.v1.html(f"""
    <script>
    var count = 30;
    var timer = setInterval(function(){{
        count--;
        var el = window.parent.document.getElementById('cd');
        if(el) el.innerText = count;
        if(count <= 0){{
            clearInterval(timer);
            window.parent.location.reload();
        }}
    }}, 1000);
    </script>
    """, height=0)
