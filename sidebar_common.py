# sidebar_common.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from utils import load_excel, ensure_cols

def load_dataset(state_key="__weapon_df__"):
    with st.sidebar:
        st.header("データの読み込み")
        uploaded = st.file_uploader("大剣.xlsx をアップロード（未指定なら同梱ファイルを読み込み）", type=["xlsx"], key="uploader1")
        use_default = st.checkbox("同梱の大剣.xlsxを使う", value=True, key="use_default1")

        if "dataset" not in st.session_state:
            st.session_state["dataset"] = None
        df = st.session_state.get("dataset", None)

        if uploaded is not None:
            try:
                df = pd.read_excel(uploaded, engine="openpyxl")
                st.session_state["dataset"] = df
                st.success("アップロードしたデータを読み込みました。")
            except Exception as e:
                st.error(f"アップロード読込エラー: {e}")
        elif use_default and df is None:
            try:
                df = load_excel("大剣.xlsx")
                st.session_state["dataset"] = df
                st.info("同梱の大剣.xlsxを読み込みました。")
            except Exception as e:
                st.warning(f"同梱ファイル読込エラー: {e}")

        if df is not None:
            miss = ensure_cols(df)
            if miss:
                st.warning(f"列が不足しています: {', '.join(miss)}")

    return st.session_state.get("dataset", None)
