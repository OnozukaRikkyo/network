---
name: network
description: USPTO D18クラス設計特許の引用ネットワーク構築・グラフ分析を行う。引用ペアJSONLを起点に有向グラフを構築し、トリプレット抽出・コサイン類似度付与までの一連のパイプラインを実行する場合に使う。ネットワーク統計・中心性・トリプレットパターン分析が必要な時にも使う。
allowed-tools: Read Write Bash
disable-model-invocation: false
context: fork
---

# 実験の起点：D18 引用ペア JSONL

## 入力ファイル

```
/mnt/eightthdd/uspto/class/D18/cited_image_pairs/{year}.jsonl
  year: 2007〜2022（16ファイル）
  総レコード数: 1,530 ペア
  総イベント数: 2,332 件（平均 1.52 イベント/ペア）
```

## レコード構造

```json
{
  "source": "D0550278",
  "target": "D0550759",
  "source_images": {
    "perspective": "/mnt/eightthdd/impact/images/2007/USD0550278-20070904-D00000.TIF"
  },
  "target_images": {
    "perspective": "/mnt/eightthdd/impact/images/2007/USD0550759-20070904-D00000.TIF"
  },
  "events": [
    {
      "patentApplicationNumber": "29666802",
      "officeActionDate": "2020-11-12T00:00:00",
      "officeActionCategory": "CTNF",
      "citationCategoryCode": "A",
      "examinerCitedReferenceIndicator": "True",
      "applicantCitedExaminerReferenceIndicator": "False",
      "workGroup": "2900-WG",
      "groupArtUnitNumber": "2921",
      "techCenter": "2900"
    }
  ]
}
```

## events フィールドの意味

`events` は **source と target が同一特許出願内で共引用された USPTO オフィスアクション記録の配列**。
1ペアが複数の出願で共引用されると複数イベントが記録される。

| フィールド | 内容 |
|---|---|
| `patentApplicationNumber` | 引用した出願番号 |
| `officeActionDate` | オフィスアクション発行日時 |
| `officeActionCategory` | `CTNF`（非最終拒絶）/ `CTFR`（最終拒絶） |
| `citationCategoryCode` | 引用カテゴリ（`A` = 米国デザイン特許） |
| `examinerCitedReferenceIndicator` | 審査官による引用か |
| `applicantCitedExaminerReferenceIndicator` | 出願人による引用か |
| `workGroup` / `groupArtUnitNumber` / `techCenter` | USPTO 審査部門情報 |

## イベント多重度の分布

| イベント数/ペア | 件数 | 割合 |
|---|---|---|
| 1 | 1,023 | 66.9% |
| 2 | 305 | 19.9% |
| 3 | 144 | 9.4% |
| 4以上 | 58 | 3.8%（最大15） |

## ネットワーク構築における位置づけ

```
cited_image_pairs/{year}.jsonl  ← ★ 実験の起点
  │  source / target → ノード（デザイン特許）
  │  events が存在する = 共引用関係 → エッジ
  │  events 数 → エッジ重みの候補
  ▼
networkx.Graph / DiGraph を構築
  ノード属性: patent_id, year
  エッジ属性: n_events, latest_officeActionDate,
             officeActionCategory, examinerCited
  ▼
グラフ分析（中心性・コミュニティ・PageRank 等）
```

全 1,530 件のレコードは `events` が必ず1件以上存在する（引用情報なしのレコードは存在しない）。

## 参照先

- 詳細な入出力マップ: `/home/sonozuka/network/CLAUDE.md`
- 上流スクリプト: `/home/sonozuka/design_similarity/extract_cited_image_pairs.py`
- 判定結合済み出力: `/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl`

---

# ネットワーク構築スクリプト: `build_network.py`

## 実行方法

```bash
cd /home/sonozuka/network
source venv/bin/activate
python3 build_network.py
```

## 有向グラフの定義

| 要素 | 定義 |
|---|---|
| ノード | デザイン特許ID（`D0xxxxxx` 形式）|
| エッジ方向 | `source → target`（D番号昇順 = 先行特許 → 後続特許）|
| エッジ重み | `events` 数（同ペアが複数出願で共引用された回数）|
| エッジ属性 | `year`, `latest_date`, `examiner_cited` |

