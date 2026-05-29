#!/usr/bin/env python3
"""
plot_triplets.py
タイプ1・2・3のトリプレットについて、2エッジのコサイン類似度の散布図を出力する。
1タイプ1ファイル（PNG のみ）。

横軸: 第1エッジのコサイン類似度
縦軸: 第2エッジのコサイン類似度
マーカー: 中抜き・同サイズ・濃色 1色

スタイル: PRL / Nature Physics 準拠
入力: /home/sonozuka/network/data/triplets_type{1,2,3}_enriched.csv
出力: /home/sonozuka/network/output/fig_triplet1_scatter.png
     /home/sonozuka/network/output/fig_triplet2_scatter.png
     /home/sonozuka/network/output/fig_triplet3_scatter.png
"""

import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

DATA_DIR   = pathlib.Path("/home/sonozuka/network/data")
OUTPUT_DIR = pathlib.Path("/home/sonozuka/network/output")

# ── 物理学論文スタイル（PRL / Nature Physics 準拠）────────────────────────
RC = {
    "font.family":         "sans-serif",
    "font.sans-serif":     ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size":           8,
    "axes.labelsize":      9,
    "xtick.labelsize":     8,
    "ytick.labelsize":     8,
    "axes.linewidth":      0.7,
    "xtick.direction":     "in",
    "ytick.direction":     "in",
    "xtick.major.size":    4.5,
    "ytick.major.size":    4.5,
    "xtick.minor.size":    2.2,
    "ytick.minor.size":    2.2,
    "xtick.major.width":   0.7,
    "ytick.major.width":   0.7,
    "xtick.minor.width":   0.4,
    "ytick.minor.width":   0.4,
    "xtick.minor.visible": True,
    "ytick.minor.visible": True,
    "xtick.top":           True,
    "ytick.right":         True,
    "axes.grid":           False,
    "legend.frameon":      False,
    "figure.dpi":          100,
    "savefig.dpi":         300,
}

# ── タイプ別設定 ──────────────────────────────────────────────────────────
TYPES = {
    1: dict(
        file  = "triplets_type1_enriched.csv",
        x_col = "sim_A_B",
        y_col = "sim_B_C",
        x_lbl = "Cosine similarity (A→B)",
        y_lbl = "Cosine similarity (B→C)",
    ),
    2: dict(
        file  = "triplets_type2_enriched.csv",
        x_col = "sim_A_B",
        y_col = "sim_C_B",
        x_lbl = "Cosine similarity (A→B)",
        y_lbl = "Cosine similarity (C→B)",
    ),
    3: dict(
        file  = "triplets_type3_enriched.csv",
        x_col = "sim_B_A",
        y_col = "sim_C_B",
        x_lbl = "Cosine similarity (B→A)",
        y_lbl = "Cosine similarity (C→B)",
    ),
}

MARKER_COLOR = "#1a3a6b"   # ネイビーブルー（濃色）
MARKER_SIZE  = 10          # pt²（全タイプ共通）
MARKER_ALPHA = 0.45
MARKER_LW    = 0.6         # 中抜きマーカーの枠線幅

LIM = [0.38, 1.02]


def make_figure(df: pd.DataFrame, cfg: dict) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(3.5, 3.5))

    x = df[cfg["x_col"]].values
    y = df[cfg["y_col"]].values

    ax.scatter(
        x, y,
        s=MARKER_SIZE,
        facecolors="none",        # 中抜き
        edgecolors=MARKER_COLOR,
        linewidths=MARKER_LW,
        alpha=MARKER_ALPHA,
        rasterized=True,
    )

    # 対角参照線 (x = y)
    ax.plot(LIM, LIM, lw=0.7, ls=":", color="#555555", zorder=0)

    # 軸設定
    ax.set_xlim(LIM)
    ax.set_ylim(LIM)
    ax.set_xlabel(cfg["x_lbl"])
    ax.set_ylabel(cfg["y_lbl"])

    ax.xaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.05))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.05))

    # 全辺のスパイン幅を統一
    for spine in ax.spines.values():
        spine.set_linewidth(0.7)

    fig.tight_layout()
    return fig


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with plt.rc_context(RC):
        for tnum, cfg in TYPES.items():
            df  = pd.read_csv(DATA_DIR / cfg["file"])
            fig = make_figure(df, cfg)
            out = OUTPUT_DIR / f"fig_triplet{tnum}_scatter.png"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            plt.close(fig)
            print(f"保存: {out}  ({len(df):,} 点)")


if __name__ == "__main__":
    main()
