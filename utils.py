# utils.py
# -*- coding: utf-8 -*-
import pandas as pd
from janome.tokenizer import Tokenizer

_ATTR_CANON = ["火", "水", "雷", "氷", "龍", "爆破", "毒", "睡眠", "麻痺", "無"]
_ATTR_ALIASES = {
    "火属性": "火", "火": "火",
    "水属性": "水", "水": "水",
    "雷属性": "雷", "雷": "雷", "電": "雷", "電撃": "雷", "電気": "雷",
    "氷属性": "氷", "氷": "氷",
    "龍属性": "龍", "竜属性": "龍", "龍": "龍", "竜": "龍", "ドラゴン": "龍",
    "爆破属性": "爆破", "爆破": "爆破",
    "毒属性": "毒", "毒": "毒",
    "睡眠属性": "睡眠", "睡眠": "睡眠",
    "麻痺属性": "麻痺", "麻痺": "麻痺",
    "無属性": "無", "無": "無", "無撃": "無",
}

PREFERRED_COLS = [
    "武器","基礎攻撃力","会心率","スロット数","スキル",
    "総攻撃力","総攻撃力(物理)","属性","属性値","切れ味","レア度"
]

NEEDED_COLS = ["武器","会心率","属性","総攻撃力","総攻撃力(物理)","レア度"]

def normalize_attr(s):
    if s is None:
        return None
    s = str(s).strip()
    return _ATTR_ALIASES.get(s, s)

def tokenize(text):
    t = Tokenizer()
    return [tok.surface for tok in t.tokenize(text or "")]

def detect_attrs(text, tokens):
    found = set()
    t = text or ""
    for key, canon in _ATTR_ALIASES.items():
        if key and key in t:
            found.add(canon)
    for i, tok in enumerate(tokens):
        tok = tok.strip()
        if not tok:
            continue
        if tok in _ATTR_ALIASES:
            found.add(_ATTR_ALIASES[tok])
        if tok in _ATTR_CANON:
            if i + 1 < len(tokens) and tokens[i + 1] == "属性":
                found.add(tok)
    return found

def ensure_cols(df: pd.DataFrame):
    missing = [c for c in NEEDED_COLS if c not in df.columns]
    return missing

def load_excel(path_or_buffer):
    return pd.read_excel(path_or_buffer, engine="openpyxl")

def parse_and_filter(df: pd.DataFrame, text: str) -> pd.DataFrame:
    tokens = tokenize(text)

    a_flag = b_flag = False
    high_flag = low_flag = False
    kai_flag = zyoui_flag = False
    rarity = None
    kaisin0 = None

    strong_flag = ("強い" in text) or ("最強" in text)
    weak_flag   = ("弱い" in text) or ("最弱" in text)

    attrs = detect_attrs(text, tokens)

    for i in range(len(tokens)):
        token = tokens[i]
        if token == "攻撃":
            a_flag = True
        elif token == "会心":
            b_flag = True
        elif token == "高い":
            high_flag = True
        elif token == "低い":
            low_flag = True
        elif token == "下位":
            kai_flag = True
        elif token == "上位":
            zyoui_flag = True

        if i <= len(tokens) - 3:
            if tokens[i] == "レア" and tokens[i + 1] == "度" and tokens[i + 2].isdigit():
                rarity = int(tokens[i + 2])

    for i in range(len(tokens) - 2):
        if tokens[i] == "会心" and tokens[i + 1] == "率" and tokens[i + 2].isdigit():
            b_flag = False
            kaisin0 = int(tokens[i + 2])
            break

    df_work = df.copy()

    # レア度指定
    if rarity is not None:
        df_work = df_work[pd.to_numeric(df_work["レア度"], errors="coerce") == rarity]

    # 上位・下位フィルタ
    if kai_flag and not zyoui_flag:
        df_work = df_work[pd.to_numeric(df_work["レア度"], errors="coerce") <= 4]
    elif zyoui_flag and not kai_flag:
        df_work = df_work[pd.to_numeric(df_work["レア度"], errors="coerce") >= 5]

    # 会心率 >= N
    if kaisin0 is not None and "会心率" in df_work.columns:
        df_work = df_work[pd.to_numeric(df_work["会心率"], errors="coerce") >= kaisin0]

    if df_work.empty:
        return df_work

    # 属性 × 強い/弱い の優先分岐
    if attrs and (strong_flag or weak_flag) and "総攻撃力" in df_work.columns:
        df_attr = df_work.copy()
        df_attr["__attr_norm__"] = df_attr["属性"].astype(str).map(normalize_attr)
        df_attr = df_attr[df_attr["__attr_norm__"].isin(attrs)]
        if df_attr.empty:
            return df_attr
        df_attr["総攻撃力"] = pd.to_numeric(df_attr["総攻撃力"], errors="coerce")
        if strong_flag:
            key_val = df_attr["総攻撃力"].max()
            return df_attr[df_attr["総攻撃力"] == key_val]
        else:
            key_val = df_attr["総攻撃力"].min()
            return df_attr[df_attr["総攻撃力"] == key_val]

    # 既存仕様: 攻撃/会心 × 高い/低い
    if a_flag and "総攻撃力(物理)" in df_work.columns:
        df_work["総攻撃力(物理)"] = pd.to_numeric(df_work["総攻撃力(物理)"], errors="coerce")
        if high_flag:
            val = df_work["総攻撃力(物理)"].max()
            return df_work[df_work["総攻撃力(物理)"] == val]
        elif low_flag:
            val = df_work["総攻撃力(物理)"].min()
            return df_work[df_work["総攻撃力(物理)"] == val]
        else:
            return df_work

    if b_flag and "会心率" in df_work.columns:
        df_work["会心率"] = pd.to_numeric(df_work["会心率"], errors="coerce")
        if high_flag:
            val = df_work["会心率"].max()
            return df_work[df_work["会心率"] == val]
        elif low_flag:
            val = df_work["会心率"].min()
            return df_work[df_work["会心率"] == val]
        else:
            return df_work

    # 条件が何もなければ現状を返す
    return df_work

def order_cols(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in PREFERRED_COLS if c in df.columns] + [c for c in df.columns if c not in PREFERRED_COLS]
    return df[cols]
