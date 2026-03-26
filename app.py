import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import base64
import os
import qrcode
from io import BytesIO

# 1. ページ設定
st.set_page_config(layout="wide", page_title="オフィス座席マップ", initial_sidebar_state="expanded")

# 自動リフレッシュ（30秒ごと）
st.fragment(run_every=30)(lambda: None)() 

# 2. Google Sheets 接続
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 定数設定
FILENAME = "office_layout_with_islands.png"
APP_URL = "https://office-map001-d7unukgvvdas4njkzblvyv.streamlit.app/"

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

# 5. データ読み込み
def load_data():
    try:
        return conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

df_now = load_data()

# --- メイン画面：CSS ---
st.markdown("""
    <style>
    @keyframes blink {
        0% { opacity: 1; transform: translate(-50%, -50%) scale(1.1); }
        50% { opacity: 0.5; transform: translate(-50%, -50%) scale(1.4); }
        100% { opacity: 1; transform: translate(-50%, -50%) scale(1.1); }
    }
    .blinking-dot {
        animation: blink 0.8s infinite;
        z-index: 30 !important;
        border: 2px solid #FFD700 !important;
        box-shadow: 0 0 15px #FFD700;
    }
    .main .block-container { padding-top: 1rem; }
    /* 最終更新表示のスタイル */
    .last-update-box {
        position: absolute;
        top: 0px;
        right: 10px;
        background-color: #f0f2f6;
        padding: 5px 15px;
        border-radius: 10px;
        border: 1px solid #ddd;
        text-align: right;
        z-index: 100;
    }
    </style>
    """, unsafe_allow_html=True)

# タイトルと最終更新のレイアウト
col_title, col_update = st.columns([2, 1])
with col_title:
    st.title("📍 事務所座席図")

with col_update:
    if not df_now.empty:
        # 最新の更新時間を取得
        latest_row = df_now.sort_values("更新日時", ascending=False).iloc[0]
        l_time = latest_row["更新日時"].split(" ")[1] if " " in str(latest_row["更新日時"]) else str(latest_row["更新日時"])
        l_user = latest_row["担当者"]
        st.markdown(f"""
            <div class="last-update-box">
                <span style="font-size: 0.8em; color: #666;">最終データ更新</span><br>
                <span style="font-size: 1.5em; font-weight: bold; color: #FF4B4B;">{l_time}</span><br>
                <span style="font-size: 0.7em; color: #888;">(by {l_user}さん)</span>
            </div>
        """, unsafe_allow_html=True)

# --- サイドバー：検索・操作 ---
st.sidebar.header("🔍 担当者検索")
search_query = st.sidebar.text_input("名前を入力")

with st.sidebar.expander("👥 現在の着席者一覧"):
    if not df_now.empty:
        df_list = df_now.copy()
        df_list["島"] = df_list["座席番号"].apply(lambda x: x.split('-')[0])
        for island in sorted(df_list["島"].unique()):
            st.markdown(f"**🔹 {island}島**")
            members = df_list[df_list["島"] == island].sort_values("座席番号")
            for _, row in members.iterrows():
                st.caption(f"🪑{row['座席番号']} : {row['担当者']}")
    else:
        st.write("着席者なし")

st.sidebar.markdown("---")
st.sidebar.header("📝 入退室・移動")
current_members = df_now["担当者"].unique().tolist()
mode = st.sidebar.radio("操作", ["新しく座る・移動する", "退席する"])

u_name = ""
s_id = None
selected_group = "未選択"

if mode == "新しく座る・移動する":
    u_name = st.sidebar.text_input("👤 名前", placeholder="例：田中 太郎")
    all_seats = list(seat_coords.keys())
    island_list = sorted(list(set([s.split('-')[0] for s in all_seats if '-' in s])))
    special_list = sorted([s for s in all_seats if '-' not in s])
    selected_group = st.sidebar.selectbox("🏝️ エリア", ["未選択"] + island_list + special_list)
    
    if selected_group != "未選択":
        if selected_group in special_list:
            s_id = selected_group
        else:
            raw_seats = [s for s in all_seats if s.startswith(f"{selected_group}-")]
            island_seats = sorted(raw_seats, key=lambda x: int(x.split('-')[1]) if x.split('-')[1].isdigit() else 0)
            seat_options = [f"{s}（{'👤 ' + df_now[df_now['座席番号']==s].iloc[0]['担当者'] if not df_now[df_now['座席番号']==s].empty else '✅ 空席'}）" for s in island_seats]
            selected_label = st.sidebar.selectbox("📍 座席", seat_options)
            s_id = selected_label.split('（')[0]

# --- マップ描画 ---
if os.path.exists(FILENAME):
    with open(FILENAME, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    map_html = f'''<div style="position: relative; width:100%;"><img src="data:image/png;base64,{b64_string}" style="width:100%; opacity:0.8;">'''
    
    for seat_id, pos in seat_coords.items():
        occ = df_now[df_now["座席番号"] == seat_id]
        label = occ.iloc[0]["担当者"] if not occ.empty else ""
        
        is_highlight = (search_query and label and search_query in label) or (selected_group != "未選択" and seat_id.startswith(f"{selected_group}-")) or (selected_group == seat_id)

        dot_class = "blinking-dot" if is_highlight else ""
        dot_color = "#FFD700" if is_highlight else ("#FF4B4B" if label else "#28a745")
        dot_size = "12px" if is_highlight else "8px"
        
        map_html += f'''<div class="{dot_class}" title="{seat_id}" style="position: absolute; width:{dot_size}; height:{dot_size}; border-radius: 50%; top:{pos["top"]}%; left:{pos["left"]}%; background-color:{dot_color}; border:1px solid white; transform:translate(-50%, -50%); z-index:20;"></div>'''
        
        display_text = label if label else seat_id
        label_bg = "rgba(255, 215, 0, 1.0)" if is_highlight else ("rgba(0,0,0,0.7)" if label else "rgba(200,200,200,0.5)")
        label_color = "black" if is_highlight else "white"
        
        map_html += f'''<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:{"10px" if is_highlight else "8px"}; background:{label_bg}; color:{label_color}; padding:1px 3px; border-radius:2px; transform:translate(-50%, -130%); white-space:nowrap; z-index:15; font-weight:{"bold" if label else "normal"};">{display_text}</div>'''
    map_html += '</div>'
    st.markdown(map_html, unsafe_allow_html=True)

# --- 更新ロジック ---
if mode == "新しく座る・移動する" and u_name and s_id:
    if st.sidebar.button("チェックイン / 移動", use_container_width=True, type="primary"):
        new_df = df_now[df_now["担当者"] != u_name].copy()
        new_row = pd.DataFrame([[datetime.now().strftime("%m/%d %H:%M"), u_name, s_id]], columns=["更新日時", "担当者", "座席番号"])
        conn.update(worksheet="Sheet1", data=pd.concat([new_df, new_row], ignore_index=True))
        st.rerun()
elif mode == "退席する" and current_members:
    target = st.sidebar.selectbox("👤 誰が退席しますか？", current_members)
    if st.sidebar.button("退席", use_container_width=True):
        conn.update(worksheet="Sheet1", data=df_now[df_now["担当者"] != target])
        st.rerun()

# QRコード
st.sidebar.markdown("---")
st.sidebar.subheader("📱 スマホで共有")
qr_img = BytesIO()
qrcode.make(APP_URL).save(qr_img, format="PNG")
st.sidebar.image(qr_img.getvalue(), width=150)
