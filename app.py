import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64
from git import Repo

st.set_page_config(layout="wide", page_title="オフィス座席マップ")

# --- 設定 ---
DB_FILE = "seat_master.csv"
FILENAME = "事務所レイアウト01.png"
# GitHubへ保存するための設定（自分の情報を入れてください）
GITHUB_TOKEN = st.secrets["github_token"]
REPO_URL = f"https://{GITHUB_TOKEN}@github.com/hidemic06-eng/オフィスマップ001.git"

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

# 座標設定はそのまま（省略せず貼り付けてください）
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
df_now = load_data()

# --- メイン画面 ---
st.title("📍 事務所リアルタイム座席図")

# マップ表示（これまでのコードと同じ）
if os.path.exists(FILENAME):
    with open(FILENAME, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    map_html = f'<div style="position: relative; width:100%;"><img src="data:image/png;base64,{b64_string}" style="width:100%; opacity:0.6;">'
    for seat_id, pos in seat_coords.items():
        occ = df_now[df_now["座席番号"] == seat_id]
        bg_color = "#FF4B4B" if not occ.empty else "#28a745"
        label = occ.iloc[0]["担当者"] if not occ.empty else ""
        map_html += f'<div style="position: absolute; width:12px; height:12px; border-radius: 50%; top:{pos["top"]}%; left:{pos["left"]}%; background-color:{bg_color}; border:1px solid white;"></div>'
        if label:
            map_html += f'<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:9px; background:rgba(0,0,0,0.6); color:white; padding:1px 3px; border-radius:2px; transform:translate(-50%, -120%);">{label}</div>'
    map_html += '</div>'
    st.markdown(map_html, unsafe_allow_html=True)

# --- 登録処理 ---
st.sidebar.header("📝 在席登録")
u_name = st.sidebar.text_input("👤 名前")
s_id = st.sidebar.selectbox("📍 座席番号", list(seat_coords.keys()))

if st.sidebar.button("チェックイン", use_container_width=True, type="primary"):
    if u_name:
        df = load_data()
        df = df[df["担当者"] != u_name]
        new_row = pd.DataFrame([[datetime.now().strftime("%H:%M"), u_name, s_id]], columns=["更新日時", "担当者", "座席番号"])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
        
        # --- GitHubに強制保存（ここがポイント！） ---
        try:
            repo = Repo(".")
            repo.git.add(DB_FILE)
            repo.index.commit("座席更新: " + u_name)
            origin = repo.remote(name='origin')
            origin.push()
            st.success("GitHubへ保存しました！")
            st.rerun()
        except:
            st.warning("一時保存しました（GitHub同期なし）")
