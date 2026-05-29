#!/usr/bin/env python3
"""
add_similarity.py
各トリプレットの2つのエッジにコサイン類似度を付与して CSV に再保存する。

類似度ソース:
  /mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl
  フィールド: source, target, similarity（コサイン類似度 0–1）
  キー正規化: source < target（アルファベット順）

入力:
  data/triplets_type1.csv  (node_A, node_B, node_C)
  data/triplets_type2.csv
  data/triplets_type3.csv

出力:
  data/triplets_type1_sim.csv  (node_A, node_B, node_C, sim_A_B, sim_B_C)
  data/triplets_type2_sim.csv  (node_A, node_B, node_C, sim_A_B, sim_C_B)
  data/triplets_type3_sim.csv  (node_A, node_B, node_C, sim_B_A, sim_C_B)
"""

import json
import pathlib
import pandas as pd

SIM_SRC  = pathlib.Path("/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl")
DATA_DIR = pathlib.Path("/home/sonozuka/network/data")


# ── 類似度ルックアップテーブルを構築 ──────────────────────────────────────
def load_similarity() -> dict[tuple, float]:
    """
    (source, target) → similarity のマップを返す。
    キーは常に (min, max) に正規化済み（source < target アルファベット順）。
    """
    sim_map: dict[tuple, float] = {}
    with open(SIM_SRC) as f:
        for line in f:
            r = json.loads(line)
            key = (r["source"], r["target"])  # すでに source < target
            sim_map[key] = r["similarity"]
    print(f"類似度ルックアップ: {len(sim_map):,} ペア（{SIM_SRC}）")
    return sim_map


def lookup(sim_map: dict, u: str, v: str) -> float | None:
    """エッジ (u, v) のコサイン類似度を返す。キーを正規化して検索。"""
    key = (min(u, v), max(u, v))
    return sim_map.get(key, None)


# ── 各タイプに類似度列を付与 ──────────────────────────────────────────────
def process(sim_map: dict) -> dict[str, pd.DataFrame]:
    results: dict[str, pd.DataFrame] = {}

    # ── タイプ1: A -> B -> C
    t1 = pd.read_csv(DATA_DIR / "triplets_type1.csv")
    t1["sim_A_B"] = t1.apply(lambda r: lookup(sim_map, r["node_A"], r["node_B"]), axis=1)
    t1["sim_B_C"] = t1.apply(lambda r: lookup(sim_map, r["node_B"], r["node_C"]), axis=1)
    results["type1"] = t1

    # ── タイプ2: A -> B <- C
    t2 = pd.read_csv(DATA_DIR / "triplets_type2.csv")
    t2["sim_A_B"] = t2.apply(lambda r: lookup(sim_map, r["node_A"], r["node_B"]), axis=1)
    t2["sim_C_B"] = t2.apply(lambda r: lookup(sim_map, r["node_C"], r["node_B"]), axis=1)
    results["type2"] = t2

    # ── タイプ3: A <- B <- C
    t3 = pd.read_csv(DATA_DIR / "triplets_type3.csv")
    t3["sim_B_A"] = t3.apply(lambda r: lookup(sim_map, r["node_B"], r["node_A"]), axis=1)
    t3["sim_C_B"] = t3.apply(lambda r: lookup(sim_map, r["node_C"], r["node_B"]), axis=1)
    results["type3"] = t3

    return results


# ── 統計表示 ──────────────────────────────────────────────────────────────
def print_stats(results: dict[str, pd.DataFrame]) -> None:
    import numpy as np

    cfg = {
        "type1": ("A→B→C（連鎖）",   ["sim_A_B", "sim_B_C"]),
        "type2": ("A→B←C（収束）",   ["sim_A_B", "sim_C_B"]),
        "type3": ("A←B←C（連鎖逆）", ["sim_B_A", "sim_C_B"]),
    }
    sep = "=" * 64
    print(f"\n{sep}")
    print("  トリプレット × コサイン類似度 統計")
    print(sep)

    for key, (label, cols) in cfg.items():
        df = results[key]
        print(f"\n【タイプ{key[-1]}: {label}】  {len(df):,} 件")
        for col in cols:
            s = df[col].dropna()
            miss = df[col].isna().sum()
            print(f"  {col}:  N={len(s):,}（欠損={miss}）  "
                  f"min={s.min():.4f}  max={s.max():.4f}  "
                  f"mean={s.mean():.4f}  std={s.std():.4f}  "
                  f"median={s.median():.4f}")

    print(f"\n{sep}")


# ── メイン ────────────────────────────────────────────────────────────────
def main() -> None:
    sim_map = load_similarity()
    results = process(sim_map)
    print_stats(results)

    for key, df in results.items():
        out = DATA_DIR / f"triplets_{key}_sim.csv"
        df.to_csv(out, index=False)
        print(f"保存: {out}  ({len(df):,} 行, {len(df.columns)} 列)")


if __name__ == "__main__":
    main()
