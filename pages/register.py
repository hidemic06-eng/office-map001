import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from streamlit_gsheets import GSheetsConnection

# 1. ページ設定（スマホで見やすいようスリムに）
st.set_page_config(page_title="座席クイック登録", layout="centered")

JST = timezone(timedelta(hours=9))
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        return conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

# 2. URLから座席番号を取得 (?seat=A-1 のような形式)
query_params = st.query_params
default_seat = query_params.get("seat", "未選択")

st.title("📝 座席チェックイン")

# 3. ユーザー名の保存機能（一度入力したら次回から自動入力）
if "saved_name" not in st.session_state:
    st.session_state["saved_name"] = ""

u_name = st.text_input("👤 お名前", value=st.session_state["saved_name"], placeholder="例：田中 太郎")

# 4. 座席の表示（QRから読み取っていれば自動入力される）
st.info(f"📍 選択中の座席: **{default_seat}**")

if default_seat == "未選択":
    st.warning("QRコードを読み直すか、手動で座席を指定してください。")

# 5. 登録ボタン（デカデカと押しやすく）
if st.button("✅ この席に座る", use_container_width=True, type="primary"):
    if u_name and default_seat != "未選択":
        # 名前をセッションに保存（次回入力の手間を省く）
        st.session_state["saved_name"] = u_name
        
        df_logic = load_data()
        today_str = datetime.now(JST).strftime("%m/%d")
        
        # 既存データの整理（本人の旧データ削除）
        new_df = df_logic[
            (df_logic["更新日時"].str.startswith(today_str)) & 
            (df_logic["担当者"] != u_name)
        ].copy()
        
        # 新規登録
        new_row = pd.DataFrame([[
            datetime.now(JST).strftime("%m/%d %H:%M"), 
            u_name, 
            default_seat
        ]], columns=["更新日時", "担当者", "座席番号"])
        
        conn.update(worksheet="Sheet1", data=pd.concat([new_df, new_row], ignore_index=True))
        
        st.success(f"{default_seat} に登録しました！ブラウザを閉じてOKです。")
        st.balloons()
    else:
        st.error("名前を入力してください。")
