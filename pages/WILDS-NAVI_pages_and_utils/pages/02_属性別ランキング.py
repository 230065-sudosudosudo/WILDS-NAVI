# 02_属性別ランキング.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from utils import normalize_attr, order_cols
from sidebar_common import load_dataset

st.set_page_config(page_title="属性別ランキング", layout="wide")
st.title("属性別ランキング")

df = load_dataset()
if df is None or df.empty:
    st.warning("有効なデータが読み込めていません。左サイドバーから読み込んでください。")
    st.stop()

left, right = st.columns(2)
with left:
    attr = st.selectbox("属性", ["火","水","雷","氷","龍","爆破","毒","睡眠","麻痺","無"], index=0)
with right:
    mode = st.radio("モード", ["強い順","弱い順"], horizontal=True)

work = df.copy()
if "属性" not in work.columns or "総攻撃力" not in work.columns:
    st.error("必要な列（属性, 総攻撃力）が不足しています。")
    st.stop()

work["__attr_norm__"] = work["属性"].astype(str).map(normalize_attr)
work = work[work["__attr_norm__"] == attr].copy()
work["総攻撃力"] = pd.to_numeric(work["総攻撃力"], errors="coerce")

c1, c2, c3 = st.columns(3)
with c1:
    rare_series = pd.to_numeric(work["レア度"], errors="coerce")
    mn = int(rare_series.min()) if rare_series.notna().any() else 0
    mx = int(rare_series.max()) if rare_series.notna().any() else 10
    rare_min, rare_max = st.slider("レア度範囲", min_value=mn, max_value=mx, value=(mn, mx))
with c2:
    topk = st.number_input("表示件数", min_value=5, max_value=100, value=20, step=5)
with c3:
    st.caption("※ 追加条件があればここに増やせます")

work = work[(pd.to_numeric(work["レア度"], errors="coerce") >= rare_min) &
            (pd.to_numeric(work["レア度"], errors="coerce") <= rare_max)]

if mode == "強い順":
    work = work.sort_values("総攻撃力", ascending=False).head(int(topk))
else:
    work = work.sort_values("総攻撃力", ascending=True).head(int(topk))

st.subheader(f"{attr}属性の{mode}ランキング")
st.dataframe(order_cols(work), use_container_width=True)
