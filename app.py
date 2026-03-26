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
    for i in range(5): coords[f"L-{i+1}"] = {"top": 28.5 + i*6.6, "left": 83.0}
    for i in range(4): coords[f"S-{i+1}"] = {"top": 66.5 + i*6.6, "left": 83.0}
    coords["支社長席"] = {"top": 23.5, "left": 12.0}
    for i in range(5): coords[f"集中ブース-{i+1}"] = {"top": 72.5, "left": 3.2 + i*2.1}
    return coords

seat_coords = generate_coords()

def load_data():
    try:
        return conn.read(worksheet="Sheet1", ttl="0")
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

df_now = load_data()

# --- メイン画面表示 ---
# カスタムCSSを追加して背景と枠をかっこよくする
st.markdown("""
    <style>
    /* 全体の背景を深い紺色のグラデーションに */
    .stApp {
        background: radial-gradient(circle at center, #1e2227 0%, #111418 100%);
    }
    
    /* 座席図の周りに光る枠線（サイバー風）を追加 */
    .main-container {
        border: 1px solid rgba(0, 255, 255, 0.1);
        border-radius: 12px;
        padding: 10px;
        background: rgba(255, 255, 255, 0.02);
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
    }
    
    /* タイトルの文字を少し光らせる */
    .stTitle {
        color: #ffffff;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
        font-family: 'Helvetica Neue', sans-serif;
        letter-spacing: 1.5px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📍 事務所リアルタイム座席図")

# 以前の「ばっちり」なコードをそのまま流用
if os.path.exists(FILENAME):
    with open(FILENAME, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    
    # 枠で囲むために <div> を一つ追加
    html_content = f'<div class="main-container">'
    html_content += f'<div style="position: relative; width: 100%;">'
    html_content += f'<img src="data:image/png;base64,{b64_string}" style="width: 100%; opacity: 0.8; display: block; border-radius: 4px;">'
    
    for seat_id, pos in seat_coords.items():
        occ = df_now[df_now["座席番号"] == seat_id]
        bg_color = "#FF4B4B" if not occ.empty else "#28a745"
        label = occ.iloc[0]["担当者"] if not occ.empty else ""
        
        # 元のシンプルなドットとラベル
        html_content += f'<div style="position: absolute; width:10px; height:10px; border-radius: 50%; top:{pos["top"]}%; left:{pos["left"]}%; background-color:{bg_color}; border:1px solid white; transform: translate(-50%, -50%); z-index:5;"></div>'
        
        if label:
            html_content += f'<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:9px; background:rgba(0,0,0,0.8); color:white; padding:1px 4px; border-radius:2px; transform:translate(-50%, -130%); white-space:nowrap; z-index:10; border: 0.5px solid #444;">{label}</div>'
            
    html_content += '</div></div>' # 閉じタグを忘れずに
    st.markdown(html_content, unsafe_allow_html=True)


st.title("📍 事務所リアルタイム座席図")

if os.path.exists(FILENAME):
    with open(FILENAME, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    
    # HTMLの組み立て
    html_content = f'<div style="position: relative; width: 100%; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">'
    html_content += f'<img src="data:image/png;base64,{b64_string}" style="width: 100%; opacity: 0.85; display: block;">'
    
    for seat_id, pos in seat_coords.items():
        occ = df_now[df_now["座席番号"] == seat_id]
        if not occ.empty:
            color = "#FF4B4B" 
            glow = "rgba(255, 75, 75, 0.6)"
            label = occ.iloc[0]["担当者"]
        else:
            color = "#00D166" 
            glow = "rgba(0, 209, 102, 0.4)"
            label = ""
        
        # ドットのHTML
        html_content += f'<div style="position: absolute; width: 12px; height: 12px; border-radius: 50%; top: {pos["top"]}%; left: {pos["left"]}%; background-color: {color}; border: 2px solid white; box-shadow: 0 0 8px {glow}; z-index: 5; transform: translate(-50%, -50%);"></div>'
        
        # 名前のHTML
        if label:
            html_content += f'<div style="position: absolute; top: {pos["top"]}%; left: {pos["left"]}%; font-size: 10px; font-weight: bold; background: rgba(33, 33, 33, 0.9); color: white; padding: 2px 8px; border-radius: 4px; transform: translate(-50%, -150%); white-space: nowrap; z-index: 10; border: 1px solid rgba(255,255,255,0.2); box-shadow: 0 2px 5px rgba(0,0,0,0.5);">{label}</div>'
            
    html_content += '</div>'
    st.markdown(html_content, unsafe_allow_html=True)

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
