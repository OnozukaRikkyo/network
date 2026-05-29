#!/usr/bin/env python3
"""
build_network.py
D18クラス引用ペアJSONLから有向グラフを構築し、統計情報と可視化を出力する。

有向グラフの方向定義:
  source → target（D番号昇順 = 先行デザイン → 後続デザイン）
  D特許番号は通番で発行されるため、番号が小さい = 先行公報。
  共引用された文脈で先行デザインが後続デザインと対比されたと解釈する。

入力:  /mnt/eightthdd/uspto/class/D18/cited_image_pairs/{year}.jsonl
出力:  /home/sonozuka/network/output/d18_citation_network.png
       /home/sonozuka/network/output/d18_degree_distribution.png
"""

import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import networkx as nx
import numpy as np

DATA_DIR   = pathlib.Path("/mnt/eightthdd/uspto/class/D18/cited_image_pairs")
OUTPUT_DIR = pathlib.Path("/home/sonozuka/network/output")
DATA_OUT   = pathlib.Path("/home/sonozuka/network/data")
YEARS      = range(2007, 2023)


# ── データ読み込み ──────────────────────────────────────────────────────

def load_pairs() -> list[dict]:
    records = []
    for year in YEARS:
        path = DATA_DIR / f"{year}.jsonl"
        if not path.exists():
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    rec["_year"] = year
                    records.append(rec)
    print(f"読み込み: {len(records)} レコード（{DATA_DIR}）")
    return records


# ── グラフ構築 ──────────────────────────────────────────────────────────

def build_directed_graph(records: list[dict]) -> nx.DiGraph:
    """
    ノード: デザイン特許ID（D0xxxxxx 形式）
    エッジ: source → target（D番号昇順）
    エッジ属性:
      weight       : 共引用イベント数（重複エッジは加算）
      year         : 初出年
      examiner_cited: いずれかのイベントで審査官引用か
    """
    G = nx.DiGraph()

    for rec in records:
        src    = rec["source"]
        tgt    = rec["target"]
        events = rec.get("events", [])
        year   = rec["_year"]

        n_ev = len(events)
        latest_date = max(
            (e.get("officeActionDate", "") for e in events), default=""
        )
        examiner_cited = any(
            e.get("examinerCitedReferenceIndicator") == "True" for e in events
        )

        if G.has_edge(src, tgt):
            G[src][tgt]["weight"]        += n_ev
            G[src][tgt]["n_events"]      += n_ev
        else:
            G.add_edge(
                src, tgt,
                weight=n_ev,
                n_events=n_ev,
                year=year,
                latest_date=latest_date,
                examiner_cited=examiner_cited,
            )

    return G


# ── 統計出力 ────────────────────────────────────────────────────────────

