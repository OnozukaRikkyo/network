#!/usr/bin/env python3
"""
plot_degree_combined.py
In-degree / Out-degree / Degree (undirected) の3分布を1軸に重ねて描画する。

スタイル: PRL / Nature Physics 準拠
入力: /home/sonozuka/network/data/d18_citation_network.graphml
出力: /home/sonozuka/network/output/fig_degree_combined.png  (300 DPI)
"""

import pathlib
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

DATA_DIR   = pathlib.Path("/home/sonozuka/network/data")
OUTPUT_DIR = pathlib.Path("/home/sonozuka/network/output")

RC = {
    "font.family":         "sans-serif",
    "font.sans-serif":     ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size":           13,
    "axes.labelsize":      14,
    "xtick.labelsize":     12,
    "ytick.labelsize":     12,
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

SERIES = [
    dict(label="$N = 1{,}530$", color="#2e7d32"),
]

FILL_ALPHA  = 0.40   # 塗りつぶし透過度
EDGE_ALPHA  = 0.85   # 枠線透過度
EDGE_LW     = 1.2


def main(G: nx.DiGraph) -> None:

    in_deg  = np.array([d for _, d in G.in_degree()],  dtype=int)
    out_deg = np.array([d for _, d in G.out_degree()], dtype=int)
    tot_deg = np.array([d for _, d in G.degree()],     dtype=int)

    arrays = [tot_deg]
    max_deg = max(a.max() for a in arrays)
    bins = np.arange(max_deg + 2) - 0.5   # 整数値の中央に bin 境界

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(3.5, 3.5))

        for arr, cfg in zip(arrays, SERIES):
            ax.hist(
                arr,
                bins=bins,
                density=False,
                histtype="bar",
                color=cfg["color"],
                alpha=FILL_ALPHA,
                edgecolor=cfg["color"],
                linewidth=EDGE_LW,
                label=cfg["label"],
            )

        ax.set_xlabel("Degree $k$ (Undirected)")
        ax.set_ylabel("Count")
        ax.set_xlim(-0.5, max_deg + 0.5)

        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=8))
        ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))

        for spine in ax.spines.values():
            spine.set_linewidth(0.7)

        ax.text(0.97, 0.97, "$N = 1{,}530$", fontsize=11,
                ha="right", va="top", transform=ax.transAxes)

        fig.tight_layout()
        out = OUTPUT_DIR / "fig_degree_combined.png"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)

    print(f"保存: {out}")
    for arr, cfg in zip(arrays, SERIES):
        print(f"  {cfg['label']:25s}: mean={arr.mean():.2f}  max={arr.max()}")


def plot_subgraph_node_counts(G: nx.DiGraph) -> None:
    # 有向グラフの弱連結成分（辺の向きを無視した連結サブグラフ）を取得
    components = list(nx.weakly_connected_components(G))

    # サブグラフごとのノード数
    sizes = np.array(sorted(len(c) for c in components), dtype=int)
    n_graphs = len(sizes)
    max_size = sizes.max()
    bins = np.arange(max_size + 2) - 0.5

    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(3.5, 3.5))

        ax.hist(
            sizes,
            bins=bins,
            density=False,
            histtype="bar",
            color="#1a3a6b",
            alpha=FILL_ALPHA,
            edgecolor="#1a3a6b",
            linewidth=EDGE_LW,
        )

        ax.set_xlabel("Number of nodes")
        ax.set_ylabel("Number of graphs")
        ax.set_xlim(0.5, max_size + 0.5)

        ax.xaxis.set_major_locator(ticker.MultipleLocator(5))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(2))

        for spine in ax.spines.values():
            spine.set_linewidth(0.7)

        ax.text(0.97, 0.97, f"$N = {n_graphs}$", fontsize=11,
                ha="right", va="top", transform=ax.transAxes)

        fig.tight_layout()
        out = OUTPUT_DIR / "fig_subgraph_size.png"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        plt.close(fig)

    print(f"保存: {out}")
    print(f"  サブグラフ数={n_graphs}  最大ノード数={max_size}  最小ノード数={sizes.min()}")
    from collections import Counter
    print(f"  ノード数別グラフ数: {dict(sorted(Counter(sizes.tolist()).items()))}")


if __name__ == "__main__":
    G = nx.read_graphml(DATA_DIR / "d18_citation_network.graphml")
    main(G)
    plot_subgraph_node_counts(G)
