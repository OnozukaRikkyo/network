---
title: D18 引用ネットワーク 統計情報
generated_by: build_network.py
date: 2026-05-29
---

# D18 引用ネットワーク 統計情報

生成スクリプト: `/home/sonozuka/network/build_network.py`
入力データ: `/mnt/eightthdd/uspto/class/D18/cited_image_pairs/{year}.jsonl`（2007〜2022）

---

## 基本情報

| 指標 | 値 |
|---|---|
| ノード数（特許数） | 1,030 |
| エッジ数（引用ペア数） | 1,530 |
| 密度 | 0.001444 |
| 平均クラスタ係数（無向換算） | 0.5236 |

---

## ネットワーク数（連結成分）

| 指標 | 値 | 備考 |
|---|---|---|
| 弱連結成分（WCC）数 | 252 | 実質的な「サブネットワーク」の数 |
| 強連結成分（SCC）数 | 1,030 | 全ノードが独立 → DAG的構造 |
| 最大 WCC ノード数 | 44 | 全体の 4.3% |
| WCC サイズ上位5 | [44, 31, 24, 20, 20] | |
| 孤立ノード数 | 0 | 全ノードが少なくとも1エッジを持つ |

**解釈:**
- WCC が 252 あるため、ネットワークは多数の独立したサブグループに分かれている。
- SCC が全ノード数と等しい（= 1,030）ことから、有向グラフ上で「相互到達可能なサイクル」は存在しない。エッジは一方向のみ（DAG的）。

---

## 次数統計

### in-degree（被引用数）

| 指標 | 値 |
|---|---|
| min | 0 |
| max | 21 |
| mean | 1.485 |
| std | 1.912 |
| median | 1.0 |

上位5ノード:

| ノード | in-degree |
|---|---|
| D0832343 | 21 |
| D0827021 | 15 |
| D0821490 | 14 |
| D0832342 | 12 |
| D0775275 | 11 |

### out-degree（引用数）

| 指標 | 値 |
|---|---|
| min | 0 |
| max | 13 |
| mean | 1.485 |
| std | 1.805 |
| median | 1.0 |

上位5ノード:

| ノード | out-degree |
|---|---|
| D0807426 | 13 |
| D0808461 | 12 |
| D0811474 | 11 |
| D0809594 | 10 |
| D0812683 | 10 |

### degree（無向換算）

| 指標 | 値 |
|---|---|
| min | 1 |
| max | 21 |
| mean | 2.971 |
| std | 2.589 |
| median | 2.0 |

上位5ノード:

| ノード | degree |
|---|---|
| D0832343 | 21 |
| D0821490 | 20 |
| D0827021 | 19 |
| D0811474 | 15 |
| D0826321 | 14 |

---

## エッジ重み（共引用イベント数）

| 指標 | 値 |
|---|---|
| min | 1 |
| max | 15 |
| mean | 1.524 |
| std | 0.948 |
| weight = 1 | 1,023 件（66.9%） |
| weight ≥ 2 | 507 件（33.1%） |

---

## PageRank 上位10

| 順位 | ノード | PageRank | in-degree | out-degree |
|---|---|---|---|---|
| 1 | D0775275 | 0.007204 | 11 | 0 |
| 2 | D0832343 | 0.006924 | 21 | 0 |
| 3 | D0772977 | 0.004989 | 6 | 0 |
| 4 | D0695337 | 0.004828 | 10 | 0 |
| 5 | D0798949 | 0.004748 | 11 | 0 |
| 6 | D0827021 | 0.004340 | 15 | 4 |
| 7 | D0803310 | 0.004086 | 8 | 0 |
| 8 | D0970606 | 0.003901 | 9 | 0 |
| 9 | D0818533 | 0.003683 | 10 | 2 |
| 10 | D0832916 | 0.003451 | 5 | 0 |

---

## 可視化

| ファイル | 内容 |
|---|---|
| [`output/d18_citation_network.png`](../output/d18_citation_network.png) | ネットワーク図（左: 最大WCC、右: 高次数トップ80） |
| [`output/d18_degree_distribution.png`](../output/d18_degree_distribution.png) | in / out / total 次数分布ヒストグラム |

---

## グラフデータファイル（次分析への入力）

保存先: `/home/sonozuka/network/data/`

| ファイル | 形式 | 用途 |
|---|---|---|
| [`data/d18_citation_network.graphml`](../data/d18_citation_network.graphml) | GraphML | **主力**。NetworkX / igraph / Gephi 共通読み込み可 |
| [`data/d18_citation_network.gexf`](../data/d18_citation_network.gexf) | GEXF | Gephi での可視化・探索 |
| [`data/d18_edges.csv`](../data/d18_edges.csv) | CSV | エッジリスト（汎用・pandas 読み込み可） |
| [`data/d18_nodes.csv`](../data/d18_nodes.csv) | CSV | ノード属性（in/out/degree, PageRank） |

### GraphML の読み込み方法

```python
import networkx as nx

G = nx.read_graphml("data/d18_citation_network.graphml")
print(nx.info(G))

# ノード属性の確認
print(G.nodes["D0832343"])
# → {'in_degree': 21, 'out_degree': 0, 'degree': 21, 'pagerank': 0.006924}

# エッジ属性の確認
for u, v, d in list(G.edges(data=True))[:3]:
    print(u, "->", v, d)
```

### Edge CSV の読み込み方法

```python
import pandas as pd

edges = pd.read_csv("data/d18_edges.csv")
nodes = pd.read_csv("data/d18_nodes.csv")
```

### GEXF（Gephi）の読み込み方法

```python
G = nx.read_gexf("data/d18_citation_network.gexf")
```

---

## エッジ属性一覧

| 属性 | 型 | 内容 |
|---|---|---|
| `weight` | int | 共引用イベント数（グラフ分析の重みに使用） |
| `n_events` | int | `weight` と同値（明示的な別名） |
| `year` | int | 初出年（JSONL ファイル年） |
| `latest_date` | str | 最新オフィスアクション日時 |
| `examiner_cited` | bool | いずれかのイベントで審査官引用か |

## ノード属性一覧

| 属性 | 型 | 内容 |
|---|---|---|
| `in_degree` | int | 被引用数（後続特許から参照された回数） |
| `out_degree` | int | 引用数（先行特許を参照した回数） |
| `degree` | int | 無向次数 |
| `pagerank` | float | PageRank スコア（重み付き） |
