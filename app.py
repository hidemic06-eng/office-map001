import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import base64
import os

# ページ設定
st.set_page_config(layout="wide", page_title="オフィス座席マップ")

# --- Google Sheets 接続設定 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 設定 ---
FILENAME = "office_layout_with_islands.png"

# 座席座標の設定
def generate_coords():
    coords = {}
    top_gap = 1.6 
    
    islands_top = {"A": 18.2, "B": 23.5, "C": 28.9, "D": 34.8, "E": 40.2}
    for label, left_base in islands_top.items():
        for i in range(6):
            coords[f"{label}-{i+1}"] = {"top": 28.5 + i*6.6, "left": left_base - top_gap}
        for i in range(6):
            coords[f"{label}-{i+7}"] = {"top": 28.5 + i*6.6, "left": left_base + top_gap}

    islands_mid = {"F": 50.4, "G": 55.9, "H": 61.2, "I": 66.7, "J": 73.8, "K": 79.2}
    for label, left_base in islands_mid.items():
        for i in range(5):
            coords[f"{label}-{i+1}"] = {"top": 28.5 + i*6.6, "left": left_base - top_gap}
        for i in range(5):
            coords[f"{label}-{i+6}"] = {"top": 28.5 + i*6.6, "left": left_base + top_gap}

    islands_bottom_mapping = {"M": 50.4, "N": 55.9, "O": 61.2, "P": 66.7, "Q": 73.8, "R": 79.2}
    for label, left_base in islands_bottom_mapping.items():
        for i in range(4):
            coords[f"{label}-{i+1}"] = {"top": 66.5 + i*6.6, "left": left_base - top_gap}
        for i in range(4):
            coords[f"{label}-{i+5}"] = {"top": 66.5 + i*6.6, "left": left_base + top_gap}

    for i in range(5):
        coords[f"L-{i+1}"] = {"top": 28.5 + i*6.6, "left": 83.0}

    for i in range(4):
        coords[f"S-{i+1}"] = {"top": 66.5 + i*6.6, "left": 83.0}
    
    coords["支社長席"] = {"top": 23.5, "left": 12.0}
    for i in range(5):
        coords[f"集中ブース-{i+1}"] = {"top": 72.5, "left": 3.2 + i*2.1}

    return coords
    
seat_coords = generate_coords()

def load_data():
    try:
        return conn.read(worksheet="Sheet1", ttl="0")
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

df_now = load_data()

# --- サイドバー：検索機能 ---
st.sidebar.header("🔍 担当者検索")
search_query = st.sidebar.text_input("名前を入力して検索")

st.sidebar.markdown("---")

# --- メイン画面表示 ---
st.title("📍 事務所リアルタイム座席図")

# 点滅アニメーションのCSSを定義
st.markdown("""
    <style>
    @keyframes blink {
        0% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
        50% { opacity: 0.4; transform: translate(-50%, -50%) scale(1.6); }
        100% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
    }
    .blinking-dot {
        animation: blink 0.8s infinite;
        z-index: 15 !important;
        border: 2px solid #FFFFFF !important;
        box-shadow: 0 0 15px #FFFFFF;
    }
    </style>
    """, unsafe_allow_html=True)

if os.path.exists(FILENAME):
    with open(FILENAME, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    
    map_html = f'''
    <div style="position: relative; width:100%;">
        <img src="data:image/png;base64,{b64_string}" style="width:100%; opacity:0.8;">
    '''
    
    for seat_id, pos in seat_coords.items():
        occ = df_now[df_now["座席番号"] == seat_id]
        bg_color = "#FF4B4B" if not occ.empty else "#28a745"
        label = occ.iloc[0]["担当者"] if not occ.empty else ""
        
        # 検索条件の判定
        is_searching = False
        if search_query and label and (search_query in label):
            is_searching = True
            
        dot_class = "blinking-dot" if is_searching else ""
        
        # ドットの描画
        map_html += f'''<div class="{dot_class}" style="position: absolute; width:10px; height:10px; border-radius: 50%; 
                        top:{pos["top"]}%; left:{pos["left"]}%; background-color:{bg_color}; border:1px solid white; 
                        transform:translate(-50%, -50%); z-index:5;"></div>'''
        
        if label:
            # 検索対象の場合はラベルを目立たせる（黄色背景）
            label_bg = "rgba(255, 255, 0, 0.9)" if is_searching else "rgba(0,0,0,0.7)"
            label_color = "black" if is_searching else "white"
            
            map_html += f'''<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:9px; 
                            background:{label_bg}; color:{label_color}; padding:1px 3px; border-radius:2px; 
                            transform:translate(-50%, -120%); white-space:nowrap; z-index:10; font-weight:{"bold" if is_searching else "normal"};">
                            {label}</div>'''
            
    map_html += '</div>'
    st.markdown(map_html, unsafe_allow_html=True)

# --- サイドバー：入退室管理 ---
st.sidebar.header("📝 入退室管理")
current_members = df_now["担当者"].unique().tolist()
mode = st.sidebar.radio("操作を選択", ["新しく座る", "退席・移動する"])

if mode == "新しく座る":
    u_name = st.sidebar.text_input("👤 名前を入力")
    sorted_seats = sorted(list(seat_coords.keys()))
    s_id = st.sidebar.selectbox("📍 座席番号を選択", sorted_seats)
    
    if st.sidebar.button("チェックイン", use_container_width=True, type="primary"):
        if u_name:
            today_str = datetime.now().strftime("%m/%d")
            new_df = df_now[(df_now["更新日時"].str.startswith(today_str)) & (df_now["担当者"] != u_name)].copy()
            new_row = pd.DataFrame([[datetime.now().strftime("%m/%d %H:%M"), u_name, s_id]], columns=["更新日時", "担当者", "座席番号"])
            final_df = pd.concat([new_df, new_row], ignore_index=True)
            
            conn.update(worksheet="Sheet1", data=final_df)
            st.success(f"{u_name}さん、登録完了！")
            st.rerun()
        else:
            st.sidebar.error("名前を入力してください")

else:
    if not current_members:
        st.sidebar.info("現在、席に座っている人はいません。")
    else:
        target_name = st.sidebar.selectbox("👤 誰が退席しますか？", current_members)
        if st.sidebar.button("退席（チェックアウト）", use_container_width=True):
            new_df = df_now[df_now["担当者"] != target_name]
            conn.update(worksheet="Sheet1", data=new_df)
            st.sidebar.warning(f"{target_name}さんを退席処理しました。")
            st.rerun()
