import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from streamlit_gsheets import GSheetsConnection
import base64
import os

# 1. ページ設定
st.set_page_config(layout="wide", page_title="オフィス座席マップ")

# --- 【更新設定】2分（120秒）ごとに自動リフレッシュ ---
st.fragment(run_every=120)(lambda: None) 

# 日本時間(JST)の定義
JST = timezone(timedelta(hours=9))

# 2. Google Sheets 接続設定
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 設定
FILENAME = "office_layout_with_islands.png"

# 座席座標の設定
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

df_now = load_data()

# --- サイドバー：検索・リスト ---
st.sidebar.header("🔍 担当者検索")
search_query = st.sidebar.text_input("名前を入力")

with st.sidebar.expander("👥 現在の着席者一覧", expanded=False):
    if not df_now.empty:
        df_list = df_now.copy()
        df_list["島"] = df_list["座席番号"].apply(lambda x: x.split('-')[0])
        islands = sorted(df_list["島"].unique())
        for island in islands:
            st.markdown(f"**🔹 {island}島・エリア**")
            members = df_list[df_list["島"] == island].sort_values("座席番号")
            cols = st.columns(2)
            for i, (_, row) in enumerate(members.iterrows()):
                with cols[i % 2]:
                    st.caption(f"🪑{row['座席番号']}\n{row['担当者']}")
            st.markdown("---")
    else:
        st.write("着席中のメンバーはいません")

st.sidebar.markdown("---")

# --- メイン画面表示 ---
st.title("📍 事務所リアルタイム座席図")

