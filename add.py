# app.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from search_core import search_weapons, load_weapon_df

st.set_page_config(
    page_title="WILDS-NAVI 大剣版（モンスター弱点対応）",
    layout="wide",
)

st.title("武器データ検索アプリ（大剣×モンスター弱点）")

st.markdown(
    """
質問を日本語で入力すると、**大剣.xlsx** と **モンスター一覧.xlsx** を使って
おすすめの大剣を絞り込みます。

例）  
- `チャタカブラに一番効く武器`  
- `ケマトリスに有効な武器`  
- `雷属性で強い武器`  
"""
)

# ランク選択
rank_choice = st.radio("今プレイしているランク", ["下位", "上位"], horizontal=True)

query = st.text_area(
    "質問を入力",
    height=80,
    placeholder="例: チャタカブラに一番効く武器 / ケマトリスに有効な武器 / 雷属性で強い武器",
)

if st.button("検索", type="primary"):
    with st.spinner("検索中..."):
        df, message = search_weapons(query, rank_choice)

    if message:
        st.info(message)

    if df is None or df.empty:
        st.warning("該当する武器が見つかりませんでした。")
    else:
        # 見やすい順に並べ替え（列があるものだけ）
        preferred_cols = [
            "武器", "基礎攻撃力", "会心率", "スロット数", "スキル",
            "総攻撃力", "総攻撃力(物理)", "属性", "属性値", "切れ味", "レア度", "下位",
        ]
        cols = [c for c in preferred_cols if c in df.columns] + [
            c for c in df.columns if c not in preferred_cols
        ]
        st.dataframe(df[cols], use_container_width=True)

# デバッグ用：データ確認
with st.expander("大剣.xlsx の中身を確認する（開発者向け）"):
    try:
        base_df = load_weapon_df()
        st.dataframe(base_df.head(), use_container_width=True)
    except Exception as e:
        st.error(f"読み込みエラー: {e}")
