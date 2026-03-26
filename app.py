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
# アップロードした新しい画像ファイル名に書き換えています
FILENAME = "office_layout_with_islands.png"

# 座席座標の設定（図面に基づいた全141席＋主要エリア）
# --- app.py の generate_coords()関数の中身を書き換え ---
def generate_coords():
    coords = {}
    
    # 【追加】デスクとドットの間隔を調整する設定 (gap)
    # ドットを少し「左」にずらしたい場合は、1.2を小さく（例: 1.0）
    # ドットを少し「右」にずらしたい場合は、1.2を大きく（例: 1.4）
    top_gap = 1.2 # デスク中心とドットの間隔 (%単位)
    
    # 1. A-E島 (12席、左右6席ずつ)
    # もし島全体を「右」にずらしたい場合は、leftの値を大きく（例: 19.5 -> 19.8）
    islands_top = {"A": 19.5, "B": 24.5, "C": 29.5, "D": 34.5, "E": 39.5}
    for label, left_base in islands_top.items():
        for i in range(6): # 左側
            coords[f"{label}-{i+1}"] = {"top": 28.0 + i*6.5, "left": left_base - top_gap}
        for i in range(6): # 右側
            coords[f"{label}-{i+7}"] = {"top": 28.0 + i*6.5, "left": left_base + top_gap}

    # 2. F-K島 (10席、左右5席ずつ)
    islands_mid = {"F": 51.5, "G": 56.5, "H": 61.5, "I": 66.5, "J": 73.5, "K": 78.5}
    for label, left_base in islands_mid.items():
        for i in range(5): # 左側
            coords[f"{label}-{i+1}"] = {"top": 28.0 + i*6.5, "left": left_base - top_gap}
        for i in range(5): # 右側
            coords[f"{label}-{i+6}"] = {"top": 28.0 + i*6.5, "left": left_base + top_gap}

    # 3. M-R島 (8席、左右4席ずつ)
    islands_bottom = {"M": 51.5, "N": 56.5, "O": 61.5, "P": 67.5, "Q": 73.5, "R": 80.5}
    for label, left_base in islands_bottom.items():
        for i in range(4): # 左側
            coords[f"{label}-{i+1}"] = {"top": 66.0 + i*6.5, "left": left_base - top_gap}
        for i in range(4): # 右側
            coords[f"{label}-{i+5}"] = {"top": 66.0 + i*6.5, "left": left_base + top_gap}
            
    # （L島、S島、その他は今のままでOK）
    # ...以下のコードは変更なし...
    # L島: 5席 (片側)
    for i in range(5):
        coords[f"L-{i+1}"] = {"top": 28.0 + i*6.5, "left": 83.5}

    # M-R島: 各8席 (左右4席ずつ)
    islands_bottom = {"M": 51.5, "N": 56.5, "O": 61.5, "P": 67.5, "Q": 73.5, "R": 80.5}
    for label, left_base in islands_bottom.items():
        for i in range(4): # 左側
            coords[f"{label}-{i+1}"] = {"top": 66.0 + i*6.5, "left": left_base - 1.2}
        for i in range(4): # 右側
            coords[f"{label}-{i+5}"] = {"top": 66.0 + i*6.5, "left": left_base + 1.2}

    # S島: 4席 (片側)
    for i in range(4):
        coords[f"S-{i+1}"] = {"top": 66.0 + i*6.5, "left": 85.5}

    # その他エリア
    coords["支社長席"] = {"top": 23.0, "left": 11.5}
    for i in range(5):
        coords[f"集中ブース-{i+1}"] = {"top": 72.0, "left": 3.0 + i*2.1}

    return coords

seat_coords = generate_coords()

# スプレッドシートから読み込み
def load_data():
    try:
        return conn.read(worksheet="Sheet1", ttl="0")
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

df_now = load_data()

# --- メイン画面表示 ---
st.title("📍 事務所リアルタイム座席図")

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
        
        map_html += f'<div style="position: absolute; width:10px; height:10px; border-radius: 50%; top:{pos["top"]}%; left:{pos["left"]}%; background-color:{bg_color}; border:1px solid white;"></div>'
        
        if label:
            map_html += f'<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:9px; background:rgba(0,0,0,0.7); color:white; padding:1px 3px; border-radius:2px; transform:translate(-50%, -120%); white-space:nowrap; z-index:10;">{label}</div>'
            
    map_html += '</div>'
    st.markdown(map_html, unsafe_allow_html=True)

# --- サイドバー：入退室管理 ---
st.sidebar.header("📝 入退室管理")
current_members = df_now["担当者"].unique().tolist()
mode = st.sidebar.radio("操作を選択", ["新しく座る", "退席・移動する"])

if mode == "新しく座る":
    u_name = st.sidebar.text_input("👤 名前を入力")
    # 席番号をA-1, A-2...の順に並び替えて表示
    sorted_seats = sorted(list(seat_coords.keys()))
    s_id = st.sidebar.selectbox("📍 座席番号を選択", sorted_seats)
    
    if st.sidebar.button("チェックイン", use_container_width=True, type="primary"):
        if u_name:
            today_str = datetime.now().strftime("%m/%d")
            # 昨日のデータクリア ＆ 重複削除
            new_df = df_now[(df_now["更新日時"].str.startswith(today_str)) & (df_now["担当者"] != u_name)].copy()
            new_row = pd.DataFrame([[datetime.now().strftime("%m/%d %H:%M"), u_name, s_id]], columns=["更新日時", "担当者", "座席番号"])
            final_df = pd.concat([new_df, new_row], ignore_index=True)
            
            conn.update(worksheet="Sheet1", data=final_df)
            st.success(f"{u_name}さん、登録完了！")
            st.rerun()
        else:
            st.sidebar.error("名前を入力してください")

else: # 退席モード
    if not current_members:
        st.sidebar.info("現在、席に座っている人はいません。")
    else:
        target_name = st.sidebar.selectbox("👤 誰が退席しますか？", current_members)
        if st.sidebar.button("退席（チェックアウト）", use_container_width=True):
            new_df = df_now[df_now["担当者"] != target_name]
            conn.update(worksheet="Sheet1", data=new_df)
            st.sidebar.warning(f"{target_name}さんを退席処理しました。")
            st.rerun()
