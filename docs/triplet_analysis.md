---
title: D18 トリプレット分析
generated_by: triplet_analysis.py
date: 2026-05-29
---

# D18 トリプレット分析

有向グラフのエッジリストから、3ノードで構成されるパターン（トリプレット）を抽出した。

---

## 入出力

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/home/sonozuka/network/data/d18_edges.csv` | CSV（ユニークエッジ 1,530件） |
| 出力 | `/home/sonozuka/network/data/triplets_type1.csv` | CSV |
| 出力 | `/home/sonozuka/network/data/triplets_type2.csv` | CSV |
| 出力 | `/home/sonozuka/network/data/triplets_type3.csv` | CSV |

## 実行方法

```bash
cd /home/sonozuka/network
source venv/bin/activate
python3 triplet_analysis.py
```

---

## トリプレットの定義

### タイプ1: A → B → C（連鎖）

```
A ──► B ──► C
```

先行特許 A が中間特許 B と共引用され、さらに B が後続特許 C と共引用されるパターン。
AとCが一致するケース（自己ループ）は除外。

### タイプ2: A → B ← C（収束）

```
A ──► B ◄── C
```

異なる2つの先行特許 A・C が、同一の後続特許 B と共引用されるパターン。
A と C の対称性（A→B←C と C→B←A は同一）および A=C を `A < C` で除外。

### タイプ3: A ← B ← C（連鎖・逆向き）

```
A ◄── B ◄── C
```

タイプ1の逆向き。後続特許 C → 中間 B → 先行 A の連鎖。
タイプ1と構造は同一だが、ノード A・C の役割（先行/後続）が逆転している。
AとCが一致するケースは除外。

---

## 抽出結果

| タイプ | パターン | 件数 | 割合 |
|---|---|---|---|
| タイプ1 | A → B → C | 2,164 | 32.9% |
| タイプ2 | A → B ← C | 2,255 | 34.3% |
| タイプ3 | A ← B ← C | 2,164 | 32.9% |
| **合計** | | **6,583** | 100% |

---

## 考察

- **タイプ1とタイプ3の件数が同一（2,164件）**
  グラフの source/target が D番号昇順で正規化されているため（source < target）、
  連鎖パターンの逆向きを取っても対称的に同数になる。

- **タイプ2（収束）が最多（2,255件）**
  複数の先行デザインが同一の後続デザインと対比される「競合参照」パターンが
  連鎖パターンより若干多い。これはデザイン特許審査で
  「類似した複数の先行例をまとめて引用する」傾向を反映している可能性がある。

- **入力エッジ数（1,530）に対してトリプレット総数（6,583）は約4.3倍**
  ネットワーク密度（0.001444）が低い割に局所的な密集（クラスタ係数 0.524）があり、
  特定のハブノード周辺でトリプレットが集中していると考えられる。

---

## 出力 CSV スキーマ

全タイプ共通:

| 列 | 内容 |
|---|---|
| `node_A` | 始端ノード（特許ID） |
| `node_B` | 中間ノード（特許ID） |
| `node_C` | 終端ノード（特許ID） |

---

## エッジ特徴量付与（`enrich_triplets.py`）

コサイン類似度・LLM判定（Yes/No）・判断理由を各トリプレットのエッジに付与する。

### 入出力

| 種別 | フルパス | 備考 |
|---|---|---|
| 入力 | `/home/sonozuka/network/data/triplets_type1.csv` | triplet_analysis.py 出力 |
| 入力 | `/home/sonozuka/network/data/triplets_type2.csv` | 同上 |
| 入力 | `/home/sonozuka/network/data/triplets_type3.csv` | 同上 |
| 特徴量ソース | `/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl` | 1,530ペア |
| 出力 | `/home/sonozuka/network/data/triplets_type1_enriched.csv` | 2,164行 × 9列 |
| 出力 | `/home/sonozuka/network/data/triplets_type2_enriched.csv` | 2,255行 × 9列 |
| 出力 | `/home/sonozuka/network/data/triplets_type3_enriched.csv` | 2,164行 × 9列 |

ルックアップキーは `(min(u,v), max(u,v))` に正規化。全 6,583 件で欠損なし（ヒット率 100%）。

### 出力 CSV 列構成

| タイプ | 列（順序） |
|---|---|
| タイプ1 | `node_A, node_B, node_C, sim_A_B, judgment_A_B, reason_A_B, sim_B_C, judgment_B_C, reason_B_C` |
| タイプ2 | `node_A, node_B, node_C, sim_A_B, judgment_A_B, reason_A_B, sim_C_B, judgment_C_B, reason_C_B` |
| タイプ3 | `node_A, node_B, node_C, sim_B_A, judgment_B_A, reason_B_A, sim_C_B, judgment_C_B, reason_C_B` |

### コサイン類似度統計

#### タイプ1: A → B → C（連鎖）  2,164 件

| エッジ | min | max | mean | std | median |
|---|---|---|---|---|---|
| sim_A_B | 0.4395 | 0.9967 | 0.8898 | 0.0997 | 0.9202 |
| sim_B_C | 0.4389 | 0.9967 | 0.8882 | 0.0906 | 0.9139 |

#### タイプ2: A → B ← C（収束）  2,255 件

| エッジ | min | max | mean | std | median |
|---|---|---|---|---|---|
| sim_A_B | 0.4265 | 0.9953 | 0.8739 | 0.0958 | 0.8929 |
| sim_C_B | 0.4265 | 0.9967 | 0.8822 | 0.0928 | 0.9106 |

#### タイプ3: A ← B ← C（連鎖逆）  2,164 件

| エッジ | min | max | mean | std | median |
|---|---|---|---|---|---|
| sim_B_A | 0.4389 | 0.9967 | 0.8882 | 0.0906 | 0.9139 |
| sim_C_B | 0.4395 | 0.9967 | 0.8898 | 0.0997 | 0.9202 |

### LLM 判定統計（judgment: Yes/No）

#### タイプ1: A → B → C（連鎖）

| エッジ | Yes | No | Yes率 |
|---|---|---|---|
| judgment_A_B | 339 | 1,825 | 15.7% |
| judgment_B_C | 313 | 1,851 | 14.5% |

#### タイプ2: A → B ← C（収束）

| エッジ | Yes | No | Yes率 |
|---|---|---|---|
| judgment_A_B | 270 | 1,985 | 12.0% |
| judgment_C_B | 272 | 1,983 | 12.1% |

#### タイプ3: A ← B ← C（連鎖逆）

| エッジ | Yes | No | Yes率 |
|---|---|---|---|
| judgment_B_A | 313 | 1,851 | 14.5% |
| judgment_C_B | 339 | 1,825 | 15.7% |

### 観察

- **類似度の対称性**: タイプ1とタイプ3は同一エッジセットの逆参照のため、sim/judgment が完全対称。
- **タイプ2の類似度・Yes率が最も低い**: 収束パターン（A→B←C）は連鎖パターンより mean sim が低く（0.87台）、Yes率も 12% 前後にとどまる。競合する複数先行例が引用される場合は必ずしも高類似度ではない。
- **全タイプで median sim > 0.89**: D18クラス内の引用ペアは全体的にコサイン類似度が高い。
- **judgment の Yes率は全体で約 14.8%**: 元の引用ペアデータ（227/1,530 = 14.8%）と一致しており、トリプレット展開後もバランスが保持されている。

---

## 散布図（`plot_triplets.py`）

### 概要

各タイプについて、2エッジのコサイン類似度の散布図を物理学論文スタイルで出力する。

- **横軸**: 第1エッジのコサイン類似度
- **縦軸**: 第2エッジのコサイン類似度
- **色**: 両エッジの judgment 組み合わせ（4カテゴリ）
- **等高線**: ガウシアン KDE による密度等高線（全体 + Yes-Yes のみ）
- **点線**: 対角線 $s_1 = s_2$（参照線）

### 実行方法

```bash
cd /home/sonozuka/network
source venv/bin/activate
python3 plot_triplets.py
```

### 入出力

| 種別 | フルパス |
|---|---|
| 入力 | `/home/sonozuka/network/data/triplets_type1_enriched.csv` |
| 入力 | `/home/sonozuka/network/data/triplets_type2_enriched.csv` |
| 入力 | `/home/sonozuka/network/data/triplets_type3_enriched.csv` |
| 出力 | `/home/sonozuka/network/output/fig_triplet1_scatter.png` |
| 出力 | `/home/sonozuka/network/output/fig_triplet2_scatter.png` |
| 出力 | `/home/sonozuka/network/output/fig_triplet3_scatter.png` |

### 図スタイル仕様（PRL / Nature Physics 準拠）

| 設定項目 | 値 |
|---|---|
| 図サイズ | 3.5 × 3.5 inch（シングルカラム正方形）× 1タイプ1ファイル |
| フォント | Arial / Helvetica, 14 pt（軸ラベル）/ 12 pt（ティック）/ 13 pt（ベース） |
| DPI | 300 PNG のみ（PDF 不要） |
| ティック方向 | 内向き（`direction='in'`）、4辺表示 |
| マイナーティック | 0.05 間隔で表示 |
| スパイン | 4辺 0.7 pt 統一 |
| マーカー | 中抜き円（`facecolors='none'`）、ネイビー `#1a3a6b`、同サイズ（s=10）|
| タイトル | なし |
| 等高線 | なし |
| 軸ラベル | 矢印表記（例: `Cosine similarity (A→B)`）|
| 対角参照線 | $x = y$ 点線 |