## 出力ファイル

| ファイル | 内容 |
|---|---|
| `/home/sonozuka/network/output/d18_citation_network.png` | ネットワーク図（最大WCC + 高次数サブグラフ） |
| `/home/sonozuka/network/output/d18_degree_distribution.png` | in/out/total 次数分布ヒストグラム |

## 実測統計（2007〜2022 全年）

```
ノード数（特許数）    : 1,030
エッジ数（ペア数）    : 1,530
密度                 : 0.001444
平均クラスタ係数      : 0.5236

【ネットワーク数（連結成分）】
  弱連結成分 (WCC) 数 : 252
  強連結成分 (SCC) 数 : 1,030  ← 全ノードが独立（DAG的構造）
  最大 WCC ノード数   : 44 (4.3%)
  WCC サイズ上位5     : [44, 31, 24, 20, 20]
  孤立ノード数        : 0（全ノードが少なくとも1エッジを持つ）

【in-degree（被引用数）】
  min=0  max=21  mean=1.485  std=1.912  median=1.0
  上位: D0832343(21), D0827021(15), D0821490(14)

【out-degree（引用数）】
  min=0  max=13  mean=1.485  std=1.805  median=1.0
  上位: D0807426(13), D0808461(12), D0811474(11)

【エッジ重み（共引用イベント数）】
  min=1  max=15  mean=1.524  weight=1: 66.9%  weight≥2: 33.1%

【PageRank 上位3】
  1. D0775275  PR=0.007204  in=11
  2. D0832343  PR=0.006924  in=21
  3. D0772977  PR=0.004989  in=6
```

## 依存ライブラリ

```bash
pip install networkx matplotlib numpy scipy pandas
```

---

# パイプライン全体フロー

```
【外部データ（上流）】
/mnt/eightthdd/uspto/class/D18/cited_image_pairs/{year}.jsonl   ← 実験起点
/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl  ← 類似度ソース

        │                                   │
        ▼                                   │
 ┌─────────────────┐                        │
 │ build_network.py│                        │
 └────────┬────────┘                        │
          │                                 │
          ▼                                 │
 data/d18_citation_network.graphml  ◄───────┤ (グラフ構築)
 data/d18_citation_network.gexf             │
 data/d18_edges.csv                         │
 data/d18_nodes.csv                         │
 output/d18_citation_network.png            │
 output/d18_degree_distribution.png         │
          │                                 │
          ▼                                 │
 ┌──────────────────────┐                   │
 │ triplet_analysis.py  │                   │
 └──────────┬───────────┘                   │
            │                               │
            ▼                               │
 data/triplets_type1.csv                    │
 data/triplets_type2.csv                    │
 data/triplets_type3.csv                    │
            │                               │
            └───────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  enrich_triplets.py   │
            └───────────┬───────────┘
                        │
                        ▼
            data/triplets_type1_enriched.csv
            data/triplets_type2_enriched.csv
            data/triplets_type3_enriched.csv
```

---

# STEP 2: トリプレット抽出 `triplet_analysis.py`

## 実行方法

```bash
cd /home/sonozuka/network
source venv/bin/activate
python3 triplet_analysis.py
```

## 入力

| ファイル | フルパス | 形式 | 備考 |
|---|---|---|---|
| エッジリスト | `/home/sonozuka/network/data/d18_edges.csv` | CSV | `build_network.py` 出力 |

**入力スキーマ（使用列）:**

| 列 | 内容 |
|---|---|
| `source` | 先行特許ID（source < target、アルファベット順） |
| `target` | 後続特許ID |

## 出力

| ファイル | フルパス | 件数 |
|---|---|---|
| タイプ1 CSV | `/home/sonozuka/network/data/triplets_type1.csv` | 2,164件 |
| タイプ2 CSV | `/home/sonozuka/network/data/triplets_type2.csv` | 2,255件 |
| タイプ3 CSV | `/home/sonozuka/network/data/triplets_type3.csv` | 2,164件 |

