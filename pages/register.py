import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from streamlit_gsheets import GSheetsConnection

# ページ設定（地図なし・軽量モード）
st.set_page_config(
    page_title="座席チェックイン",
    page_icon="📲",  # 登録画面なのでスマホっぽい絵文字にしてみました
)

JST = timezone(timedelta(hours=9))
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        return conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

# URLから座席番号を取得
query_params = st.query_params
default_seat = query_params.get("seat", "未選択")

# ★ 地図アプリと見分けるための大きなタイトル
st.title("📲 座席チェックイン (QR専用)")

if "saved_name" not in st.session_state:
    st.session_state["saved_name"] = ""

u_name = st.text_input("👤 お名前", value=st.session_state["saved_name"])
st.info(f"📍 選択中の座席: {default_seat}")

if st.button("✅ 登録する", use_container_width=True, type="primary"):
    if u_name and default_seat != "未選択":
        st.session_state["saved_name"] = u_name
        df_logic = load_data()
        today_str = datetime.now(JST).strftime("%m/%d")
        
        new_df = df_logic[(df_logic["更新日時"].str.startswith(today_str)) & (df_logic["担当者"] != u_name)].copy()
        new_row = pd.DataFrame([[datetime.now(JST).strftime("%m/%d %H:%M"), u_name, default_seat]], columns=["更新日時", "担当者", "座席番号"])
        
        conn.update(worksheet="Sheet1", data=pd.concat([new_df, new_row], ignore_index=True))
        st.success(f"{default_seat} に登録完了！")
        st.balloons()