### マーカー仕様

| 設定 | 値 |
|---|---|
| 色 | ネイビーブルー `#1a3a6b`（1色のみ、judgment 区別なし）|
| 形状 | 中抜き円（`facecolors='none'`）|
| サイズ | s=10（全タイプ共通）|
| 透過度 | alpha=0.45 |
| 凡例 | なし |

---

## 判定ヒートマップ（`plot_heatmap.py`）

両エッジの LLM 判定（Yes=1 / No=0）の 2×2 カウントヒートマップ。
3タイプを1図にまとめ、共通カラーバー 1本で比較可能にした。

### 入出力

| 種別 | フルパス |
|---|---|
| 入力 | `/home/sonozuka/network/data/triplets_type{1,2,3}_enriched.csv` |
| 出力 | `/home/sonozuka/network/output/fig_triplet_heatmap.png` |

### 図スタイル仕様

| 設定 | 値 |
|---|---|
| 図サイズ | 8.0 × 2.8 inch |
| カラーマップ | `Blues`（モノクロ印刷・色覚多様性対応）|
| 共通カラーバー | vmin=0、vmax=1,818（全タイプ最大値）|
| セル注釈 | カウント値 13 pt bold、背景濃度 > 55% で白文字・それ以下で黒文字 |
| 軸ラベル | 矢印表記（例: `Judgment (A→B)`）、14 pt |
| ティックラベル | `"0"` / `"1"`（Yes/No 表記なし）|
| ティック | `direction='out'`、`length=0` |
| パネルラベル | なし |
| セル枠線 | `axvline`/`axhline` + スパイン、`color='black'`、`linewidth=2.0`、`zorder=10` |

### カウント行列（実測値）

| タイプ | (0,0) No–No | (0,1) No–Yes | (1,0) Yes–No | (1,1) Yes–Yes |
|---|---|---|---|---|
| タイプ1 | 1,630 | 195 | 221 | **118** |
| タイプ2 | 1,818 | 167 | 165 | **105** |
| タイプ3 | 1,630 | 221 | 195 | **118** |

## 次のステップ

- 両エッジが共に Yes のトリプレット（強一致三角形）の抽出・詳細分析
- ハブノード（高次数）がどのタイプに多く出現するかの分析

## 参照

- グラフ統計: [`docs/network_stats.md`](network_stats.md)
- グラフ構築スクリプト: [`build_network.py`](../build_network.py)
- 入力データ仕様: [`CLAUDE.md`](../CLAUDE.md)