**出力スキーマ（全タイプ共通）:**

| 列 | 内容 |
|---|---|
| `node_A` | 始端ノード（特許ID） |
| `node_B` | 中間ノード（特許ID） |
| `node_C` | 終端ノード（特許ID） |

## トリプレットの定義

| タイプ | パターン | 説明 | 除外条件 |
|---|---|---|---|
| タイプ1 | A → B → C | 連鎖（先行→中間→後続） | node_A == node_C |
| タイプ2 | A → B ← C | 収束（2つの先行→共通後続） | node_A >= node_C（対称性除去） |
| タイプ3 | A ← B ← C | 連鎖逆向き（後続→中間→先行） | node_A == node_C |

## 抽出結果

| タイプ | 件数 | 割合 |
|---|---|---|
| タイプ1 | 2,164 | 32.9% |
| タイプ2 | 2,255 | 34.3% |
| タイプ3 | 2,164 | 32.9% |
| **合計** | **6,583** | 100% |

---

# STEP 3: エッジ特徴量付与 `enrich_triplets.py`

コサイン類似度・LLM判定（Yes/No）・判断理由をトリプレットの各エッジに付与する。

## 実行方法

```bash
cd /home/sonozuka/network
source venv/bin/activate
python3 enrich_triplets.py
```

## 入力

| ファイル | フルパス | 形式 | 備考 |
|---|---|---|---|
| トリプレット タイプ1 | `/home/sonozuka/network/data/triplets_type1.csv` | CSV | `triplet_analysis.py` 出力 |
| トリプレット タイプ2 | `/home/sonozuka/network/data/triplets_type2.csv` | CSV | 同上 |
| トリプレット タイプ3 | `/home/sonozuka/network/data/triplets_type3.csv` | CSV | 同上 |
| エッジ特徴量ソース | `/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl` | JSONL | 1,530ペア、欠損なし |

**JSONL 使用フィールド:**

| フィールド | 型 | 内容 |
|---|---|---|
| `source` | str | 先行特許ID（source < target、アルファベット順） |
| `target` | str | 後続特許ID |
| `similarity` | float | コサイン類似度（0〜1） |
| `judgment` | str | LLM判定: `"Yes"` または `"No"` |
| `reason` | str | 判断理由（英語 1〜2文） |

**ルックアップキー正規化:** `(min(u, v), max(u, v))` で統一

## 出力

| ファイル | フルパス | 行数 | 列数 |
|---|---|---|---|
| タイプ1 enriched | `/home/sonozuka/network/data/triplets_type1_enriched.csv` | 2,164 | 9 |
| タイプ2 enriched | `/home/sonozuka/network/data/triplets_type2_enriched.csv` | 2,255 | 9 |
| タイプ3 enriched | `/home/sonozuka/network/data/triplets_type3_enriched.csv` | 2,164 | 9 |

**出力列構成:**

| タイプ | 列（順序） |
|---|---|
| タイプ1 | `node_A, node_B, node_C, sim_A_B, judgment_A_B, reason_A_B, sim_B_C, judgment_B_C, reason_B_C` |
| タイプ2 | `node_A, node_B, node_C, sim_A_B, judgment_A_B, reason_A_B, sim_C_B, judgment_C_B, reason_C_B` |
| タイプ3 | `node_A, node_B, node_C, sim_B_A, judgment_B_A, reason_B_A, sim_C_B, judgment_C_B, reason_C_B` |

**ヒット率: 100%（全 6,583 件、欠損 0 件）**

## エッジ特徴量統計

| タイプ | エッジ | sim mean | sim median | Yes率 | No率 |
|---|---|---|---|---|---|
| タイプ1 | A↔B | 0.8898 | 0.9202 | 15.7% | 84.3% |
| タイプ1 | B↔C | 0.8882 | 0.9139 | 14.5% | 85.5% |
| タイプ2 | A↔B | 0.8739 | 0.8929 | 12.0% | 88.0% |
| タイプ2 | C↔B | 0.8822 | 0.9106 | 12.1% | 87.9% |
| タイプ3 | B↔A | 0.8882 | 0.9139 | 14.5% | 85.5% |
| タイプ3 | C↔B | 0.8898 | 0.9202 | 15.7% | 84.3% |

