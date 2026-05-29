# ネットワーク分析プロジェクト

## プロジェクト概要

USPTO デザイン特許の引用ネットワーク・グラフ分析パイプライン。

- **データ**: USPTO特許コーパス、引用ペア画像類似度判定済みデータ（2007〜2022）
- **使用ライブラリ**: networkx, pandas, scipy, matplotlib, numpy

## 禁止事項

- 実験結果の JSONL・CSV を上書きしない（必ず別ファイルで保存）
- `/mnt/eightthdd/` 以下のデータを直接編集しない

## 検証基準（成功基準）

グラフ構築が完了した時：
- ノード数・エッジ数がログに記録されていること
- 孤立ノードの割合が確認できること
- 主要指標（次数分布・PageRank上位10件）が出力されること

---

# 上流パイプライン 入出力マップ（design_similarity プロジェクト）

## ストレージ全体構造

```
/mnt/eightthdd/uspto/
  ├── json/{year}.json                              ← 生データ（引用JSON）
  ├── data/{year}.csv                               ← 生データ（特許属性CSV）
  ├── _image_index.pkl                              ← STEP 2a キャッシュ
  ├── edge_list/{year}.csv                          ← STEP 1 出力
  ├── edge_list_with_class/{year}.csv               ← STEP 2c 出力
  ├── cited_image_pairs/{year}.jsonl                ← STEP 2a 出力
  ├── cited_image_vectors/{type}/                   ← GPU生成ベクトル（全クラス）
  ├── qwen_similarity_results/{year}.jsonl          ← STEP 3 出力（qwen）
  ├── similarity_results/{year}.jsonl               ← STEP 3 出力（gemini）
  ├── yes_pair/
  │   ├── qwen_yes_pairs/{year}.jsonl               ← STEP 4 出力
  │   ├── qwen_yes_image_pair/                      ← STEP 4 出力（PNG）
  │   └── _patent_index.pkl
  └── class/{CLASS}/
      ├── cited_image_pairs/{year}.jsonl            ← STEP V1 出力
      ├── cited_image_vectors/{type}/               ← STEP V2 出力
      ├── rank_index/{type}/                        ← STEP V3 出力
      ├── rank_results/{sim_func}/{year}.jsonl      ← STEP V4 出力
      └── rank_judgments/{sim_func}/all.jsonl       ← STEP V5 出力

/mnt/eightthdd/impact/images/{year}/USD*.TIF        ← 特許画像

/home/sonozuka/design_similarity/
  ├── ergm_input/                                   ← STEP 2d 出力
  ├── output/                                       ← STEP 5–6 出力
  ├── debug/image/                                  ← STEP 3 デバッグ画像
  ├── log/error/                                    ← エラーログ
  ├── vector/output/{CLASS}/{sim_func}/             ← ランク分析出力
  ├── vector/output/{CLASS}/{sim_func}/reasoning/   ← 推論パイプライン出力
  └── graph/output/{CLASS}/                         ← グラフ分析出力
```

---

## STEP 1: 引用グラフ構築 (`build_edge_list.py`)

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/json/{year}.json` | JSON（patent_id → 引用レコード） |
| 入力 | `/mnt/eightthdd/uspto/data/{year}.csv` | CSV（id, title, date, class, file_names 等） |
| 出力 | `/mnt/eightthdd/uspto/edge_list/{year}.csv` | CSV |

**出力列**: `source, target, patentApplicationNumber, officeActionDate, officeActionCategory, citationCategoryCode, examinerCitedReferenceIndicator, applicantCitedExaminerReferenceIndicator, workGroup, groupArtUnitNumber, techCenter`
- エッジ定義: 同一 `patentApplicationNumber` 内で共引用された特許ペア
- `source < target`（アルファベット正規化済み）

---

## STEP 2a: 引用画像ペア抽出 (`extract_cited_image_pairs.py`)

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/edge_list/{year}.csv` | CSV（STEP 1出力） |
| 入力 | `/mnt/eightthdd/uspto/data/{year}.csv` | CSV（file_names, fig_desc 参照） |
| キャッシュ | `/mnt/eightthdd/uspto/_image_index.pkl` | Pickle `{patent_id_int: {image_type: path}}` |
| 出力 | `/mnt/eightthdd/uspto/cited_image_pairs/{year}.jsonl` | JSONL（1行1ペア） |