def print_stats(G: nx.DiGraph) -> None:
    sep = "=" * 60

    # ── 基本情報
    n   = G.number_of_nodes()
    m   = G.number_of_edges()
    print(sep)
    print("  D18 引用ネットワーク 統計情報（有向グラフ）")
    print(sep)
    print(f"\n【基本情報】")
    print(f"  ノード数 (特許数)     : {n:,}")
    print(f"  エッジ数 (ペア数)     : {m:,}")
    print(f"  密度                 : {nx.density(G):.6f}")
    print(f"  平均クラスタ係数      : {nx.average_clustering(G.to_undirected()):.4f}")

    # ── 連結成分（ネットワーク数）
    wcc_list = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
    scc_list = sorted(nx.strongly_connected_components(G), key=len, reverse=True)
    wcc_sizes = [len(c) for c in wcc_list]
    scc_sizes = [len(c) for c in scc_list]

    print(f"\n【ネットワーク（連結成分）数】")
    print(f"  弱連結成分 (WCC) 数  : {len(wcc_list):,}")
    print(f"  強連結成分 (SCC) 数  : {len(scc_list):,}")
    print(f"  最大 WCC ノード数    : {wcc_sizes[0]:,}  ({wcc_sizes[0]/n*100:.1f}%)")
    print(f"  最大 SCC ノード数    : {scc_sizes[0]:,}  ({scc_sizes[0]/n*100:.1f}%)")
    print(f"  WCC サイズ上位5      : {wcc_sizes[:5]}")
    print(f"  孤立ノード数         : {sum(1 for s in wcc_sizes if s == 1):,}")

    # ── 次数統計
    in_deg  = np.array([d for _, d in G.in_degree()])
    out_deg = np.array([d for _, d in G.out_degree()])
    tot_deg = np.array([d for _, d in G.degree()])
    nodes   = list(G.nodes())

    for label, arr in [
        ("in-degree  (被引用数)", in_deg),
        ("out-degree (引用数)  ", out_deg),
        ("degree（無向換算）   ", tot_deg),
    ]:
        top5 = sorted(zip(nodes, arr.tolist()), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n【{label}】")
        print(f"  min={arr.min()}  max={arr.max()}  "
              f"mean={arr.mean():.3f}  std={arr.std():.3f}  "
              f"median={np.median(arr):.1f}")
        print(f"  上位5: {[(n, int(v)) for n, v in top5]}")

    # ── エッジ重み統計
    weights = np.array([d["weight"] for _, _, d in G.edges(data=True)])
    print(f"\n【エッジ重み（共引用イベント数）】")
    print(f"  min={weights.min()}  max={weights.max()}  "
          f"mean={weights.mean():.3f}  std={weights.std():.3f}")
    print(f"  weight=1  : {(weights==1).sum():,}  ({(weights==1).mean()*100:.1f}%)")
    print(f"  weight>=2 : {(weights>=2).sum():,}  ({(weights>=2).mean()*100:.1f}%)")

    # ── PageRank 上位10
    pr = nx.pagerank(G, weight="weight")
    top10 = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"\n【PageRank 上位10】")
    for i, (node, score) in enumerate(top10, 1):
        print(f"  {i:2d}. {node}  PR={score:.6f}"
              f"  in={G.in_degree(node)}  out={G.out_degree(node)}")

    print(f"\n{sep}")


# ── 可視化 ──────────────────────────────────────────────────────────────

def _draw_graph(ax, G: nx.DiGraph, title: str, layout_k: float = 0.4) -> None:
    pr    = nx.pagerank(G, weight="weight")
    deg   = dict(G.degree())
    sizes = [max(15, deg[n] * 25) for n in G.nodes()]
    colors = [pr[n] for n in G.nodes()]
    weights = [G[u][v]["weight"] for u, v in G.edges()]
    max_w   = max(weights) if weights else 1
    widths  = [0.3 + 1.8 * (w / max_w) for w in weights]

    pos = nx.spring_layout(G, seed=42, k=layout_k)

    sc = nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_size=sizes, node_color=colors,
        cmap=plt.cm.plasma, alpha=0.85, vmin=0,
    )
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        width=widths, alpha=0.35, edge_color="#555555",
        arrows=True, arrowsize=7, arrowstyle="->",
        connectionstyle="arc3,rad=0.08",
    )
    # 上位ノードにラベル
    top_nodes = sorted(deg, key=deg.get, reverse=True)[:12]
    nx.draw_networkx_labels(
        G, pos, {n: n for n in top_nodes}, ax=ax, font_size=5.5
    )
    plt.colorbar(sc, ax=ax, label="PageRank", shrink=0.55, pad=0.02)
    ax.set_title(
        f"{title}\n{G.number_of_nodes()} nodes, {G.number_of_edges()} edges",
        fontsize=10,
    )
    ax.axis("off")


