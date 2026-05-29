# コサイン類似度 CDF (`plot_sim_histogram.py`)

## 概要

D18 引用ペア全件のコサイン類似度の経験的累積分布関数（ECDF）を
Similar / Non-similar / All / Random の4線で可視化する。

引用のないランダムペアを基準線として加えることで、
「引用されたこと自体が視覚的類似度の高さと相関するか」を検証できる。

---

## 元スクリプトの誤りと修正

### 誤り1: タイプフィルタによる N= の過小計上

元スクリプト `design_similarity/vector/analysis/rank_analysis.py` の
`plot_sim_histogram()` は `--type perspective`（デフォルト）でフィルタして
実行するため、`all.jsonl` に収録された全 1,530 件のうち
`overview`（74件）と `front`（9件）の計 83 件が "All" から抜け落ちていた。

| 項目 | 元（誤） | 本スクリプト（正） |
|---|---|---|
| All N= | 1,447（perspective のみ） | **1,530**（全タイプ） |
| Similar N= | 196 | **227**（全タイプ） |
| タイプフィルタ | `type == "perspective"` | なし |

### 誤りの背景：1特許 = 1タイプ = 1画像

各特許には `fig_desc` の解析により **1つの画像タイプのみ**が割り当てられる
（`design_similarity/vector/doc/image_index.md` より）。

```
優先順: front > overview > perspective（フォールバック）
1特許 = 1タイプ = 1画像（D00000.TIF）のみ
```

よって1つの引用ペアに対して `all.jsonl` のレコードも1件のみ存在する
（perspective と overview 両方のレコードを同一ペアが持つことはない）。

`all.jsonl` の 1,530 件はすべて**異なるペア**であり、タイプ別内訳は以下のとおり：

| タイプ | 全件 | Yes | No | Unknown |
|---|---|---|---|---|
| perspective | 1,447 | 199 | 1,248 | 0 |
| overview | 74 | 26 | 48 | 0 |
| front | 9 | 2 | 7 | 0 |
| **合計** | **1,530** | **227** | **1,303** | **0** |

---

## スクリプト・実行方法

```
/home/sonozuka/network/plot_sim_histogram.py
```

```bash
cd /home/sonozuka/network
source venv/bin/activate
python3 plot_sim_histogram.py
```

---

## 入力

| ファイル | フルパス | 形式 | 用途 |
|---|---|---|---|
| 判定結合済み全件 | `/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl` | JSONL | 引用ペア（Similar/Non-similar/All）|
| L2正規化済みベクトル | `/mnt/eightthdd/uspto/class/D18/rank_index/perspective/vectors_l2norm.npy` | NumPy float32 (959, 2048) | Random ペアのコサイン類似度計算 |

JSONL 使用フィールド: `similarity`, `judgment`（`"Yes"` / `"No"` / `"Unknown"`）

---

## 出力

| ファイル | フルパス | DPI |
|---|---|---|
| 類似度 CDF | `/home/sonozuka/network/output/fig_sim_cdf.png` | 300 |

---

## Random ペアの実装

### 背景

`all.jsonl` の 1,530 件はすべて USPTO のオフィスアクション内で
共引用された**引用ペア**であり、未引用ペアはこのファイルに含まれない。
引用のないランダムペアと比較するために、別途コサイン類似度を計算する。

### コサイン類似度の計算

`rank_index/perspective/vectors_l2norm.npy` は **L2 正規化済み**ベクトルであるため、
内積（ドット積）がそのままコサイン類似度になる
（`design_similarity/vector/doc/build_rank_index.md` より）：

```
cosine_similarity(A, B) = A_norm · B_norm   （L2正規化済みなら成立）
```

全 C(959,2)=459,361 ペアの類似度を行列積で一括計算する：

```python
vecs = np.load("vectors_l2norm.npy")   # (959, 2048) float32, L2正規化済み
S    = vecs @ vecs.T                   # (959, 959) コサイン類似度行列
# 上三角（対角除く）→ 全 C(959,2) 一意ペア
rows, cols = np.triu_indices(959, k=1)
all_sims   = S[rows, cols]             # shape (459361,)
```

行列 S のサイズは 959×959×4 bytes ≈ 3.7 MB であり、メモリ・計算ともに問題ない。

### 乱数による 1,000 件の一様抽出（物理慣例）

物理分野では乱数の使い方に以下の慣例がある：

1. **アルゴリズム**: PCG64（Permuted Congruential Generator）
   - NumPy 1.17+ の `np.random.default_rng` がデフォルトで使用
   - 統計的品質が高く、周期が長い（2^128）
   - 旧 `np.random.seed` + `np.random.choice` より推奨

2. **固定シード**: 再現性確保のため論文・コードに必ず明記
   - ここでは `seed=42` を使用

3. **重複なし一様抽出** (`replace=False`):
   - 同一ペアを2度以上選ばない
   - 母集団（459,361件）から等確率で 1,000 件を選ぶ

```python
RANDOM_N    = 1000
RANDOM_SEED = 42

rng = np.random.default_rng(RANDOM_SEED)          # PCG64 初期化
idx = rng.choice(len(all_sims), size=RANDOM_N, replace=False)
rand_sims = all_sims[idx]                          # shape (1000,)
```