---

# STEP 4: 散布図作成 `plot_triplets.py`

1タイプ1ファイル（PNG のみ）。物理学論文スタイル（PRL / Nature Physics 準拠）。

## 実行方法

```bash
cd /home/sonozuka/network
source venv/bin/activate
python3 plot_triplets.py
```

## 入力

| ファイル | フルパス |
|---|---|
| タイプ1 enriched | `/home/sonozuka/network/data/triplets_type1_enriched.csv` |
| タイプ2 enriched | `/home/sonozuka/network/data/triplets_type2_enriched.csv` |
| タイプ3 enriched | `/home/sonozuka/network/data/triplets_type3_enriched.csv` |

## 出力

| ファイル | フルパス | 内容 |
|---|---|---|
| タイプ1 散布図 | `/home/sonozuka/network/output/fig_triplet1_scatter.png` | 横: A→B、縦: B→C |
| タイプ2 散布図 | `/home/sonozuka/network/output/fig_triplet2_scatter.png` | 横: A→B、縦: C→B |
| タイプ3 散布図 | `/home/sonozuka/network/output/fig_triplet3_scatter.png` | 横: B→A、縦: C→B |

## 図スタイル仕様（PRL / Nature Physics 準拠）

| 設定 | 値 |
|---|---|
| 図サイズ | 3.5 × 3.5 inch（シングルカラム正方形）|
| 出力形式 | PNG 300 DPI のみ（PDF 不要）|
| フォント | Arial / Helvetica |
| フォントサイズ | 軸ラベル 14 pt・ティック 12 pt・ベース 13 pt |
| ティック方向 | 内向き（`direction='in'`）、4辺表示 |
| マイナーティック | 0.05 間隔 |
| スパイン | 4辺 0.7 pt 統一 |
| マーカー | 中抜き円（`facecolors='none'`）|
| マーカー色 | ネイビーブルー `#1a3a6b`（1色のみ）|
| マーカーサイズ | s=10（全タイプ共通）|
| タイトル | なし |
| 等高線 | なし |
| 凡例 | なし |
| 軸ラベル | 矢印表記（例: `Cosine similarity (A→B)`）|
| 対角参照線 | $x=y$ 点線（`ls=':'`、`color='#555555'`）|
| 軸範囲 | [0.38, 1.02] |
| ティック間隔（major）| 0.1 |

## matplotlib rcParams（主要設定）

```python
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
    "xtick.minor.visible": True,
    "ytick.minor.visible": True,
    "xtick.top":           True,
    "ytick.right":         True,
    "savefig.dpi":         300,
}
```

---

# STEP 5: ヒートマップ作成 `plot_heatmap.py`

両エッジの LLM 判定（Yes=1 / No=0）の 2×2 カウントヒートマップ。
3タイプ共通カラーバー 1本、セル内にカウント値を表示。

## 実行方法

```bash
cd /home/sonozuka/network
source venv/bin/activate
python3 plot_heatmap.py
```

## 入力

| ファイル | フルパス |
|---|---|
| タイプ1 enriched | `/home/sonozuka/network/data/triplets_type1_enriched.csv` |
| タイプ2 enriched | `/home/sonozuka/network/data/triplets_type2_enriched.csv` |
| タイプ3 enriched | `/home/sonozuka/network/data/triplets_type3_enriched.csv` |

## 出力

| ファイル | フルパス |
|---|---|
| ヒートマップ（3パネル） | `/home/sonozuka/network/output/fig_triplet_heatmap.png` |

## 図スタイル仕様

