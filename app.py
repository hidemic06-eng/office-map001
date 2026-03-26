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
FILENAME = "事務所レイアウト01.png"

# 座席座標の設定（運用・開発・ERPの各エリア）
def generate_coords():
    coords = {}
    for col in range(6):
        for row in range(10):
            seat_id = f"運用-{col*10 + row + 1}"
            coords[seat_id] = {"top": 15 + row*6, "left": 18 + col*5}
    for col in range(6):
        for row in range(12):
            seat_id = f"開発-{col*12 + row + 1}"
            coords[seat_id] = {"top": 12 + row*5, "left": 55 + col*4}
    for col in range(4):
        for row in range(11):
            seat_id = f"ERP-{col*11 + row + 1}"
            coords[seat_id] = {"top": 15 + row*6, "left": 82 + col*4}
    return coords

seat_coords = generate_coords()

# スプレッドシートから最新データを読み込み
def load_data():
    try:
        # worksheet名が "Sheet1" であることを前提としています
        return conn.read(worksheet="Sheet1", ttl="0")
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

df_now = load_data()

# --- メイン画面表示 ---
st.title("📍 事務所リアルタイム座席図")

# マップ表示ロジック
if os.path.exists(FILENAME):
    with open(FILENAME, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    
    map_html = f'''
    <div style="position: relative; width:100%;">
        <img src="data:image/png;base64,{b64_string}" style="width:100%; opacity:0.6;">
    '''
    
    for seat_id, pos in seat_coords.items():
        occ = df_now[df_now["座席番号"] == seat_id]
        bg_color = "#FF4B4B" if not occ.empty else "#28a745"
        label = occ.iloc[0]["担当者"] if not occ.empty else ""
        
        # 座席のドット
        map_html += f'<div style="position: absolute; width:12px; height:12px; border-radius: 50%; top:{pos["top"]}%; left:{pos["left"]}%; background-color:{bg_color}; border:1px solid white;"></div>'
        
        # 名前ラベル表示
        if label:
            map_html += f'<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:9px; background:rgba(0,0,0,0.6); color:white; padding:1px 3px; border-radius:2px; transform:translate(-50%, -120%); white-space:nowrap;">{label}</div>'
            
    map_html += '</div>'
    st.markdown(map_html, unsafe_allow_html=True)

# --- サイドバー：入退室管理 ---
st.sidebar.header("📝 入退室管理")

# 現在座っている人のリストを取得
current_members = df_now["担当者"].unique().tolist()

# 操作モードの選択
mode = st.sidebar.radio("操作を選択", ["新しく座る", "退席・移動する"])

if mode == "新しく座る":
    u_name = st.sidebar.text_input("👤 名前を入力")
    s_id = st.sidebar.selectbox("📍 座席番号を選択", list(seat_coords.keys()))
    
    if st.sidebar.button("チェックイン", use_container_width=True, type="primary"):
        if u_name:
            # 同名の既存データを削除（1人1箇所を維持）
            new_df = df_now[df_now["担当者"] != u_name].copy()
            # 新規行の追加
            new_row = pd.DataFrame([[datetime.now().strftime("%m/%d %H:%M"), u_name, s_id]], 
                                   columns=["更新日時", "担当者", "座席番号"])
            final_df = pd.concat([new_df, new_row], ignore_index=True)
            
            # スプレッドシート更新
            conn.update(worksheet="Sheet1", data=final_df)
            st.success(f"{u_name}さん、登録完了！")
            st.rerun()
        else:
            st.sidebar.error("名前を入力してください")

else: # 退席・移動する モード
    if not current_members:
        st.sidebar.info("現在、席に座っている人はいません。")
    else:
        # リストから名前を選択
        target_name = st.sidebar.selectbox("👤 誰が退席しますか？", current_members)
        
        if st.sidebar.button("退席（チェックアウト）", use_container_width=True):
            # 選択された名前を削除
            new_df = df_now[df_now["担当者"] != target_name]
            # スプレッドシート更新
            conn.update(worksheet="Sheet1", data=new_df)
            st.sidebar.warning(f"{target_name}さんを退席処理しました。")
            st.rerun()
