# search_core.py
# -*- coding: utf-8 -*-
import os
import pandas as pd
from janome.tokenizer import Tokenizer

# === 属性の正規化 =====================================
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


def _normalize_attr(s: str):
    if s is None:
        return None
    s = str(s).strip()
    return _ATTR_ALIASES.get(s, s)


def _detect_attributes_from_query(text: str, tokens):
    found = set()
    t = text
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


# === ファイル読み込み =================================
_WEAPON_CANDIDATE_FILES = [
    "大剣.xlsx",
    "大剣 - コピー.xlsx",
    "大剣 - コピ゚ー.xlsx",
    "大剣 - コピー.xlsx",
]


def load_weapon_df():
    """大剣.xlsx 系を探して読み込む"""
    last_err = None
    for name in _WEAPON_CANDIDATE_FILES:
        if os.path.exists(name):
            try:
                return pd.read_excel(name)
            except Exception as e:
                last_err = e
    if last_err:
        raise last_err
    raise FileNotFoundError("武器データファイル（大剣.xlsx 等）が見つかりません。")


def _load_monster_df():
    candidates = ["モンスター一覧.xlsx", os.path.join("/mnt/data", "モンスター一覧.xlsx")]
    last = None
    for path in candidates:
        if os.path.exists(path):
            try:
                df = pd.read_excel(path)
                if not {"モンスター名", "弱点"}.issubset(set(df.columns)):
                    raise ValueError("モンスター一覧.xlsx のカラム名が想定と異なります（必要: モンスター名, 弱点）。")
                df["__weak_norm__"] = df["弱点"].map(_normalize_attr)
                df["__name__"] = df["モンスター名"].astype(str)
                if "下位" in df.columns:
                    df["__low_rank__"] = pd.to_numeric(df["下位"], errors="coerce")
                else:
                    df["__low_rank__"] = pd.NA
                return df
            except Exception as e:
                last = e
    return None


_MON_DF = _load_monster_df()


def _detect_monster_and_weak_attr(text: str):
    if _MON_DF is None or _MON_DF.empty:
        return []
    t = str(text)
    hits = []
    for _, row in _MON_DF.iterrows():
        name = row["__name__"]
        if name and name in t:
            weak = row["__weak_norm__"]
            if weak:
                hits.append((name, weak))
    return hits


def _get_monster_low_rank(monster_name: str):
    if _MON_DF is None or _MON_DF.empty:
        return None
    name = str(monster_name)
    sub = _MON_DF[_MON_DF["__name__"] == name]
    if sub.empty or "__low_rank__" not in sub.columns:
        return None
    vals = pd.to_numeric(sub["__low_rank__"], errors="coerce").dropna()
    if vals.empty:
        return None
    try:
        return int(vals.iloc[0])
    except Exception:
        return None


# === フレーズ検出（効く/最強 の同義語） ======================
MOST_PATTERNS = ["最強", "一番効く", "一番有効な", "一番効果のある"]
EFFECTIVE_PATTERNS = ["効く", "有効", "強い", "効果のある"]


def _has_any(text: str, patterns):
    return any(p in text for p in patterns)


_tokenizer = Tokenizer()


