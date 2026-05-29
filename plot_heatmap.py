#!/usr/bin/env python3
"""
plot_heatmap.py
タイプ1・2・3のトリプレットについて、両エッジの LLM 判定（Yes=1 / No=0）の
2×2 ヒートマップを描画する。3パネル共通カラーバー 1本。

入力: /home/sonozuka/network/data/triplets_type{1,2,3}_enriched.csv
出力: /home/sonozuka/network/output/fig_triplet_heatmap.png

スタイル: PRL / Nature Physics 準拠（SKILL.md 参照）
"""

import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as ticker

DATA_DIR   = pathlib.Path("/home/sonozuka/network/data")
OUTPUT_DIR = pathlib.Path("/home/sonozuka/network/output")

# ── スタイル設定 ──────────────────────────────────────────────────────────
RC = {
    "font.family":         "sans-serif",
    "font.sans-serif":     ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size":           13,
    "axes.labelsize":      14,
    "xtick.labelsize":     13,
    "ytick.labelsize":     13,
    "axes.linewidth":      0.7,
    "xtick.direction":     "in",
    "ytick.direction":     "in",
    "xtick.major.size":    4.0,
    "ytick.major.size":    4.0,
    "xtick.major.width":   0.7,
    "ytick.major.width":   0.7,
    "xtick.top":           True,
    "ytick.right":         True,
    "axes.grid":           False,
    "figure.dpi":          100,
    "savefig.dpi":         300,
}

# ── タイプ別設定 ──────────────────────────────────────────────────────────
TYPES = {
    1: dict(
        file   = "triplets_type1_enriched.csv",
        jx_col = "judgment_A_B",
        jy_col = "judgment_B_C",
        x_lbl  = "Judgment (A→B)",
        y_lbl  = "Judgment (B→C)",
        panel  = "(a)",
    ),
    2: dict(
        file   = "triplets_type2_enriched.csv",
        jx_col = "judgment_A_B",
        jy_col = "judgment_C_B",
        x_lbl  = "Judgment (A→B)",
        y_lbl  = "Judgment (C→B)",
        panel  = "(b)",
    ),
    3: dict(
        file   = "triplets_type3_enriched.csv",
        jx_col = "judgment_B_A",
        jy_col = "judgment_C_B",
        x_lbl  = "Judgment (B→A)",
        y_lbl  = "Judgment (C→B)",
        panel  = "(c)",
    ),
}

TICK_LABELS = ["0 (No)", "1 (Yes)"]


def build_matrix(df: pd.DataFrame, jx: str, jy: str) -> np.ndarray:
    """2×2 カウント行列を返す。行=jx、列=jy、0=No / 1=Yes。"""
    mat = np.zeros((2, 2), dtype=int)
    for xi, xv in enumerate(["No", "Yes"]):
        for yi, yv in enumerate(["No", "Yes"]):
            mat[xi, yi] = int(((df[jx] == xv) & (df[jy] == yv)).sum())
    return mat


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 全タイプのカウント行列を先に計算して vmax を確定 ─────────────────
    matrices = {}
    for tnum, cfg in TYPES.items():
        df = pd.read_csv(DATA_DIR / cfg["file"])
        matrices[tnum] = build_matrix(df, cfg["jx_col"], cfg["jy_col"])

    vmax = max(m.max() for m in matrices.values())
    norm = mcolors.Normalize(vmin=0, vmax=vmax)
    cmap = plt.cm.Blues   # モノクロ印刷・色覚多様性対応

    with plt.rc_context(RC):
        # パネル幅 2.4 inch × 3 + カラーバー 0.35 inch + 余白
        fig, axes = plt.subplots(
            1, 3,
            figsize=(8.0, 2.8),
            constrained_layout=False,
        )
        fig.subplots_adjust(left=0.07, right=0.88, top=0.92,
                            bottom=0.18, wspace=0.38)

        for idx, (tnum, cfg) in enumerate(TYPES.items()):
            ax  = axes[idx]
            mat = matrices[tnum]

            im = ax.imshow(mat, cmap=cmap, norm=norm,
                           aspect="equal", origin="lower")

            # セル内にカウント値を表示
            for xi in range(2):
                for yi in range(2):
                    count = mat[xi, yi]
                    # 背景が濃い場合は白文字、薄い場合は黒文字
                    rel   = count / vmax
                    color = "white" if rel > 0.55 else "black"
                    ax.text(yi, xi, f"{count:,}",
                            ha="center", va="center",
                            fontsize=13, fontweight="bold", color=color)

            # 軸設定
            ax.set_xticks([0, 1])
            ax.set_yticks([0, 1])
            ax.set_xticklabels(TICK_LABELS)
            ax.set_yticklabels(TICK_LABELS)
            ax.set_xlabel(cfg["x_lbl"])
            ax.set_ylabel(cfg["y_lbl"])

            # パネルラベル
            ax.text(-0.18, 1.06, cfg["panel"],
                    transform=ax.transAxes,
                    fontsize=14, fontweight="bold", va="top")

            # スパイン統一
            for spine in ax.spines.values():
                spine.set_linewidth(0.7)

            # ティックを外側に出さない（ヒートマップはティック不要）
            ax.tick_params(direction="out", length=0)

        # ── 共通カラーバー（図の右端に1本）────────────────────────────
        cbar_ax = fig.add_axes([0.905, 0.18, 0.018, 0.74])
        sm  = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, cax=cbar_ax)
        cbar.set_label("Count", fontsize=13)
        cbar.ax.tick_params(labelsize=12)
        cbar.outline.set_linewidth(0.7)

        out = OUTPUT_DIR / "fig_triplet_heatmap.png"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"保存: {out}")

        # ── 統計サマリー ──────────────────────────────────────────────
        print("\n【カウント行列】")
        for tnum, mat in matrices.items():
            print(f"  Type {tnum}:")
            print(f"    (No,No)={mat[0,0]:,}  (No,Yes)={mat[0,1]:,}")
            print(f"    (Yes,No)={mat[1,0]:,}  (Yes,Yes)={mat[1,1]:,}")


if __name__ == "__main__":
    main()
