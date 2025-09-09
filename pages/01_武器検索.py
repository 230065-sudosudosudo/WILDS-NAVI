# 01_武器検索.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from utils import parse_and_filter, order_cols
from sidebar_common import load_dataset

st.set_page_config(page_title="武器検索", layout="wide")
st.title("武器検索")

df = load_dataset()
query = st.text_area("質問を入力", value="", height=100, placeholder="例: 火属性で強い武器 / 上位で攻撃が高い / レア 度 8 会心 率 30 以上")

if st.button("実行", type="primary"):
    if df is None or df.empty:
        st.warning("有効なデータが読み込めていません。")
    else:
        try:
            result = parse_and_filter(df, query)
            if result is None or result.empty:
                st.info("該当する条件が見つかりませんでした。")
            else:
                st.dataframe(order_cols(result), use_container_width=True)
        except Exception as e:
            st.exception(e)
