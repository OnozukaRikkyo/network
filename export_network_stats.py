#!/usr/bin/env python3
"""
export_network_stats.py
D18 引用ネットワークの統計情報を CSV に出力する。

出力:
  data/network_summary.csv        -- 基本統計・次数・エッジ重み（key-value形式）
  data/network_pagerank.csv       -- PageRank 上位ノード一覧
  data/network_component_dist.csv -- サブグラフ（連結成分）サイズ分布
"""

import pathlib
import csv
import numpy as np
import networkx as nx

DATA_DIR = pathlib.Path("/home/sonozuka/network/data")


def compute_stats(G: nx.DiGraph) -> None:

    # ── 基本量 ────────────────────────────────────────────────────────────
    n_nodes  = G.number_of_nodes()
    n_edges  = G.number_of_edges()
    density  = nx.density(G)
    avg_clust = nx.average_clustering(G.to_undirected())

    # ── 次数 ──────────────────────────────────────────────────────────────
    in_deg  = np.array([d for _, d in G.in_degree()],  dtype=float)
    out_deg = np.array([d for _, d in G.out_degree()], dtype=float)
    tot_deg = np.array([d for _, d in G.degree()],     dtype=float)

    # ── エッジ重み ────────────────────────────────────────────────────────
    weights = np.array([d["weight"] for _, _, d in G.edges(data=True)], dtype=float)
    w1 = int(np.sum(weights == 1))

    # ── 連結成分 ──────────────────────────────────────────────────────────
    components = list(nx.weakly_connected_components(G))
    comp_sizes = sorted(len(c) for c in components)
    n_comp     = len(comp_sizes)
    scc_count  = nx.number_strongly_connected_components(G)
    isolated   = sum(1 for s in comp_sizes if s == 1)

    # ── PageRank ──────────────────────────────────────────────────────────
    pr = nx.pagerank(G, weight="weight")

    # ═══════════════════════════════════════════════════════════════════════
    # 1. network_summary.csv  (metric, value)
    # ═══════════════════════════════════════════════════════════════════════
    summary_rows = [
        ("metric", "value"),
        # 基本
        ("n_nodes",                   n_nodes),
        ("n_edges",                   n_edges),
        ("density",                   f"{density:.6f}"),
        ("avg_clustering_undirected", f"{avg_clust:.4f}"),
        # 連結成分
        ("n_components",              n_comp),
        ("n_scc",                     scc_count),
        ("max_component_size",        comp_sizes[-1]),
        ("min_component_size",        comp_sizes[0]),
        ("isolated_nodes",            isolated),
        # in-degree
        ("in_degree_min",    int(in_deg.min())),
        ("in_degree_max",    int(in_deg.max())),
        ("in_degree_mean",   f"{in_deg.mean():.4f}"),
        ("in_degree_std",    f"{in_deg.std():.4f}"),
        ("in_degree_median", f"{np.median(in_deg):.1f}"),
        # out-degree
        ("out_degree_min",    int(out_deg.min())),
        ("out_degree_max",    int(out_deg.max())),
        ("out_degree_mean",   f"{out_deg.mean():.4f}"),
        ("out_degree_std",    f"{out_deg.std():.4f}"),
        ("out_degree_median", f"{np.median(out_deg):.1f}"),
        # undirected degree
        ("degree_min",    int(tot_deg.min())),
        ("degree_max",    int(tot_deg.max())),
        ("degree_mean",   f"{tot_deg.mean():.4f}"),
        ("degree_std",    f"{tot_deg.std():.4f}"),
        ("degree_median", f"{np.median(tot_deg):.1f}"),
        # edge weight
        ("weight_min",         int(weights.min())),
        ("weight_max",         int(weights.max())),
        ("weight_mean",        f"{weights.mean():.4f}"),
        ("weight_std",         f"{weights.std():.4f}"),
        ("weight_eq1_count",   w1),
        ("weight_eq1_pct",     f"{w1 / n_edges * 100:.1f}"),
        ("weight_ge2_count",   n_edges - w1),
        ("weight_ge2_pct",     f"{(n_edges - w1) / n_edges * 100:.1f}"),
    ]

    out1 = DATA_DIR / "network_summary.csv"
    with open(out1, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(summary_rows)
    print(f"保存: {out1}")

    # ═══════════════════════════════════════════════════════════════════════
    # 2. network_pagerank.csv  (rank, node, pagerank, in_degree, out_degree)
    # ═══════════════════════════════════════════════════════════════════════
    top_pr = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:10]

    out2 = DATA_DIR / "network_pagerank.csv"
    with open(out2, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "node", "pagerank", "in_degree", "out_degree"])
        for i, (node, score) in enumerate(top_pr, 1):
            writer.writerow([
                i, node,
                f"{score:.6f}",
                G.in_degree(node),
                G.out_degree(node),
            ])
    print(f"保存: {out2}")

    # ═══════════════════════════════════════════════════════════════════════
    # 3. network_component_dist.csv  (n_nodes, n_graphs)
    # ═══════════════════════════════════════════════════════════════════════
    from collections import Counter
    size_counter = Counter(comp_sizes)

    out3 = DATA_DIR / "network_component_dist.csv"
    with open(out3, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["n_nodes", "n_graphs"])
        for size in sorted(size_counter):
            writer.writerow([size, size_counter[size]])
    print(f"保存: {out3}")

    # ── 確認出力 ──────────────────────────────────────────────────────────
    print(f"\n基本: nodes={n_nodes}, edges={n_edges}, components={n_comp}")
    print(f"次数 (undirected): mean={tot_deg.mean():.3f}, max={int(tot_deg.max())}")
    print(f"PageRank 1位: {top_pr[0][0]}  score={top_pr[0][1]:.6f}")


if __name__ == "__main__":
    G = nx.read_graphml(DATA_DIR / "d18_citation_network.graphml")
    compute_stats(G)