def visualize_network(G: nx.DiGraph) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 図1: ネットワーク可視化（全体 + 高次数サブグラフ）
    fig, axes = plt.subplots(1, 2, figsize=(22, 10))
    fig.suptitle(
        "D18 Design Patent Co-Citation Network (Directed)\n"
        "Edge: source→target (ascending D-number = earlier→later patent)",
        fontsize=12, fontweight="bold",
    )

    # 左: 最大WCCを表示
    largest_wcc = max(nx.weakly_connected_components(G), key=len)
    G_wcc = G.subgraph(largest_wcc).copy()
    _draw_graph(axes[0], G_wcc, "Largest Weakly Connected Component", layout_k=0.35)

    # 右: 高次数上位80ノードのサブグラフ
    top_n = min(80, G.number_of_nodes())
    top_nodes = sorted(dict(G.degree()), key=lambda n: G.degree(n), reverse=True)[:top_n]
    G_top = G.subgraph(top_nodes).copy()
    _draw_graph(axes[1], G_top, f"Top-{top_n} High-Degree Nodes", layout_k=0.55)

    plt.tight_layout()
    out1 = OUTPUT_DIR / "d18_citation_network.png"
    plt.savefig(out1, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"保存: {out1}")

    # ── 図2: 次数分布
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("D18 Citation Network — Degree Distributions", fontsize=12, fontweight="bold")

    in_deg  = [d for _, d in G.in_degree()]
    out_deg = [d for _, d in G.out_degree()]
    tot_deg = [d for _, d in G.degree()]

    for ax, data, label, color in [
        (axes[0], in_deg,  "In-Degree",       "steelblue"),
        (axes[1], out_deg, "Out-Degree",       "tomato"),
        (axes[2], tot_deg, "Degree (undirected)", "seagreen"),
    ]:
        data = np.array(data)
        bins = np.arange(data.max() + 2) - 0.5
        ax.hist(data, bins=bins, color=color, alpha=0.75, edgecolor="white", linewidth=0.4)
        ax.set_xlabel(label, fontsize=10)
        ax.set_ylabel("Count", fontsize=10)
        ax.set_title(
            f"{label}\nmean={data.mean():.2f}  max={data.max()}",
            fontsize=10,
        )
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax.grid(axis="y", alpha=0.4)

    plt.tight_layout()
    out2 = OUTPUT_DIR / "d18_degree_distribution.png"
    plt.savefig(out2, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"保存: {out2}")


# ── グラフ保存 ──────────────────────────────────────────────────────────

def save_graph(G: nx.DiGraph) -> None:
    """
    グラフを複数フォーマットで data/ に保存する。

    graphml : 分析ツール間の標準形式（NetworkX / igraph / Gephi 共通）
    gexf    : Gephi 専用。動的グラフ・リッチ属性対応
    edges.csv: エッジリスト CSV（汎用）
    nodes.csv: ノード属性 CSV（汎用）
    """
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    pr = nx.pagerank(G, weight="weight")

    # ノード属性を付与
    for node in G.nodes():
        G.nodes[node]["in_degree"]  = G.in_degree(node)
        G.nodes[node]["out_degree"] = G.out_degree(node)
        G.nodes[node]["degree"]     = G.degree(node)
        G.nodes[node]["pagerank"]   = round(pr[node], 8)

    # GraphML（主力：igraph / NetworkX / Gephi 全対応）
    p1 = DATA_OUT / "d18_citation_network.graphml"
    nx.write_graphml(G, str(p1))
    print(f"保存: {p1}")

    # GEXF（Gephi 可視化用）
    p2 = DATA_OUT / "d18_citation_network.gexf"
    nx.write_gexf(G, str(p2))
    print(f"保存: {p2}")

    # エッジリスト CSV
    import csv
    p3 = DATA_OUT / "d18_edges.csv"
    with open(p3, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", "weight", "n_events",
                    "year", "latest_date", "examiner_cited"])
        for u, v, d in G.edges(data=True):
            w.writerow([u, v, d["weight"], d["n_events"],
                        d["year"], d["latest_date"], d["examiner_cited"]])
    print(f"保存: {p3}")

    # ノード属性 CSV
    p4 = DATA_OUT / "d18_nodes.csv"
    with open(p4, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node_id", "in_degree", "out_degree", "degree", "pagerank"])
        for node in G.nodes():
            nd = G.nodes[node]
            w.writerow([node, nd["in_degree"], nd["out_degree"],
                        nd["degree"], nd["pagerank"]])
    print(f"保存: {p4}")


# ── メイン ──────────────────────────────────────────────────────────────

def main():
    records = load_pairs()
    G       = build_directed_graph(records)
    print_stats(G)
    print("\nグラフファイルを保存中...")
    save_graph(G)
    print("\nネットワーク図を生成中...")
    visualize_network(G)
    print("\n完了。")


if __name__ == "__main__":
    main()
