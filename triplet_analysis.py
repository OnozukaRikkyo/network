#!/usr/bin/env python3
"""
triplet_analysis.py
有向グラフの3ノードパターン（トリプレット）を抽出し CSV に出力する。

タイプ1: A -> B -> C  （連鎖）
タイプ2: A -> B <- C  （収束）
タイプ3: A <- B <- C  （連鎖・逆向き）

入力: /home/sonozuka/network/data/d18_edges.csv
出力: /home/sonozuka/network/data/triplets_type{1,2,3}.csv
"""

import pathlib
import pandas as pd

DATA_DIR = pathlib.Path("/home/sonozuka/network/data")
INPUT    = DATA_DIR / "d18_edges.csv"
OUT_T1   = DATA_DIR / "triplets_type1.csv"
OUT_T2   = DATA_DIR / "triplets_type2.csv"
OUT_T3   = DATA_DIR / "triplets_type3.csv"


def main() -> None:
    # ── 読み込み ──────────────────────────────────────────────────────
    edges_df = pd.read_csv(INPUT)
    edges    = edges_df[["source", "target"]].drop_duplicates().reset_index(drop=True)
    print(f"入力: {INPUT}")
    print(f"ユニークエッジ数: {len(edges):,}")

    # ── タイプ1: A -> B -> C ──────────────────────────────────────────
    # edges(A->B) と edges(B->C) を B で結合
    t1 = pd.merge(edges, edges,
                  left_on="target", right_on="source",
                  suffixes=("_A", "_C"))
    t1 = t1.rename(columns={"source_A": "node_A",
                             "target_A": "node_B",
                             "target_C": "node_C"})
    t1 = t1[["node_A", "node_B", "node_C"]]
    t1 = t1[t1["node_A"] != t1["node_C"]]   # 自己ループ除外

    # ── タイプ2: A -> B <- C ──────────────────────────────────────────
    # edges(A->B) と edges(C->B) を B（target）で結合
    t2 = pd.merge(edges, edges,
                  on="target",
                  suffixes=("_A", "_C"))
    t2 = t2.rename(columns={"source_A": "node_A",
                             "target":   "node_B",
                             "source_C": "node_C"})
    t2 = t2[["node_A", "node_B", "node_C"]]
    t2 = t2[t2["node_A"] < t2["node_C"]]    # 対称性・自己ループ除外

    # ── タイプ3: A <- B <- C ──────────────────────────────────────────
    # edges(B->A) と edges(C->B) を B で結合
    t3 = pd.merge(edges, edges,
                  left_on="source", right_on="target",
                  suffixes=("_BA", "_CB"))
    t3 = t3.rename(columns={"target_BA": "node_A",
                             "source_BA": "node_B",
                             "source_CB": "node_C"})
    t3 = t3[["node_A", "node_B", "node_C"]]
    t3 = t3[t3["node_A"] != t3["node_C"]]   # 自己ループ除外

    # ── 出力 ──────────────────────────────────────────────────────────
    t1.to_csv(OUT_T1, index=False)
    t2.to_csv(OUT_T2, index=False)
    t3.to_csv(OUT_T3, index=False)

    print(f"\n【トリプレット抽出結果】")
    print(f"  タイプ1 (A->B->C) : {len(t1):,} 件  →  {OUT_T1}")
    print(f"  タイプ2 (A->B<-C) : {len(t2):,} 件  →  {OUT_T2}")
    print(f"  タイプ3 (A<-B<-C) : {len(t3):,} 件  →  {OUT_T3}")
    print(f"  合計               : {len(t1)+len(t2)+len(t3):,} 件")


if __name__ == "__main__":
    main()