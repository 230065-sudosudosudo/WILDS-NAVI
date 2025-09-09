# 03_比較ツール.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sidebar_common import load_dataset
from utils import order_cols

st.set_page_config(page_title="比較ツール", layout="wide")
st.title("武器の比較ツール")

df = load_dataset()
if df is None or df.empty:
    st.warning("有効なデータが読み込めていません。")
    st.stop()

names = sorted(list(df["武器"].astype(str).unique())) if "武器" in df.columns else []
selected = st.multiselect("比較する武器（最大5つ）", names, max_selections=5)

cols_numeric = ["基礎攻撃力","総攻撃力(物理)","総攻撃力","属性値","会心率"]
cols_numeric = [c for c in cols_numeric if c in df.columns]

if selected:
    view = df[df["武器"].astype(str).isin(selected)].copy()
    st.dataframe(order_cols(view), use_container_width=True)

    # レーダーチャート用正規化
    if len(cols_numeric) >= 3:
        data = view[["武器"] + cols_numeric].copy()
        for c in cols_numeric:
            vals = pd.to_numeric(data[c], errors="coerce")
            mn, mx = vals.min(), vals.max()
            if pd.isna(mn) or pd.isna(mx) or mx == mn:
                norm = np.zeros_like(vals, dtype=float)
            else:
                norm = (vals - mn) / (mx - mn)
            data[c] = norm.fillna(0)

        categories = cols_numeric
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False)

        for _, row in data.iterrows():
            stats = row[cols_numeric].values.astype(float)
            stats = np.concatenate((stats, [stats[0]]))
            angs = np.concatenate((angles, [angles[0]]))

            fig = plt.figure()
            ax = fig.add_subplot(111, polar=True)
            ax.plot(angs, stats)
            ax.fill(angs, stats, alpha=0.1)
            ax.set_thetagrids(angles * 180/np.pi, categories)
            ax.set_title(f"レーダーチャート: {row['武器']}")
            st.pyplot(fig)
