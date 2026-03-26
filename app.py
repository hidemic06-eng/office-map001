import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import base64
import os

st.set_page_config(layout="wide", page_title="オフィス座席マップ")

# --- Google Sheets 接続設定 ---
# Secretsの [connections.gsheets] を使って自動接続
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 設定 ---
FILENAME = "事務所レイアウト01.png"

# 座席座標の設定
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

# スプレッドシートから読み込み
def load_data():
    try:
        # Sheet1 からデータを読み込む
        return conn.read(worksheet="Sheet1", ttl="0")
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

df_now = load_data()

# --- メイン画面 ---
st.title("📍 事務所リアルタイム座席図")

# マップ表示
if os.path.exists(FILENAME):
    with open(FILENAME, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    
    map_html = f'''
    <div style="position: relative; width:100%;">
        <img src="data:image/png;base64,{b64_string}" style="width:100%; opacity:0.6;">
    '''
    
    for seat_id, pos in seat_coords.items():
        # 該当座席に誰かいるか確認
        occ = df_now[df_now["座席番号"] == seat_id]
        bg_color = "#FF4B4B" if not occ.empty else "#28a745"
        label = occ.iloc[0]["担当者"] if not occ.empty else ""
        
        # 座席の点
        map_html += f'<div style="position: absolute; width:12px; height:12px; border-radius: 50%; top:{pos["top"]}%; left:{pos["left"]}%; background-color:{bg_color}; border:1px solid white;"></div>'
        
        # 名前ラベル
        if label:
            map_html += f'<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:9px; background:rgba(0,0,0,0.6); color:white; padding:1px 3px; border-radius:2px; transform:translate(-50%, -120%); white-space:nowrap;">{label}</div>'
            
    map_html += '</div>'
    st.markdown(map_html, unsafe_allow_html=True)
    
# --- 登録処理 ---
st.sidebar.header("📝 在席登録")
u_name = st.sidebar.text_input("👤 名前")
s_id = st.sidebar.selectbox("📍 座席番号", list(seat_coords.keys()))

if st.sidebar.button("チェックイン", use_container_width=True, type="primary"):
    if u_name:
        # 既存の自分のデータを消す（1人1箇所）
        new_df = df_now[df_now["担当者"] != u_name].copy()
        
        # 新しい行を作成
        new_row = pd.DataFrame([[datetime.now().strftime("%m/%d %H:%M"), u_name, s_id]], 
                               columns=["更新日時", "担当者", "座席番号"])
        
        # データを結合
        final_df = pd.concat([new_df, new_row], ignore_index=True)
        
        # スプレッドシートを更新
        try:
            conn.update(worksheet="Sheet1", data=final_df)
            st.success(f"{u_name}さん、登録完了しました！")
            st.rerun()
        except Exception as e:
            st.error("書き込みに失敗しました。スプレッドシートの共有設定を確認してください。")
            st.write(e)

# --- 退席処理（既存のチェックインボタンの下に追加） ---
if st.sidebar.button("退席（チェックアウト）", use_container_width=True):
    if u_name:
        # 自分の名前以外のデータだけを残す（＝自分を削除する）
        new_df = df_now[df_now["担当者"] != u_name]
        
        try:
            # スプレッドシートを上書き更新
            conn.update(worksheet="Sheet1", data=new_df)
            st.sidebar.warning(f"{u_name}さん、退席処理をしました。")
            st.rerun()
        except Exception as e:
            st.error("退席処理に失敗しました。")
            st.write(e)
    else:
        st.sidebar.error("名前を入力してください。")