# 点滅アニメーションCSS
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
    </style>
    """, unsafe_allow_html=True)

# 入退室・移動管理のUI
st.sidebar.header("📝 入退室・移動")
current_members = df_now["担当者"].unique().tolist()
mode = st.sidebar.radio("操作を選択", ["新しく座る・移動する", "退席する"])

u_name = ""
s_id = None
selected_group = "未選択"

if mode == "新しく座る・移動する":
    u_name = st.sidebar.text_input("👤 名前を入力", placeholder="例：田中 太郎")
    all_seats = list(seat_coords.keys())
    island_list = sorted(list(set([s.split('-')[0] for s in all_seats if '-' in s])))
    special_list = sorted([s for s in all_seats if '-' not in s])
    selected_group = st.sidebar.selectbox("🏝️ 島・エリアを選択", ["未選択"] + island_list + special_list)
    
    if selected_group != "未選択":
        if selected_group in special_list:
            s_id = selected_group
        else:
            raw_seats = [s for s in all_seats if s.startswith(f"{selected_group}-")]
            island_seats = sorted(raw_seats, key=lambda x: int(x.split('-')[1]))
            seat_display_options = []
            for s in island_seats:
                occ = df_now[df_now["座席番号"] == s]
                label = f"{s}（👤 {occ.iloc[0]['担当者']}）" if not occ.empty else f"{s}（✅ 空席）"
                seat_display_options.append(label)
            selected_label = st.sidebar.selectbox("📍 座席番号を選択", seat_display_options)
            s_id = selected_label.split('（')[0]

# --- マップ描画ロジック ---
if os.path.exists(FILENAME):
    with open(FILENAME, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    
    map_html = f'''<div style="position: relative; width:100%;"><img src="data:image/png;base64,{b64_string}" style="width:100%; opacity:0.8;">'''
    
    for seat_id, pos in seat_coords.items():
        occ = df_now[df_now["座席番号"] == seat_id]
        label = occ.iloc[0]["担当者"] if not occ.empty else ""
        
        is_highlight = False
        if search_query and label and (search_query in label):
            is_highlight = True
        if selected_group != "未選択" and seat_id.startswith(f"{selected_group}-"):
            is_highlight = True
        if selected_group == seat_id:
            is_highlight = True

        dot_class = "blinking-dot" if is_highlight else ""
        dot_color = "#FFD700" if is_highlight else ("#FF4B4B" if label else "#28a745")
        dot_size = "1.2%" if is_highlight else "0.8%"
        z_index = "50" if is_highlight else "10"

        map_html += f'''<div class="{dot_class}" title="{seat_id}" style="position: absolute; width:{dot_size}; padding-top:{dot_size}; border-radius: 50%; 
                        top:{pos["top"]}%; left:{pos["left"]}%; background-color:{dot_color}; border:1px solid white; 
                        transform:translate(-50%, -50%); z-index:{z_index};"></div>'''
        
        display_text = label if label else seat_id
        label_bg = "rgba(255, 215, 0, 1.0)" if is_highlight else ("rgba(0,0,0,0.7)" if label else "rgba(200,200,200,0.5)")
        label_color = "black" if is_highlight else "white"
        font_weight = "bold" if (label or is_highlight) else "normal"
        font_size = "min(1.4vw, 9px)" if is_highlight else "min(1.1vw, 7px)"
        l_z_index = "60" if is_highlight else "15"

        map_html += f'''<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:{font_size}; 
                        background:{label_bg}; color:{label_color}; padding:1px 3px; border-radius:2px; 
                        transform:translate(-50%, -140%); white-space:nowrap; z-index:{l_z_index}; font-weight:{font_weight};">{display_text}</div>'''
                        
    map_html += '</div>'
    st.markdown(map_html, unsafe_allow_html=True)

# --- 【修正】マップの「下」に最終更新情報を表示 ---
if not df_now.empty:
    latest = df_now.sort_values("更新日時", ascending=False).iloc[0]
    l_time = str(latest['更新日時']).split(" ")[-1]
    st.info(f"🕒 最終更新: **{l_time}** ({latest['担当者']}さん) ／ ※2分ごとに自動更新されます")

# --- 登録・移動・退席の実行ロジック ---
if mode == "新しく座る・移動する" and u_name and s_id:
    now_jst = datetime.now(JST).strftime("%m/%d %H:%M")
    
    occupant = df_now[df_now["座席番号"] == s_id]
    existing_user = df_now[df_now["担当者"] == u_name]

    if not occupant.empty:
        current_occupant = occupant.iloc[0]["担当者"]
        if current_occupant != u_name:
            st.sidebar.error(f"❌ {s_id} は {current_occupant} さんが使用中です。")
        else:
            if st.sidebar.button("着席情報を更新する", use_container_width=True):
                new_df = df_now[df_now["担当者"] != u_name].copy()
                new_row = pd.DataFrame([[now_jst, u_name, s_id]], columns=["更新日時", "担当者", "座席番号"])
                conn.update(worksheet="Sheet1", data=pd.concat([new_df, new_row], ignore_index=True))
                st.rerun()
    elif not existing_user.empty:
        old_seat = existing_user.iloc[0]["座席番号"]
        if st.sidebar.button(f"🚀 {old_seat} から {s_id} へ移動", use_container_width=True, type="primary"):
            new_df = df_now[df_now["担当者"] != u_name].copy()
            new_row = pd.DataFrame([[now_jst, u_name, s_id]], columns=["更新日時", "担当者", "座席番号"])
            conn.update(worksheet="Sheet1", data=pd.concat([new_df, new_row], ignore_index=True))
            st.rerun()
    else:
        if st.sidebar.button("✅ チェックイン", use_container_width=True, type="primary"):
            new_row = pd.DataFrame([[now_jst, u_name, s_id]], columns=["更新日時", "担当者", "座席番号"])
            conn.update(worksheet="Sheet1", data=pd.concat([df_now, new_row], ignore_index=True))
            st.rerun()

elif mode == "退席する":
    if current_members:
        target_name = st.sidebar.selectbox("👤 誰が退席しますか？", current_members)
        if st.sidebar.button("退席", use_container_width=True):
            conn.update(worksheet="Sheet1", data=df_now[df_now["担当者"] != target_name])
            st.rerun()
