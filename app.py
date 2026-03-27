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

# --- 環境判定 (Secretsから取得) ---
is_test_env = st.secrets.get("env", {}).get("is_test", False)
JST = timezone(timedelta(hours=9))

# 2. Google Sheets 接続
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 定数・初期設定
FILENAME = "office_layout_with_islands.png"

if is_test_env:
    CURRENT_URL = "https://office-map001-develop.streamlit.app/"
else:
    CURRENT_URL = "https://office-map001-main.streamlit.app/"

# 4. 座席座標の生成
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

# --- 登録・移動処理用のコールバック関数 ---
def register_and_clear():
    # 入力値を取得
    u_name = st.session_state.get("u_name_input")
    s_id = st.session_state.get("seat_box")
    if s_id: s_id = s_id.split('（')[0]
    
    if u_name and s_id:
        # データの読み込みと更新
        df_logic = load_data()
        new_df = df_logic[df_logic["担当者"] != u_name].copy()
        new_row = pd.DataFrame([[datetime.now(JST).strftime("%m/%d %H:%M"), u_name, s_id]], columns=["更新日時", "担当者", "座席番号"])
        conn.update(worksheet="Sheet1", data=pd.concat([new_df, new_row], ignore_index=True))
        
        # 入力値をクリア
        st.session_state["u_name_input"] = ""
        st.session_state["island_box"] = "未選択"
        # seat_boxはisland_boxがリセットされれば自動的にリセットされます

# --- サイドバー：共通UI ---
if is_test_env:
    st.sidebar.warning("🛠️ テスト環境 (別シート接続中)")

st.sidebar.header("🔍 担当者検索")
search_query = st.sidebar.text_input("名前を入力", key="search_input")

# --- 自動更新フラグメント ---
@st.fragment(run_every=120)
def main_display(selected_group):
    df_now = load_data()
    st.title("📍 事務所リアルタイム座席図")

    with st.sidebar.expander("👥 現在の着席者一覧", expanded=False):
        if not df_now.empty:
            df_list = df_now.copy()
            df_list["島"] = df_list["座席番号"].apply(lambda x: x.split('-')[0])
            for island in sorted(df_list["島"].unique()):
                st.markdown(f"**🔹 {island}島・エリア**")
                members = df_list[df_list["島"] == island].sort_values("座席番号")
                cols = st.columns(2)
                for i, (_, row) in enumerate(members.iterrows()):
                    with cols[i % 2]: st.caption(f"🪑{row['座席番号']}\n{row['担当者']}")
        else:
            st.write("着席中のメンバーはいません")

    st.markdown("""
        <style>
        @keyframes blink {
            0% { opacity: 1; transform: translate(-20%, -20%) scale(1.0); box-shadow: 0 0 5px #FFD700; }
            50% { opacity: 0.7; transform: translate(-20%, -20%) scale(1.3); box-shadow: 0 0 15px #FFD700; }
            100% { opacity: 1; transform: translate(-20%, -20%) scale(1.0); box-shadow: 0 0 5px #FFD700; }
        }
        .blinking-dot { 
            animation: blink 0.8s infinite !important; 
            background-color: #FFD700 !important; 
            border: 1.5px solid #FFFFFF !important;
            z-index: 100 !important;
        }
        </style>
        """, unsafe_allow_html=True)

    if os.path.exists(FILENAME):
        with open(FILENAME, "rb") as img_file:
            b64_string = base64.b64encode(img_file.read()).decode()
        
        map_html = f'''<div style="position: relative; width:100%; max-width:1200px; margin: auto;">
                       <img src="data:image/png;base64,{b64_string}" style="width:100%; display: block; opacity:0.8;">'''
        
        for seat_id, pos in seat_coords.items():
            occ = df_now[df_now["座席番号"] == seat_id]
            label = occ.iloc[0]["担当者"] if not occ.empty else ""
            is_highlight = (search_query and label and search_query in label) or \
                           (selected_group != "未選択" and seat_id.startswith(f"{selected_group}-")) or \
                           (selected_group == seat_id)
            
            dot_class = "blinking-dot" if is_highlight else ""
            dot_color = "#FF4B4B" if label else "#28a745"
            map_html += f'''<div class="{dot_class}" style="position: absolute; width:1.2%; aspect-ratio: 1 / 1; border-radius: 50%; 
                            top:{pos["top"]}%; left:{pos["left"]}%; background-color:{dot_color}; border:1px solid white; 
                            transform:translate(-20%, -20%); z-index:10;"></div>'''
            if label or is_highlight:
                display_text = label if label else seat_id
                label_bg = "rgba(255, 215, 0, 0.9)" if is_highlight else "rgba(0,0,0,0.7)"
                label_txt = "black" if is_highlight else "white"
                map_html += f'''<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:min(1.1vw, 9px); 
                                background:{label_bg}; color:{label_txt}; padding:1px 3px; border-radius:2px; 
                                transform:translate(-20%, -140%); white-space:nowrap; z-index:110; font-weight:bold;">{display_text}</div>'''
        map_html += '</div>'
        st.markdown(map_html, unsafe_allow_html=True)

    if not df_now.empty:
        latest = df_now.sort_values("更新日時", ascending=False).iloc[0]
        st.info(f"🕒 最終更新: **{str(latest['更新日時']).split(' ')[-1]}** ({latest['担当er']}さん)")
    st.caption(f"🔄 最終同期: {datetime.now(JST).strftime('%H:%M:%S')}")

# --- 入退室管理ロジック ---
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
        if selected_group in special_list:
            # 支社長席や集中ブース用のダミーkey
            st.session_state["seat_box"] = selected_group
        else:
            raw_seats = [s for s in all_seats if s.startswith(f"{selected_group}-")]
            island_seats = sorted(raw_seats, key=lambda x: int(x.split('-')[1]))
            seat_options = [f"{s}（{'👤 ' + df_logic[df_logic['座席番号']==s].iloc[0]['担当者'] if not df_logic[df_logic['座席番号']==s].empty else '✅ 空席'}）" for s in island_seats]
            st.sidebar.selectbox("📍 座席番号を選択", seat_options, key="seat_box")
        
        # 登録ボタンにコールバック関数を紐付け
        st.sidebar.button("✅ 登録・移動", use_container_width=True, type="primary", on_click=register_and_clear)

elif mode == "退席する" and current_members:
    target_name = st.sidebar.selectbox("👤 誰が退席しますか？", current_members)
    if st.sidebar.button("退席する", use_container_width=True):
        conn.update(worksheet="Sheet1", data=df_logic[df_logic["担当者"] != target_name])
        st.rerun()

# メイン表示実行
main_display(selected_group)

# QRコード
st.sidebar.markdown("---")
encoded_url = urllib.parse.quote(CURRENT_URL)
qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=100x100&data={encoded_url}"
st.sidebar.image(qr_url, caption="スマホで登録・確認", use_container_width=False)