| 項目 | 値 |
|---|---|
| アルゴリズム | PCG64（`np.random.default_rng`、NumPy 1.17+ デフォルト）|
| シード | 42（固定・論文再現性のため必ず明記）|
| 抽出方法 | `rng.choice(459361, size=1000, replace=False)`（重複なし一様抽出）|
| 母集団 | 全 C(959,2)=459,361 ペアの類似度（上三角行列から抽出）|
| perspective 特許数 | 959 |
| 全組み合わせ数 | C(959,2) = 459,361 |

---

## 図の仕様（PRL / Nature Physics 準拠、SKILL.md 準拠）

| 設定 | 値 |
|---|---|
| 図サイズ | 3.5 × 3.5 inch（シングルカラム正方形）|
| フォント | Arial / Helvetica / DejaVu Sans |
| フォントサイズ | 軸ラベル 14pt・ティック 12pt・ベース 13pt |
| 縦軸 | ECDF = P(X ≤ x)、0〜1 |
| 横軸範囲 | [0.35, 1.02] |
| 縦軸範囲 | [−0.02, 1.05] |
| major tick 間隔（横）| 0.1 |
| major tick 間隔（縦）| 0.2 |
| ティック方向 | 内向き、4辺表示 |
| スパイン | 0.7pt |
| DPI | 300 |

### 系列仕様

| 系列 | 色 | 線種 | 線幅 | N | 意味 |
|---|---|---|---|---|---|
| Random | `#555555`（濃灰） | 点線 `:` | 1.0pt | 1,000 | perspective 未引用ランダムペア（基準線）|
| All | `#888888`（灰） | 実線 | 0.9pt | 1,530 | 全引用ペア（Similar+Non-similar）|
| Non-similar | `#d62728`（赤） | 破線 `--` | 1.2pt | 1,303 | LLM 非類似判定の引用ペア |
| Similar | `#2166ac`（青） | 実線 | 1.4pt | 227 | LLM 類似判定の引用ペア |

---

## 実測値・検証結果（2026-05-29）

### Random ペアの統計（seed=42）

| 統計量 | 値 |
|---|---|
| N（母集団） | 459,361 |
| N（サンプル） | 1,000 |
| min | 0.3624 |
| max | 0.9760 |
| mean | 0.7625 |
| median | 0.7775 |

### データ検証（all.jsonl の全件カウント）

| タイプ | 全件 | Yes | No | Unknown |
|---|---|---|---|---|
| perspective | 1,447 | 199 | 1,248 | 0 |
| overview | 74 | 26 | 48 | 0 |
| front | 9 | 2 | 7 | 0 |
| **合計** | **1,530** | **227** | **1,303** | **0** |

### 実装 vs 仕様 照合

| 項目 | 実装値 | 仕様 | 一致 |
|---|---|---|---|
| 入力: JSONL | `rank_judgments/cosine_numpy/all.jsonl` | 同左 | ✓ |
| 入力: ベクトル | `rank_index/perspective/vectors_l2norm.npy` | 同左 | ✓ |
| 出力ファイル | `output/fig_sim_cdf.png` | 同左 | ✓ |
| タイプフィルタ | なし | なし | ✓ |
| Unknown 除外 | `judgment != "Unknown"` | あり | ✓ |
| figsize | (3.5, 3.5) | 3.5 × 3.5 inch | ✓ |
| DPI | 300 | 300 | ✓ |
| Random 色 | `#555555` | `#555555` | ✓ |
| Random 線種 | 点線 `:` | 点線 | ✓ |
| Random N= | 1,000 | 1,000 | ✓ |
| Random seed | 42 | 42 | ✓ |
| Random アルゴリズム | PCG64 | PCG64 | ✓ |
| All 色 | `#888888` | `#888888` | ✓ |
| Non-similar 色 | `#d62728` | `#d62728` | ✓ |
| Similar 色 | `#2166ac` | `#2166ac` | ✓ |
| Non-similar 線種 | 破線 `--` | 破線 | ✓ |
| ティック方向 | `in`（4辺） | 内向き・4辺 | ✓ |
| 軸ラベルサイズ | 14pt | 14pt | ✓ |
| All N= | 1,530 | 1,530 | ✓ |
| Similar N= | 227 | 227 | ✓ |
| Non-similar N= | 1,303 | 1,303 | ✓ |

---

## 図の読み方

**4群の位置関係（左→右）**: Random < All ≈ Non-similar < Similar

| 系列 | 観察 |
|---|---|
| **Random（濃灰点線）** | 最も左 → 未引用ランダムペアは中央値 0.778 付近に分布。全引用群より明確に左にシフト |
| **All（灰実線）** | Random より右にシフト → 引用されたペアはランダムより視覚的類似度が高い |
| **Non-similar（赤破線）** | All とほぼ重なり、Random より右 → 非類似と判定されても引用ペアはランダムより高類似度 |
| **Similar（青実線）** | 最も右 → 類似判定ペアはコサイン類似度 ≥ 0.9 付近に集中 |

**解釈:**

1. 引用関係があるだけで視覚的類似度が上がる（Random < All）
2. LLM が類似と判定したペアはさらに際立って高類似度に集中する（Similar ≫ Non-similar）
3. コサイン類似度はベクトル空間での視覚的類似の判別に有効である
