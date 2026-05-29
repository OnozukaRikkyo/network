#!/usr/bin/env python3
"""
enrich_triplets.py
各トリプレットの2つのエッジにコサイン類似度・LLM判定・理由を付与して CSV に保存する。

データソース:
  /mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl
  使用フィールド: source, target, similarity, judgment, reason

入力:
  data/triplets_type1.csv  (node_A, node_B, node_C)
  data/triplets_type2.csv
  data/triplets_type3.csv

出力:
  data/triplets_type1_enriched.csv
  data/triplets_type2_enriched.csv
  data/triplets_type3_enriched.csv

出力列:
  タイプ1: node_A, node_B, node_C,
           sim_A_B, judgment_A_B, reason_A_B,
           sim_B_C, judgment_B_C, reason_B_C
  タイプ2: node_A, node_B, node_C,
           sim_A_B, judgment_A_B, reason_A_B,
           sim_C_B, judgment_C_B, reason_C_B
  タイプ3: node_A, node_B, node_C,
           sim_B_A, judgment_B_A, reason_B_A,
           sim_C_B, judgment_C_B, reason_C_B

ルックアップキー正規化: (min(u, v), max(u, v))
"""

import json
import pathlib
import pandas as pd

SIM_SRC  = pathlib.Path("/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl")
DATA_DIR = pathlib.Path("/home/sonozuka/network/data")


# ── ルックアップテーブル構築 ───────────────────────────────────────────────

def load_edge_features() -> dict[tuple, dict]:
    """
    (source, target) → {similarity, judgment, reason} のマップを返す。
    キーは (min(u,v), max(u,v)) に正規化済み。
    """
    feat: dict[tuple, dict] = {}
    with open(SIM_SRC) as f:
        for line in f:
            r = json.loads(line)
            key = (r["source"], r["target"])   # source < target 保証済み
            feat[key] = {
                "similarity": r["similarity"],
                "judgment":   r["judgment"],
                "reason":     r.get("reason", ""),
            }
    print(f"エッジ特徴量ロード: {len(feat):,} ペア  ({SIM_SRC.name})")
    return feat


def lookup(feat: dict, u: str, v: str) -> tuple:
    """エッジ (u, v) の (similarity, judgment, reason) を返す。欠損は None。"""
    key = (min(u, v), max(u, v))
    r = feat.get(key)
    if r is None:
        return None, None, None
    return r["similarity"], r["judgment"], r["reason"]


# ── 付与処理 ──────────────────────────────────────────────────────────────

def enrich(feat: dict) -> dict[str, pd.DataFrame]:
    results: dict[str, pd.DataFrame] = {}

    # ── タイプ1: A -> B -> C
    t1 = pd.read_csv(DATA_DIR / "triplets_type1.csv")
    t1[["sim_A_B", "judgment_A_B", "reason_A_B"]] = t1.apply(
        lambda r: pd.Series(lookup(feat, r["node_A"], r["node_B"])), axis=1
    )
    t1[["sim_B_C", "judgment_B_C", "reason_B_C"]] = t1.apply(
        lambda r: pd.Series(lookup(feat, r["node_B"], r["node_C"])), axis=1
    )
    results["type1"] = t1

    # ── タイプ2: A -> B <- C
    t2 = pd.read_csv(DATA_DIR / "triplets_type2.csv")
    t2[["sim_A_B", "judgment_A_B", "reason_A_B"]] = t2.apply(
        lambda r: pd.Series(lookup(feat, r["node_A"], r["node_B"])), axis=1
    )
    t2[["sim_C_B", "judgment_C_B", "reason_C_B"]] = t2.apply(
        lambda r: pd.Series(lookup(feat, r["node_C"], r["node_B"])), axis=1
    )
    results["type2"] = t2

    # ── タイプ3: A <- B <- C
    t3 = pd.read_csv(DATA_DIR / "triplets_type3.csv")
    t3[["sim_B_A", "judgment_B_A", "reason_B_A"]] = t3.apply(
        lambda r: pd.Series(lookup(feat, r["node_B"], r["node_A"])), axis=1
    )
    t3[["sim_C_B", "judgment_C_B", "reason_C_B"]] = t3.apply(
        lambda r: pd.Series(lookup(feat, r["node_C"], r["node_B"])), axis=1
    )
    results["type3"] = t3

    return results


# ── 統計表示 ──────────────────────────────────────────────────────────────

def print_stats(results: dict[str, pd.DataFrame]) -> None:
    cfg = {
        "type1": ("A→B→C（連鎖）",   [("sim_A_B", "judgment_A_B"), ("sim_B_C", "judgment_B_C")]),
        "type2": ("A→B←C（収束）",   [("sim_A_B", "judgment_A_B"), ("sim_C_B", "judgment_C_B")]),
        "type3": ("A←B←C（連鎖逆）", [("sim_B_A", "judgment_B_A"), ("sim_C_B", "judgment_C_B")]),
    }
    sep = "=" * 68
    print(f"\n{sep}")
    print("  トリプレット × エッジ特徴量 統計")
    print(sep)

    for key, (label, edge_pairs) in cfg.items():
        df = results[key]
        print(f"\n【タイプ{key[-1]}: {label}】  {len(df):,} 件")
        for sim_col, judg_col in edge_pairs:
            s    = df[sim_col].dropna()
            judg = df[judg_col].dropna()
            yes  = (judg == "Yes").sum()
            no   = (judg == "No").sum()
            miss_s = df[sim_col].isna().sum()
            miss_j = df[judg_col].isna().sum()
            print(f"  {sim_col}:")
            print(f"    similarity  N={len(s):,}（欠損={miss_s}）  "
                  f"min={s.min():.4f}  max={s.max():.4f}  "
                  f"mean={s.mean():.4f}  median={s.median():.4f}")
            print(f"  {judg_col}:")
            print(f"    judgment    N={len(judg):,}（欠損={miss_j}）  "
                  f"Yes={yes:,}（{yes/len(judg)*100:.1f}%）  "
                  f"No={no:,}（{no/len(judg)*100:.1f}%）")

    print(f"\n{sep}")


# ── メイン ────────────────────────────────────────────────────────────────

def main() -> None:
    feat    = load_edge_features()
    results = enrich(feat)
    print_stats(results)

    for key, df in results.items():
        out = DATA_DIR / f"triplets_{key}_enriched.csv"
        df.to_csv(out, index=False)
        print(f"保存: {out}  ({len(df):,} 行, {len(df.columns)} 列)")


if __name__ == "__main__":
    main()