**出力スキーマ**:
```json
{
  "source": "D0535736",
  "target": "D0537156",
  "source_images": {"perspective": "/mnt/eightthdd/impact/images/2007/USD0535736-20070123-D00000.TIF"},
  "target_images": {"perspective": "/mnt/eightthdd/impact/images/2007/USD0537156-20070220-D00000.TIF"},
  "events": [{"patentApplicationNumber": "...", "officeActionDate": "...", ...}]
}
```

---

## STEP 2b: 次数分布可視化 (`plot_indegree.py`) ※オプション

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/edge_list/{year}.csv` | CSV |
| 出力 | `indegree_pdf.png` / `indegree_ccdf.png` | PNG（log-log スケール） |

---

## STEP 2c: デザイン分類付与 (`add_class_to_edge_list.py`) ※オプション

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/edge_list/{year}.csv` | CSV |
| 入力 | `/mnt/eightthdd/uspto/data/{year}.csv` | CSV |
| キャッシュ | `/mnt/eightthdd/uspto/edge_list_with_class/_class_index.pkl` | Pickle |
| 出力 | `/mnt/eightthdd/uspto/edge_list_with_class/{year}.csv` | CSV（+4列） |

**追加列**: `source_class`（例: D14）, `source_class_name`, `target_class`, `target_class_name`

---

## STEP 2d: ERGM入力生成 (`build_ergm_input.py`) ※オプション

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/edge_list/{year}.csv` | CSV |
| 入力 | `/mnt/eightthdd/uspto/data/{year}.csv` | CSV |
| キャッシュ | `ergm_input/_patent_attr_cache.pkl` | Pickle `{patent_id: {all_classes}}` |
| 出力 | `ergm_input/arc_list.txt` | テキスト（EstimNetDirected用エッジリスト） |
| 出力 | `ergm_input/attributes.txt` | TSV（patent_id, D1…D99, diversity_score） |
| 出力 | `ergm_input/class_sim_binary.npy` | NumPy bool (N×N) |
| 出力 | `ergm_input/class_sim_jaccard.npy` | NumPy float32 (N×N)（Jaccard類似度） |
| 出力 | `ergm_input/model.cfg` | EstimNetDirected 設定テンプレート |

---

## STEP 3: 視覚的類似度判定 (`judge_cited_pairs.py`)

| 種別 | フルパス | 形式 | 条件 |
|---|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/cited_image_pairs/{year}.jsonl` | JSONL（STEP 2a出力） | |
| 参照画像 | `/mnt/eightthdd/impact/images/{year}/USD*.TIF` | TIF | source_images/target_images のパスを参照 |
| 出力（qwen） | `/mnt/eightthdd/uspto/qwen_similarity_results/{year}.jsonl` | JSONL | BACKEND="qwen" |
| 出力（gemini） | `/mnt/eightthdd/uspto/similarity_results/{year}.jsonl` | JSONL | BACKEND="gemini" |
| デバッグ画像 | `/home/sonozuka/design_similarity/debug/image/{source}__{target}__{type}.png` | PNG | DEBUG=True |
| エラーログ | `/home/sonozuka/design_similarity/log/error/error_YYYYMMDD.log` | テキスト | |

**出力追加フィールド**: `image_type_used`（front > overview > perspective）, `similarity`（"Yes"/"No"）, `confidence`（1〜5）, `reason`（英語）, `error`（エラー時のみ）

---

