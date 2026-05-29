#!/usr/bin/env python3
"""
plot_triplets.py
タイプ1・2・3のトリプレットについて、2エッジのコサイン類似度の散布図を出力する。

横軸: 第1エッジ (AB) のコサイン類似度
縦軸: 第2エッジ (BC) のコサイン類似度
色:   両エッジの judgment 組み合わせ（Yes-Yes / Yes-No / No-Yes / No-No）

物理学論文スタイル（PRL / Nature Physics 準拠）:
  - 図幅 7.2 inch (ダブルカラム)、3パネル横並び
  - フォント 8/7 pt sans-serif
  - 内向きティック・マイナーティック表示
  - 上右スパイン除去
  - Okabe-Ito カラーパレット（色覚多様性対応）
  - KDE 密度等高線でオーバープロット可視化
  - 300 DPI PNG + PDF（ベクター）出力

入力: /home/sonozuka/network/data/triplets_type{1,2,3}_enriched.csv
出力: /home/sonozuka/network/output/fig_triplet_scatter.png
     /home/sonozuka/network/output/fig_triplet_scatter.pdf
"""

import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
from scipy.stats import gaussian_kde

DATA_DIR   = pathlib.Path("/home/sonozuka/network/data")
OUTPUT_DIR = pathlib.Path("/home/sonozuka/network/output")

# ── Okabe-Ito カラーパレット（色覚多様性対応）────────────────────────────
C_NN = "#999999"   # No-No   : グレー
C_YN = "#E69F00"   # Yes-No  : オレンジ
C_NY = "#56B4E9"   # No-Yes  : スカイブルー
C_YY = "#D55E00"   # Yes-Yes : バーミリオン（最重要）

# ── 物理学論文スタイル設定（PRL / Nature Physics 準拠）──────────────────
RC = {
    "font.family":           "sans-serif",
    "font.sans-serif":       ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size":             8,
    "axes.labelsize":        8,
    "axes.titlesize":        9,
    "xtick.labelsize":       7,
    "ytick.labelsize":       7,
    "legend.fontsize":       7,
    "axes.linewidth":        0.6,
    "lines.linewidth":       0.8,
    "xtick.direction":       "in",
    "ytick.direction":       "in",
    "xtick.major.size":      4.0,
    "ytick.major.size":      4.0,
    "xtick.minor.size":      2.0,
    "ytick.minor.size":      2.0,
    "xtick.major.width":     0.6,
    "ytick.major.width":     0.6,
    "xtick.minor.width":     0.4,
    "ytick.minor.width":     0.4,
    "xtick.minor.visible":   True,
    "ytick.minor.visible":   True,
    "xtick.top":             True,   # 上辺にもティック
    "ytick.right":           True,   # 右辺にもティック
    "legend.frameon":        False,
    "legend.handlelength":   1.2,
    "figure.dpi":            100,
    "savefig.dpi":           300,
    "savefig.bbox":          "tight",
    "axes.grid":             False,
}

# ── データ設定 ───────────────────────────────────────────────────────────
TYPES = {
    1: dict(
        file    = "triplets_type1_enriched.csv",
        x_col   = "sim_A_B",
        y_col   = "sim_B_C",
        jx_col  = "judgment_A_B",
        jy_col  = "judgment_B_C",
        x_label = r"Cosine similarity $s_{AB}$",
        y_label = r"Cosine similarity $s_{BC}$",
        title   = r"Type 1: $A \rightarrow B \rightarrow C$",
    ),
    2: dict(
        file    = "triplets_type2_enriched.csv",
        x_col   = "sim_A_B",
        y_col   = "sim_C_B",
        jx_col  = "judgment_A_B",
        jy_col  = "judgment_C_B",
        x_label = r"Cosine similarity $s_{AB}$",
        y_label = r"Cosine similarity $s_{CB}$",
        title   = r"Type 2: $A \rightarrow B \leftarrow C$",
    ),
    3: dict(
        file    = "triplets_type3_enriched.csv",
        x_col   = "sim_B_A",
        y_col   = "sim_C_B",
        jx_col  = "judgment_B_A",
        jy_col  = "judgment_C_B",
        x_label = r"Cosine similarity $s_{BA}$",
        y_label = r"Cosine similarity $s_{CB}$",
        title   = r"Type 3: $A \leftarrow B \leftarrow C$",
    ),
}


# ── KDE 等高線を描画 ──────────────────────────────────────────────────────
def draw_kde(ax, x, y, color, levels=(0.25, 0.55, 0.80)):
    """ガウシアン KDE の密度等高線を重ね描きする。"""
    if len(x) < 10:
        return
    try:
        xy  = np.vstack([x, y])
        kde = gaussian_kde(xy, bw_method="scott")
        xi  = np.linspace(x.min() - 0.02, x.max() + 0.02, 120)
        yi  = np.linspace(y.min() - 0.02, y.max() + 0.02, 120)
        Xi, Yi = np.meshgrid(xi, yi)
        Zi  = kde(np.vstack([Xi.ravel(), Yi.ravel()])).reshape(Xi.shape)
        # 指定レベルをパーセンタイルで計算
        z_flat  = np.sort(Zi.ravel())[::-1]
        z_cum   = np.cumsum(z_flat) / z_cum.sum() if False else None
        z_thresh = [np.percentile(Zi, (1 - lv) * 100) for lv in levels]
        ax.contour(Xi, Yi, Zi, levels=z_thresh,
                   colors=[color], linewidths=0.8, alpha=0.7,
                   linestyles=["--", "-.", "-"])
    except Exception:
        pass  # KDE 失敗時は等高線なしで続行


