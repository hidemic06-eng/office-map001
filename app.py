# 1. 必要なツールをすべてインストール
!pip install streamlit -q
!pip install pyngrok -q
!pip install pandas -q

import os
from pyngrok import ngrok

# 2. アプリの本体（app.py）を再作成
with open('app.py', 'w', encoding='utf-8') as f:
    f.write('''
import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64

st.set_page_config(layout="wide", page_title="オフィス座席マップ")

FILENAME = "事務所レイアウト01.png"
DB_FILE = "seat_master.csv"

def load_data():
    try:
        return pd.read_csv(DB_FILE)
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

# 座標生成（運用、開発、ERP）
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

st.title("📍 事務所リアルタイム座席図")

# マップ表示
if os.path.exists(FILENAME):
    with open(FILENAME, "rb") as img_file:
        b64_string = base64.b64encode(img_file.read()).decode()
    
    map_html = f'<div style="position: relative; width:100%;"><img src="data:image/jpg;base64,{b64_string}" style="width:100%; opacity:0.6;">'
    for seat_id, pos in seat_coords.items():
        occ = df_now[df_now["座席番号"] == seat_id]
        bg_color = "#FF4B4B" if not occ.empty else "#28a745"
        label = occ.iloc[0]["担当者"] if not occ.empty else ""
        map_html += f'<div style="position: absolute; width:12px; height:12px; border-radius: 50%; top:{pos["top"]}%; left:{pos["left"]}%; background-color:{bg_color}; border:1px solid white;"></div>'
        if label:
            map_html += f'<div style="position: absolute; top:{pos["top"]}%; left:{pos["left"]}%; font-size:9px; background:rgba(0,0,0,0.6); color:white; padding:1px 3px; border-radius:2px; transform:translate(-50%, -120%);">{label}</div>'
    map_html += '</div>'
    st.markdown(map_html, unsafe_allow_html=True)

# 登録フォーム
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
        st.rerun()

if st.sidebar.button("退席（リセット）"):
    df = load_data()
    df = df[df["担当者"] != u_name]
    df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
    st.rerun()
''')

# 3. ngrokを再起動してURLを発行
NGROK_AUTH_TOKEN = "3BKGzu0vg7fbEd4682MuveKd6Jq_34cFxhF9hM5Jhjnhr2RmS"
ngrok.set_auth_token(NGROK_AUTH_TOKEN)
ngrok.kill()
public_url = ngrok.connect(8501).public_url

print(f"▼ 新しいURLはこちらです：\n{public_url}")

# 4. Streamlitをバックグラウンドで起動
!streamlit run app.py &>/dev/null &