## STEP 4: Yes ペア抽出 (`extract_yes_pairs.py`)

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/qwen_similarity_results/*.jsonl` | JSONL（STEP 3出力） |
| 入力 | `/mnt/eightthdd/uspto/data/*.csv` | CSV |
| キャッシュ | `/mnt/eightthdd/uspto/yes_pair/_patent_index.pkl` | Pickle |
| 出力 | `/mnt/eightthdd/uspto/yes_pair/qwen_yes_pairs/{year}.jsonl` | JSONL（similarity=="Yes"のみ） |
| 出力 | `/mnt/eightthdd/uspto/yes_pair/qwen_yes_image_pair/` | PNG（対比較画像） |

---

## STEP V1: クラスフィルタリング (`vector/filter_pairs_by_class.py`)

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/cited_image_pairs/{year}.jsonl` | JSONL |
| 入力 | `/mnt/eightthdd/uspto/edge_list_with_class/{year}.csv` | CSV |
| 出力 | `/mnt/eightthdd/uspto/class/{CLASS}/cited_image_pairs/{year}.jsonl` | JSONL |

フィルタ条件: `source_class == CLASS AND target_class == CLASS`

---

## STEP V2: クラスベクトル生成 (`vector/build_class_vectors.py`)

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/class/{CLASS}/cited_image_pairs/{year}.jsonl` | JSONL |
| 入力 | `/mnt/eightthdd/uspto/cited_image_vectors/{type}/` | NumPy（事前生成済み） |
| 出力 | `/mnt/eightthdd/uspto/class/{CLASS}/cited_image_vectors/{type}/patent_ids_{year}.npy` | NumPy int64 (N,) |
| 出力 | `/mnt/eightthdd/uspto/class/{CLASS}/cited_image_vectors/{type}/vectors_{year}.npy` | NumPy float32 (N, 2048) |
| 出力 | `/mnt/eightthdd/uspto/class/{CLASS}/cited_image_vectors/{type}/file_paths_{year}.txt` | テキスト（N行） |

---

## STEP V3: ランクインデックス構築 (`vector/build_rank_index.py`)

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/class/{CLASS}/cited_image_vectors/{type}/` | NumPy（年別） |
| 出力 | `/mnt/eightthdd/uspto/class/{CLASS}/rank_index/{type}/patent_ids.npy` | NumPy int64 (N,)（全年統合・重複除去） |
| 出力 | `/mnt/eightthdd/uspto/class/{CLASS}/rank_index/{type}/vectors_l2norm.npy` | NumPy float32 (N, 2048)（L2正規化済み） |
| 出力 | `/mnt/eightthdd/uspto/class/{CLASS}/rank_index/{type}/file_paths.txt` | テキスト（N行） |

---

## STEP V4: ベクトルランク検索 (`vector/compute_ranks.py`)

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/class/{CLASS}/cited_image_pairs/{year}.jsonl` | JSONL |
| 入力 | `/mnt/eightthdd/uspto/class/{CLASS}/rank_index/{type}/` | NumPy |
| 出力 | `/mnt/eightthdd/uspto/class/{CLASS}/rank_results/{sim_func}/{year}.jsonl` | JSONL |

**出力スキーマ**:
```json
{
  "source": "D0550278", "target": "D0550759", "type": "perspective",
  "rank": 5, "n_candidates": 958, "similarity": 0.873421,
  "source_image": "/mnt/eightthdd/impact/images/2007/USD0550278-20070123-D00000.TIF",
  "target_image": "/mnt/eightthdd/impact/images/2007/USD0550759-20070220-D00000.TIF"
}
```

類似度バックエンド: `cosine_numpy`（デフォルト）/ `cosine_faiss`

---

## STEP V5: 判定結合 (`vector/join_judgments.py`)

| 種別 | フルパス | 形式 |
|---|---|---|
| 入力 | `/mnt/eightthdd/uspto/class/{CLASS}/rank_results/{sim_func}/{year}.jsonl` | JSONL |
| 入力 | `/mnt/eightthdd/uspto/qwen_similarity_results/{year}.jsonl` | JSONL |
| 出力 | `/mnt/eightthdd/uspto/class/{CLASS}/rank_judgments/{sim_func}/all.jsonl` | JSONL（全年・全タイプ統合） |

**結合スキーマ**: `rank`, `similarity`（コサイン値）, `judgment`（"Yes"/"No"/"Unknown"）, `confidence`, `reason`, `source_image`, `target_image`

**D18 判定状況（2026-05-24 時点）**:
- 2007〜2019: 判定完了
- 2020: 部分完了（3,581/55,765 件）
- 2021〜2022: 未判定（judgment="Unknown"）

---

## 分析ステップ（D18 実パス）

| スクリプト | 入力（フルパス） | 出力（フルパス） |
|---|---|---|
| `vector/analysis/rank_analysis.py` | `/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl` | `/home/sonozuka/design_similarity/vector/output/D18/cosine_numpy/rank_ccdf_{type}.png` 等 |
| `graph/graph_analysis.py` | `/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl` | `/home/sonozuka/design_similarity/graph/output/D18/triadic_scored.jsonl` |
| `graph/extract_high_sim_triads.py` | `/home/sonozuka/design_similarity/graph/output/D18/triadic_scored.jsonl`<br>`/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl` | `/home/sonozuka/design_similarity/graph/output/D18/high_sim_triads/overview.png`<br>`/home/sonozuka/design_similarity/graph/output/D18/high_sim_triads/triad_{rank}.png`<br>`/home/sonozuka/design_similarity/graph/output/D18/high_sim_triads/triad_summary.csv` |
| `graph/verify/discord_analysis.py` | `triadic_scored.jsonl` | `/home/sonozuka/design_similarity/graph/output/D18/verify/fp.csv`, `fn.csv` |
| `analyze_ergm.py` | `ergm_input/` + `qwen_similarity_results/` | `output/priority1〜4_*.png`, `analysis_summary.csv` |
| `visualize_ergm_network.py` | `ergm_input/` | `output/fig1〜7_*.png`（300 DPI）, `ergm_statistics.csv` |
| `analysis/d18_network_stats.py` | `/mnt/eightthdd/uspto/all_pair/qwen_all_pairs/*.jsonl` | コンソール出力のみ（D18フィルタ後の統計） |
| `export_pipeline_counts.py` | `/mnt/eightthdd/uspto/class/D18/rank_index/perspective/patent_ids.npy`<br>`/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl`<br>`output/diagonal_summary.csv` | `output/pipeline_counts.csv` |

## 推論パイプライン（`vector/reasoning/`、D18 実パス）

| スクリプト | 入力 | 出力 |
|---|---|---|
| `extract_pilot.py` | `/home/sonozuka/design_similarity/vector/output/D18/cosine_numpy/high_sim_perspective_0950_judged.csv` | `vector/output/D18/cosine_numpy/reasoning/pilot_24.csv`<br>`reasoning/pilot_strata.csv` |
| `patent_rationale_pms.py` | `high_sim_*_judged.csv` | `vector/output/D18/cosine_numpy/reasoning/pms_results.csv`（M1/M2/M3/PMS） |
| `patent_visual_probes.py --module m5` | pilot CSV | `vector/output/D18/cosine_numpy/reasoning/m5_scores.csv` |
| `patent_visual_probes.py --module baseline` | pilot CSV | `vector/output/D18/cosine_numpy/reasoning/baseline_b.csv` |
| `merge_results.py` | 各モジュール出力 | `vector/output/D18/cosine_numpy/reasoning/unified_results.csv` |
| `analyze_results.py` | `unified_results.csv` | `vector/output/D18/cosine_numpy/reasoning/analysis_summary.txt`, `fig_*.png` |

---

## D18 クラス抽出の仕組み

D18（"Printing & Office Machinery"）は `data/{year}.csv` の `class` 列から正規表現で判定されます。

```python
# add_class_to_edge_list.py の extract_main_class()
m = re.match(r"D(\d+)", first)      # "D18xx..." にマッチ
two = int(digits[:2])               # 先頭2桁を取得
if 10 <= two <= 34: return f"D{two}" # → "D18"
```

- 複数クラス記載の場合は先頭1件を使用
- 有効クラス: D1〜D34 および D99

**D18 規模（2007〜2022 全年合計）**:

| 種別 | 件数 |
|---|---|
| D18-D18 引用ペア総数 | 1,530 ペア |
| perspective タイプ | 1,447 件（94.6%） |
| overview タイプ | 74 件（4.8%） |
| front タイプ | 9 件（0.6%） |
| ユニーク特許数（rank_index/perspective） | 959 件 |
| 3クリーク（三角形）数 | 1,593 件 |

---

## ステップ間の主要データフロー（D18 抽出を含む）

```
json/{year}.json ──┐
data/{year}.csv ───┴─► edge_list/{year}.csv (STEP1)
                            │
                    ┌───────┴────────────────────────────┐
                    ▼                                    ▼
        cited_image_pairs/{year}.jsonl (2a)   edge_list_with_class/{year}.csv (2c)
                    │                          ※ data/{year}.csv の class列を解析
          ┌─────────┤                          ※ D18xx → "D18" に正規化
          ▼         ▼                                    │
  judge_cited_pairs  filter_pairs_by_class ─────────────┘
          │          (--class D18)
          │          source_class=="D18" AND target_class=="D18"
          ▼                    ▼
  qwen_similarity_results/   class/D18/cited_image_pairs/{year}.jsonl  ◄── D18抽出点
          │                          │
          ├──► extract_yes_pairs     build_class_vectors (V2)
          │                          │
          │                   class/D18/cited_image_vectors/{type}/
          │                          │
          │                   build_rank_index (V3)
          │                          │
          │                   class/D18/rank_index/{type}/
          │                          │
          │                   compute_ranks (V4)
          │                          │
          │                   class/D18/rank_results/cosine_numpy/{year}.jsonl
          │                          │
          └─────────────────► join_judgments (V5)
                                      │
                          class/D18/rank_judgments/cosine_numpy/all.jsonl
                                      │
                    ┌─────────────────┼─────────────────────┐
                    ▼                 ▼                     ▼
             rank_analysis      graph_analysis        d18_network_stats
                    │                 │                     │
      vector/output/D18/        graph/output/D18/      コンソール出力
      cosine_numpy/*.png        triadic_scored.jsonl
                    │                 │
              reasoning/       extract_high_sim_triads
              pipeline                │
                              graph/output/D18/
                              high_sim_triads/
```

---

# バイナリ・インデックスファイル仕様

## NumPy .npy ファイル一覧

| ファイル | パス | dtype | shape | 内容 |
|---|---|---|---|---|
| `vectors_{year}.npy` | `class/D18/cited_image_vectors/{type}/` | float32 | (N, D) | 年別生埋め込みベクトル（Qwen3-VL-Embedding-2B出力） |
| `patent_ids_{year}.npy` | `class/D18/cited_image_vectors/{type}/` | int64 | (N,) | 年別特許ID整数（行インデックスと1対1対応） |
| `vectors_l2norm.npy` | `class/D18/rank_index/{type}/` | float32 | (N, D) | 全年統合・重複除去・L2正規化済みベクトル |
| `patent_ids.npy` | `class/D18/rank_index/{type}/` | int64 | (N,) | 全年統合・重複除去済み特許ID（先頭出現を保持） |
| `class_sim_binary.npy` | `ergm_input/` | bool | (N, N) | クラス共有の有無（対角=False） |
| `class_sim_jaccard.npy` | `ergm_input/` | float32 | (N, N) | クラスJaccard類似度（対角=0） |

**特許ID整数エンコード規則:**
```python
int("D543613".lstrip("D")) + 10_000_000_000  # → 10000543613
```

---

## STEP V2: `vectors_{year}.npy` / `patent_ids_{year}.npy`

年別の生ベクトル。`build_class_vectors.py` が書き込み、`build_rank_index.py` が読み込む中間ファイル。

```python
# 書き込み（build_class_vectors.py）
vecs = np.concatenate(result_vecs, axis=0).astype(np.float32)
np.save("vectors_{year}.npy", vecs)

pat_ids = np.array(result_ids, dtype=np.int64)
np.save("patent_ids_{year}.npy", pat_ids)

# 読み込み（build_rank_index.py）
ids = np.load("patent_ids_{year}.npy")
vecs = np.load("vectors_{year}.npy")
```

---

## STEP V3: `vectors_l2norm.npy` / `patent_ids.npy`（ランクインデックス）

全年統合・重複除去・L2正規化済み。コサイン類似度検索の本体。

```python
# 書き込み（build_rank_index.py）
vectors = np.concatenate(all_vecs, axis=0).astype(np.float32)

# 重複除去（先頭年の出現を保持）
_, first_idx = np.unique(patent_ids, return_index=True)
patent_ids = patent_ids[first_idx]
vectors    = vectors[first_idx]

# L2正規化（ゼロベクトル対策あり）
norms = np.linalg.norm(vectors, axis=1, keepdims=True)
norms = np.where(norms == 0, 1.0, norms)
vectors = (vectors / norms).astype(np.float32)

np.save("vectors_l2norm.npy", vectors)
np.save("patent_ids.npy", patent_ids)

# 読み込み・使用（compute_ranks.py）
ids  = np.load("patent_ids.npy")
vecs = np.load("vectors_l2norm.npy")

# patent_id → 行インデックス の逆引き辞書を作成
id2row = {int(pid): i for i, pid in enumerate(ids)}

# コサイン類似度（ドット積）でランク計算
query_vec = vecs[id2row[source_id]]           # shape (D,)
sims = vecs @ query_vec                        # shape (N,)  BLAS dgemv
sims[id2row[source_id]] = -2.0                # self除外
rank = int(np.sum(sims > sims[id2row[target_id]])) + 1
```

---

## ERGM用: `class_sim_binary.npy` / `class_sim_jaccard.npy`

EstimNetDirected に渡すペア属性行列。メモリマップ（memmap）でチャンク生成。

```python
# class_sim_binary.npy（bool, N×N）
# [i,j] = True  ←→  patents i,j が1つ以上のDクラスを共有
inter = cls_vec_i16 @ cls_vec_i16.T   # クラスベクトルの内積
binary = (inter > 0)
np.fill_diagonal(binary, False)        # 対角=False

# class_sim_jaccard.npy（float32, N×N）
# [i,j] = |classes(i) ∩ classes(j)| / |classes(i) ∪ classes(j)|
union  = n_cls[:, None] + n_cls[None, :] - inter
jaccard = np.where(union > 0, inter / union, 0.0).astype(np.float32)
np.fill_diagonal(jaccard, 0.0)

# 読み込み
binary  = np.load("class_sim_binary.npy")   # mmap_mode="r" 推奨
jaccard = np.load("class_sim_jaccard.npy")
```

---

## Pickle キャッシュファイル一覧

| ファイル | フルパス | 構造 | キー | 値 |
|---|---|---|---|---|
| `_image_index.pkl` | `/mnt/eightthdd/uspto/_image_index.pkl` | `dict[int, dict[str,str]]` | 特許ID整数 | `{"perspective": "/path/to.TIF", ...}` |
| `_class_index.pkl` | `/mnt/eightthdd/uspto/edge_list_with_class/_class_index.pkl` | `dict[str, str]` | 特許ID文字列 | 主クラスコード（例: `"D18"`） |
| `_patent_attr_cache.pkl` | `ergm_input/_patent_attr_cache.pkl` | `dict[str, dict]` | 特許ID文字列 | `{"classes": set, "primary": str, "date": str}` |
| `_patent_index.pkl` | `/mnt/eightthdd/uspto/yes_pair/_patent_index.pkl` | `dict[str, dict]` | 特許ID文字列 | `{"title": str, "class": str, "date": str, "year": str}` |

**共通の読み書きパターン:**
```python
# 書き込み（初回のみ、protocol=HIGHEST_PROTOCOL で高速化）
with open(cache_path, "wb") as f:
    pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)

# 読み込み（キャッシュヒット時）
with open(cache_path, "rb") as f:
    index = pickle.load(f)
```

再構築が必要な場合は各スクリプトの `--rebuild` フラグを使用。

---

### `_image_index.pkl` の詳細

`image_index.py` が `data/{year}.csv` の `file_names`・`fig_desc` 列を解析して構築。

```python
# 画像タイプ判定ロジック（detect_image_type）
if re.search(r"perspective", desc, re.I):   → "perspective"
elif re.search(r"front (view|elevation...)", desc, re.I): → "front"
else:                                        → "overview"

# ファイルパスは file_names の先頭（D00000.TIF）を使用
image_path = f"/mnt/eightthdd/impact/images/{year}/{filename}"
```

---

### `_class_index.pkl` の詳細

`add_class_to_edge_list.py` の `extract_main_class()` が解析。

```python
# 複数クラスは先頭1件を使用
first = class_str.split(",")[0].strip()

# 2桁優先ルール: D10-D34, D99 → 2桁; D1-D9 → 1桁
m = re.match(r"D(\d+)", first)
two = int(digits[:2])
if 10 <= two <= 34 or two == 99:
    return f"D{two}"    # "D18xx..." → "D18"
```

---

## D18 インデックスファイル実パスまとめ

```
/mnt/eightthdd/uspto/class/D18/
├── cited_image_vectors/
│   ├── perspective/
│   │   ├── patent_ids_{year}.npy   dtype=int64  shape=(N,)
│   │   ├── vectors_{year}.npy      dtype=float32 shape=(N,D)
│   │   └── file_paths_{year}.txt   N行
│   ├── front/       （同構造）
│   └── overview/    （同構造）
└── rank_index/
    ├── perspective/
    │   ├── patent_ids.npy          dtype=int64  shape=(959,)   ← 全年統合・重複除去
    │   ├── vectors_l2norm.npy      dtype=float32 shape=(959,D) ← L2正規化済み
    │   └── file_paths.txt          959行
    ├── front/        shape=(12,)
    └── overview/     shape=(59,)
```

---

# Claude Code 高度活用ガイド（研究・コンピュータ実験向け）

研究の「複雑な入出力関係」という状況には、**コンテキストエンジニアリング**という考え方が最も有効です。単発プロンプトの工夫ではなく、実験環境全体を設計するアプローチです。

---

## 研究ワークフローに必須のコマンド

### 基本操作

| コマンド / キー | 機能 | 研究での用途 |
|---|---|---|
| `Shift+Tab` | Plan Mode に切り替え | 実験設計・アルゴリズム選定 |
| `Shift+Tab`（再押し） | Auto-Accept Mode | 大量のコード生成を一気に実行 |
| `Ctrl+G` | エディタで長い指示を編集 | 複雑な実験仕様の入力 |
| `@filename.py` | ファイルをコンテキストに注入 | 実験スクリプトを直接参照 |
| `Esc+Esc` | チェックポイントを取り消し | 誤った実験方向をロールバック |
| `/compact` | 会話を圧縮（コンテキスト節約） | 長時間セッションで必須 |
| `/cost` | トークン使用量確認 | API コスト管理 |

### スラッシュコマンド

| コマンド | 機能 |
|---|---|
| `/btw` | メインコンテキストを汚さずクイック質問 |
| `/clear` | 新しい実験タスク開始時にリセット |
| `/memory` | `CLAUDE.md` を直接編集 |
| `/review` | 実験コードのレビューを依頼 |

---

## 高度テクニック

### 1. 成功基準で指示する（Plan Mode）

```
# 悪い例
「ERGMのパラメータ推定を実装して」

# 良い例
「ERGMの推定が完了した時、AICが baseline より低くなること、
 かつ収束診断のMCMC traceが安定していること を成功基準とする。
 この基準を満たす実装を提案して」
```

`think harder` を加えると複雑な問題の解析精度が上がります。

### 2. Hooks で実験の品質を自動保証

`.claude/settings.json` に設定することで、コード変更後に自動で品質チェックが走ります。

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "command": "python -m pytest tests/ -q || true",
      "description": "コード変更後に自動テスト実行"
    }],
    "Stop": [{
      "command": "python validate_experiment.py",
      "description": "Claude完了時に実験出力を自動検証"
    }]
  }
}
```

Stop Hook は「検証基準を満たすまで自律的に反復」させることができます。

### 3. Subagents で並列仮説検証

```
「以下の3つの類似度計算手法を並列で実装・評価してください:
 - Subagent A: コサイン類似度ベース
 - Subagent B: グラフ距離ベース (NetworkX)
 - Subagent C: 情報幾何学的アプローチ（Fisher metric）
 各エージェントは同じテストセットで評価しPR を作成してください」
```

### 4. Task Diary でセッション横断の知識を蓄積

セッション終了前に以下を実行すると、次セッションへ経験が引き継がれます。

```
「今日の実験セッションで学んだこと、失敗したこと、
 有効だったアプローチを task_diary.md にまとめてください」
```

### 5. Headless モードでバッチ実験自動化

```bash
for alpha in 0.1 0.5 1.0; do
  claude -p "alpha=${alpha}でERGMを推定し結果をresults/alpha_${alpha}.csv に保存" \
    --allowedTools "Read,Edit,Bash(python *)" \
    --max-budget-usd 2.00
done
```

### 6. セッション管理で実験を継続

```bash
claude -n network-experiment      # 実験に名前を付けて開始
claude --continue                 # 直近のセッションを再開
claude --resume network-experiment  # 名前指定で再開
```

---

## 推奨ワークフロー

```
1. /init → CLAUDE.md 自動生成・カスタマイズ
2. Shift+Tab → Plan Mode で実験設計
3. 成功基準（テスト・検証スクリプト）を定義して渡す
4. Hooks で自動テスト・検証を設定
5. Subagents で並列実験
6. セッション終了前に Task Diary を記録
7. /compact で定期的にコンテキストを圧縮
```

**本プロジェクトで特に有効**: CLAUDE.md へのデータスキーマ・検証基準の明記 + Stop Hook による出力自動検証の組み合わせ。