| 設定 | 値 |
|---|---|
| 図サイズ | 8.0 × 2.8 inch（3パネル横並び + 共通カラーバー）|
| カラーマップ | `Blues`（モノクロ印刷・色覚多様性対応）|
| 共通カラーバー | vmin=0、vmax=全タイプ最大カウント（1,818）|
| セル注釈 | カウント値 13 pt bold、背景濃度 > 55% で白文字・それ以下で黒文字 |
| 軸ラベル | 矢印表記（例: `Judgment (A→B)`）、14 pt |
| ティック | `direction='out'`、`length=0`（目盛り線なし）|
| ティックラベル | `"0"` / `"1"`（Yes/No 表記なし）|
| パネルラベル | なし |
| セル枠線 | `axvline`/`axhline` + スパイン を `color='black'`、`linewidth=2.0`、`zorder=10` で前面描画 |
| スパイン | 4辺 `linewidth=2.0`、`color='black'`、`zorder=10` |
| フォント | Arial / Helvetica、13/14 pt |

## カウント行列（実測値）

| | (0,0) No-No | (0,1) No-Yes | (1,0) Yes-No | (1,1) Yes-Yes |
|---|---|---|---|---|
| タイプ1 | 1,630 | 195 | 221 | 118 |
| タイプ2 | 1,818 | 167 | 165 | 105 |
| タイプ3 | 1,630 | 221 | 195 | 118 |

---

# パイプライン実行順序

```bash
cd /home/sonozuka/network
source venv/bin/activate

python3 build_network.py       # STEP 1: 有向グラフ構築・統計・可視化・グラフ保存
python3 triplet_analysis.py    # STEP 2: トリプレット抽出
python3 enrich_triplets.py     # STEP 3: コサイン類似度・LLM判定・理由を付与
python3 plot_triplets.py       # STEP 4: 散布図作成（1タイプ1PNG）
python3 plot_heatmap.py        # STEP 5: ヒートマップ（3パネル共通カラーバー）
```

# 全ファイル一覧

| ファイル | フルパス | 生成スクリプト |
|---|---|---|
| グラフ（GraphML） | `/home/sonozuka/network/data/d18_citation_network.graphml` | build_network.py |
| グラフ（GEXF） | `/home/sonozuka/network/data/d18_citation_network.gexf` | build_network.py |
| エッジリスト | `/home/sonozuka/network/data/d18_edges.csv` | build_network.py |
| ノード属性 | `/home/sonozuka/network/data/d18_nodes.csv` | build_network.py |
| ネットワーク図 | `/home/sonozuka/network/output/d18_citation_network.png` | build_network.py |
| 次数分布図 | `/home/sonozuka/network/output/d18_degree_distribution.png` | build_network.py |
| トリプレット タイプ1 | `/home/sonozuka/network/data/triplets_type1.csv` | triplet_analysis.py |
| トリプレット タイプ2 | `/home/sonozuka/network/data/triplets_type2.csv` | triplet_analysis.py |
| トリプレット タイプ3 | `/home/sonozuka/network/data/triplets_type3.csv` | triplet_analysis.py |
| タイプ1 enriched | `/home/sonozuka/network/data/triplets_type1_enriched.csv` | enrich_triplets.py |
| タイプ2 enriched | `/home/sonozuka/network/data/triplets_type2_enriched.csv` | enrich_triplets.py |
| タイプ3 enriched | `/home/sonozuka/network/data/triplets_type3_enriched.csv` | enrich_triplets.py |
| タイプ1 散布図 | `/home/sonozuka/network/output/fig_triplet1_scatter.png` | plot_triplets.py |
| タイプ2 散布図 | `/home/sonozuka/network/output/fig_triplet2_scatter.png` | plot_triplets.py |
| タイプ3 散布図 | `/home/sonozuka/network/output/fig_triplet3_scatter.png` | plot_triplets.py |
| ヒートマップ | `/home/sonozuka/network/output/fig_triplet_heatmap.png` | plot_heatmap.py |

# 詳細ドキュメント

| 内容 | ファイル |
|---|---|
| ネットワーク統計 | `/home/sonozuka/network/docs/network_stats.md` |
| トリプレット分析・類似度統計 | `/home/sonozuka/network/docs/triplet_analysis.md` |
| 入出力全体マップ・バイナリ仕様 | `/home/sonozuka/network/CLAUDE.md` |