# ── 1パネルを描画 ─────────────────────────────────────────────────────────
def draw_panel(ax, df: pd.DataFrame, cfg: dict, panel_label: str) -> None:
    x    = df[cfg["x_col"]].values
    y    = df[cfg["y_col"]].values
    jx   = df[cfg["jx_col"]].values
    jy   = df[cfg["jy_col"]].values

    # judgment 組み合わせでマスクを作成
    masks = {
        "No-No" : (jx == "No")  & (jy == "No"),
        "Yes-No": (jx == "Yes") & (jy == "No"),
        "No-Yes": (jx == "No")  & (jy == "Yes"),
        "Yes-Yes":(jx == "Yes") & (jy == "Yes"),
    }
    colors = {
        "No-No":  C_NN,
        "Yes-No": C_YN,
        "No-Yes": C_NY,
        "Yes-Yes":C_YY,
    }
    sizes  = {"No-No": 4, "Yes-No": 8, "No-Yes": 8, "Yes-Yes": 12}
    alphas = {"No-No": 0.25, "Yes-No": 0.60, "No-Yes": 0.60, "Yes-Yes": 0.90}
    zorders= {"No-No": 1, "Yes-No": 2, "No-Yes": 2, "Yes-Yes": 3}

    # No-No → Yes系 → Yes-Yes の順に描画（重要なものを前面に）
    for key in ["No-No", "Yes-No", "No-Yes", "Yes-Yes"]:
        m = masks[key]
        if m.sum() == 0:
            continue
        ax.scatter(
            x[m], y[m],
            s=sizes[key], color=colors[key], alpha=alphas[key],
            edgecolors="none", zorder=zorders[key],
            rasterized=True,   # PDF のファイルサイズ削減
        )

    # KDE 等高線（全データ + Yes-Yes のみ）
    draw_kde(ax, x, y, "#444444",  levels=(0.25, 0.55, 0.80))
    m_yy = masks["Yes-Yes"]
    if m_yy.sum() >= 10:
        draw_kde(ax, x[m_yy], y[m_yy], C_YY, levels=(0.50,))

    # x = y の対角線（参照線）
    lim = [0.40, 1.02]
    ax.plot(lim, lim, lw=0.7, ls=":", color="#444444", zorder=0)

    # 軸範囲・ラベル
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel(cfg["x_label"])
    ax.set_ylabel(cfg["y_label"])
    ax.set_title(cfg["title"], pad=4)

    # パネルラベル (a), (b), (c)
    ax.text(0.04, 0.96, panel_label,
            transform=ax.transAxes,
            fontsize=9, fontweight="bold", va="top")

    # 件数注釈
    n_tot = len(df)
    n_yy  = int(masks["Yes-Yes"].sum())
    ax.text(0.97, 0.04,
            f"$n={n_tot:,}$\nYY={n_yy}",
            transform=ax.transAxes,
            fontsize=6.5, ha="right", va="bottom", color="#333333")

    # スパイン: 上・右は枠線のみ表示（ティック方向 in で代用）
    ax.spines["top"].set_linewidth(0.4)
    ax.spines["right"].set_linewidth(0.4)
    ax.spines["bottom"].set_linewidth(0.6)
    ax.spines["left"].set_linewidth(0.6)

    # ティック間隔
    ax.xaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.05))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.05))


# ── 共通凡例を作成 ────────────────────────────────────────────────────────
def make_legend_handles():
    specs = [
        ("No–No",   C_NN, 4,  0.60),
        ("Yes–No",  C_YN, 8,  0.90),
        ("No–Yes",  C_NY, 8,  0.90),
        ("Yes–Yes", C_YY, 12, 1.00),
    ]
    return [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=c, markersize=np.sqrt(s) * 1.4,
               alpha=a, label=f"$j_1$–$j_2$ = {lbl}")
        for lbl, c, s, a in specs
    ]


# ── メイン ────────────────────────────────────────────────────────────────
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with plt.rc_context(RC):
        # ダブルカラム幅（7.2 inch）、正方形パネル3枚
        fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.55),
                                 constrained_layout=True)

        labels = ["(a)", "(b)", "(c)"]
        for idx, (tnum, cfg) in enumerate(TYPES.items()):
            df = pd.read_csv(DATA_DIR / cfg["file"])
            draw_panel(axes[idx], df, cfg, labels[idx])

        # 共通凡例（図の下中央）
        handles = make_legend_handles()
        fig.legend(
            handles=handles,
            loc="lower center",
            ncol=4,
            bbox_to_anchor=(0.5, -0.12),
            title=r"Judgment ($j_1$ = edge 1, $j_2$ = edge 2)",
            title_fontsize=7,
            frameon=False,
        )

        # 保存
        for ext in ("png", "pdf"):
            out = OUTPUT_DIR / f"fig_triplet_scatter.{ext}"
            fig.savefig(out, dpi=300, bbox_inches="tight")
            print(f"保存: {out}")

        plt.close()


if __name__ == "__main__":
    main()
