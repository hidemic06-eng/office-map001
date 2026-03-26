import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone # timezone, timedeltaを追加
from streamlit_gsheets import GSheetsConnection
import base64
import os

# 1. ページ設定
st.set_page_config(layout="wide", page_title="オフィス座席マップ")

# --- 【修正】2分（120秒）ごとに自動リフレッシュ ---
st.fragment(run_every=120)(lambda: None)() 

# 日本時間(JST)の定義
JST = timezone(timedelta(hours=9))

# --- Google Sheets 接続設定 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# (中略: generate_coords 関数はそのまま)

def load_data():
    try:
        # ttl=0 でキャッシュを無効化し、常に最新を取得
        return conn.read(worksheet="Sheet1", ttl=0)
    except:
        return pd.DataFrame(columns=["更新日時", "担当者", "座席番号"])

df_now = load_data()

# --- メイン画面表示 ---
st.title("📍 事務所リアルタイム座席図")

# --- 【修正】最終更新の表示（タイトル下・マップの上に配置） ---
if not df_now.empty:
    latest = df_now.sort_values("更新日時", ascending=False).iloc[0]
    # 時刻部分だけを綺麗に表示
    l_time = str(latest['更新日時']).split(" ")[-1]
    st.caption(f"🕒 最終データ更新: {l_time} ({latest['担当者']}さん) ／ ※2分ごとに自動更新中")

# (以下、マップ描画ロジックと入退室ロジック)
# ※ 保存時の datetime.now() を datetime.now(JST) に書き換えるのをお忘れなく！
