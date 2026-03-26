import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import os
import base64

st.set_page_config(layout="wide", page_title="オフィス座席マップ")

# スプレッドシート接続の設定
conn = st.connection("gsheets", type=GSheetsConnection)

# データの読み込み関数
def load_data():
    try:
        # スプレッドシートの「シート1」を読み込む（ttl=0でキャッシュ無効化）
        return conn.read(worksheet="Sheet1", ttl=0)
    except Exception as e:
        # エラーが出た場合は空のデータフレームを返す
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

# 画像と座標の設定
FILENAME = "事務所レイアウト01.png"

def generate_coords():
    coords = {}
    # 運用（60席）
    for col in range(6):
        for row in range(10):
            seat_id = f"運用-{col*10 + row + 1}"
            coords[seat_id] = {"top": 15 + row*6, "left": 18 + col*5}
    # 開発（72席）
    for col in range(6):
        for row in range(12):
            seat_id = f"開発-{col*12 + row + 1}"
            coords[seat_id] = {"top": 12 + row*5, "left": 55 + col*4}
    # ERP（44席）
    for col in range(4):
        for row in range(11):
            seat_id = f"ERP-{col*11 + row + 1}"
            coords[seat_id] = {"top": 15 + row*6, "left": 82 + col*4}
    return coords

seat_coords = generate_coords()

# 最新データの取得
df_now = load_data()

st.title("📍 事務所リアルタイム座席図 (保存版)")

# マップ表示部分
if os.path.exists(FILENAME):
    with open(FILENAME, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    
    map_html = f'<div style="position: relative; width:100%;"><img src="data:image/png;base64,{b64_string}" style="width:100%; opacity:0.6;">'
    
    for seat_id, pos in seat_coords.items():
        # スプレッドシートのデータから該当の座席を検索
        # データが空でないか確認してから比較
        if not df_now.empty and "座席番号" in df_now.columns:
            occ = df_now[df_now["座席番号"] == seat_id]
        else:
            occ = pd.DataFrame()
            
        bg_color = "#FF4B4B" if not occ.empty else "#28a745"
        label = occ.iloc[0]["担当者"] if not occ.empty else ""
        
        map_html += f'<div style="position: absolute; width:12px; height:12px; border-radius: 50%; top:{pos["top"]}%; left:{pos["left"]}%; background-color:{bg_color}; border:1px solid white;"></div>'
        if label:
            map_html += f'<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:9px; background:rgba(0,0,0,0.6); color:white; padding:1px 3px; border-radius:2px; transform:translate(-50%, -120%);">{label}</div>'
            
    map_html += '</div>'
    st.markdown(map_html, unsafe_allow_html=True)
else:
    st.error(f"画像「{FILENAME}」が見つかりません。")

# サイドバー：登録フォーム
st.sidebar.header("📝 在席登録")
u_name = st.sidebar.text_input("👤 名前")
s_id = st.sidebar.selectbox("📍 座席番号", list(seat_coords.keys()))

if st.sidebar.button("チェックイン", use_container_width=True, type="primary"):
    if u_name:
        try:
            # 1. 新しい1行だけのデータを作成
            new_data = pd.DataFrame([[datetime.now().strftime("%m/%d %H:%M"), u_name, s_id]], 
                                   columns=["更新日時", "担当者", "座席番号"])
            
            # 2. 「上書き」ではなく「追記（create）」を試みる
            # これにより既存データとの衝突を避けます
            conn.create(worksheet="Sheet1", data=new_data)
            
            st.success(f"{u_name}さん、登録しました！")
            # 3. 画面を更新して最新の状態を反映
            st.rerun()
        except Exception as e:
            st.error(f"書き込みエラーが発生しました。スプレッドシートの共有設定が『編集者』になっているか再確認してください。")
            # 詳細なエラーを画面に出して原因を特定しやすくします
            st.write(e)

if st.sidebar.button("退席（リセット）"):
    if u_name:
        current_df = load_data()
        if not current_df.empty and "担当者" in current_df.columns:
            updated_df = current_df[current_df["担当者"] != u_name]
            conn.update(worksheet="Sheet1", data=updated_df)
            st.rerun()