# === Web 用のメイン処理 ================================
def search_weapons(text: str, rank_choice: str):
    """
    質問文と「下位/上位」を受け取り、条件に合う DataFrame と説明メッセージを返す。
    """
    text = (text or "").strip()
    if not text:
        return pd.DataFrame(), "テキストを入力してください。"

    if rank_choice not in ("下位", "上位"):
        return pd.DataFrame(), "下位か上位を選択してください。"

    try:
        df = load_weapon_df()
    except FileNotFoundError as e:
        return pd.DataFrame(), str(e)

    tokens = [t.surface for t in _tokenizer.tokenize(text)]

    # フラグ類
    a_flag = b_flag = False
    high_flag = low_flag = False
    kai_flag = zyoui_flag = False
    rarity = None
    kaisin0 = None

    strong_flag = ("強い" in text) or ("最強" in text)
    weak_flag = ("弱い" in text) or ("最弱" in text)

    most_effective_flag = _has_any(text, MOST_PATTERNS)
    effective_flag = _has_any(text, EFFECTIVE_PATTERNS) and not most_effective_flag

    # 属性 & モンスター検出
    attrs = _detect_attributes_from_query(text, tokens)
    mon_hits = _detect_monster_and_weak_attr(text)
    if mon_hits:
        attrs_from_mon = {weak for _, weak in mon_hits}
        attrs |= attrs_from_mon

    # 条件解析
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

    # データ前処理
    df_work = df.copy()
    if rarity is not None:
        df_work = df_work[pd.to_numeric(df_work["レア度"], errors="coerce") == rarity]
    if kai_flag and not zyoui_flag:
        df_work = df_work[pd.to_numeric(df_work["レア度"], errors="coerce") <= 4]
    elif zyoui_flag and not kai_flag:
        df_work = df_work[pd.to_numeric(df_work["レア度"], errors="coerce") >= 5]
    if kaisin0 is not None and "会心率" in df_work.columns:
        df_work = df_work[pd.to_numeric(df_work["会心率"], errors="coerce") >= kaisin0]

    message = ""
    result_df = pd.DataFrame()

    # ===== モンスター名が含まれている場合 =====
    if mon_hits and attrs:
        df_attr = df_work.copy()
        df_attr["__attr_norm__"] = df_attr["属性"].astype(str).map(_normalize_attr)
        df_attr = df_attr[df_attr["__attr_norm__"].isin(attrs)]
        df_attr["総攻撃力"] = pd.to_numeric(df_attr["総攻撃力"], errors="coerce")

        first_mon_name = mon_hits[0][0]
        mon_low_rank = _get_monster_low_rank(first_mon_name)

        if rank_choice == "下位":
            if (mon_low_rank is not None) and ("下位" in df_attr.columns):
                weapon_low = pd.to_numeric(df_attr["下位"], errors="coerce")
                df_attr = df_attr[weapon_low < mon_low_rank]

        mons = ", ".join([f"{n}（弱点:{w}）" for n, w in mon_hits])

        if df_attr.empty:
            # fallback: 弱点属性が無いときは物理最大
            df_fallback = df_work.copy()
            if rank_choice == "下位" and (mon_low_rank is not None) and ("下位" in df_fallback.columns):
                weapon_low_all = pd.to_numeric(df_fallback["下位"], errors="coerce")
                df_fallback = df_fallback[weapon_low_all < mon_low_rank]

            if df_fallback.empty:
                return pd.DataFrame(), f"[モンスター検出] {mons}\n該当する武器が見つかりませんでした。"

            df_fallback["総攻撃力(物理)"] = pd.to_numeric(df_fallback["総攻撃力(物理)"], errors="coerce")
            max_phys = df_fallback["総攻撃力(物理)"].max()
            result_df = df_fallback[df_fallback["総攻撃力(物理)"] == max_phys]
            message = (
                f"[モンスター検出] {mons}\n"
                "弱点属性の武器が無かったため、条件内で総攻撃力(物理)が最大の武器を表示しています。"
            )
        else:
            if most_effective_flag:
                key_val = df_attr["総攻撃力"].max()
                result_df = df_attr[df_attr["総攻撃力"] == key_val]
                message = f"[モンスター検出] {mons}（最強系判定：総攻撃力 最大）"
            elif effective_flag:
                result_df = df_attr.sort_values("総攻撃力", ascending=False).head(3)
                message = f"[モンスター検出] {mons}（効く系判定：総攻撃力 上位3件）"
            else:
                result_df = df_attr.sort_values("総攻撃力", ascending=False)
                message = f"[モンスター検出] {mons}"

    # ===== それ以外（従来ロジック） =====
    else:
        if df_work.empty:
            return pd.DataFrame(), "条件に合うデータがありません。"

        if attrs and (("強い" in text) or ("最強" in text) or strong_flag):
            df_attr = df_work.copy()
            df_attr["__attr_norm__"] = df_attr["属性"].astype(str).map(_normalize_attr)
            df_attr = df_attr[df_attr["__attr_norm__"].isin(attrs)]
            if df_attr.empty:
                return pd.DataFrame(), "指定の属性に一致するデータがありません。"
            df_attr["総攻撃力"] = pd.to_numeric(df_attr["総攻撃力"], errors="coerce")
            key_val = df_attr["総攻撃力"].max()
            result_df = df_attr[df_attr["総攻撃力"] == key_val]

        elif attrs and (("弱い" in text) or ("最弱" in text) or weak_flag):
            df_attr = df_work.copy()
            df_attr["__attr_norm__"] = df_attr["属性"].astype(str).map(_normalize_attr)
            df_attr = df_attr[df_attr["__attr_norm__"].isin(attrs)]
            if df_attr.empty:
                return pd.DataFrame(), "指定の属性に一致するデータがありません。"
            df_attr["総攻撃力"] = pd.to_numeric(df_attr["総攻撃力"], errors="coerce")
            key_val = df_attr["総攻撃力"].min()
            result_df = df_attr[df_attr["総攻撃力"] == key_val]

        elif a_flag and "総攻撃力(物理)" in df_work.columns:
            df_work["総攻撃力(物理)"] = pd.to_numeric(df_work["総攻撃力(物理)"], errors="coerce")
            if high_flag:
                max_value = df_work["総攻撃力(物理)"].max()
                result_df = df_work[df_work["総攻撃力(物理)"] == max_value]
            elif low_flag:
                min_value = df_work["総攻撃力(物理)"].min()
                result_df = df_work[df_work["総攻撃力(物理)"] == min_value]
            else:
                result_df = df_work

        elif b_flag and "会心率" in df_work.columns:
            df_work["会心率"] = pd.to_numeric(df_work["会心率"], errors="coerce")
            if high_flag:
                max_value = df_work["会心率"].max()
                result_df = df_work[df_work["会心率"] == max_value]
            elif low_flag:
                min_value = df_work["会心率"].min()
                result_df = df_work[df_work["会心率"] == min_value]
            else:
                result_df = df_work
        else:
            result_df = df_work

    if result_df is None or result_df.empty:
        if not message:
            message = "該当する条件が見つかりませんでした。"
        return result_df, message

    return result_df, message

