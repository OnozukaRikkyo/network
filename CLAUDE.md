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

## 分析ステップ

| スクリプト | 入力 | 出力 |
|---|---|---|
| `vector/analysis/rank_analysis.py` | `rank_judgments/{sim_func}/all.jsonl` | `vector/output/{CLASS}/{sim_func}/rank_ccdf_{type}.png` 等 |
| `graph/graph_analysis.py` | `rank_judgments/{sim_func}/all.jsonl` | `graph/output/{CLASS}/triadic_scored.jsonl` |
| `graph/extract_high_sim_triads.py` | `triadic_scored.jsonl` | `graph/output/{CLASS}/high_sim_triads/` |
| `graph/verify/discord_analysis.py` | `triadic_scored.jsonl` | `graph/output/{CLASS}/verify/fp.csv`, `fn.csv` |
| `analyze_ergm.py` | `ergm_input/` + `qwen_similarity_results/` | `output/priority1〜4_*.png`, `analysis_summary.csv` |
| `visualize_ergm_network.py` | `ergm_input/` | `output/fig1〜7_*.png`（300 DPI）, `ergm_statistics.csv` |

## 推論パイプライン（`vector/reasoning/`）

| スクリプト | 入力 | 出力 |
|---|---|---|
| `extract_pilot.py` | `high_sim_perspective_0950_judged.csv` | `reasoning/pilot_24.csv`, `pilot_strata.csv` |
| `patent_rationale_pms.py` | `high_sim_*_judged.csv` | `reasoning/pms_results.csv`（M1/M2/M3/PMS） |
| `patent_visual_probes.py --module m5` | pilot CSV | `reasoning/m5_scores.csv` |
| `patent_visual_probes.py --module baseline` | pilot CSV | `reasoning/baseline_b.csv` |
| `merge_results.py` | 各モジュール出力 | `reasoning/unified_results.csv` |
| `analyze_results.py` | `unified_results.csv` | `reasoning/analysis_summary.txt`, `fig_*.png` |

---

## ステップ間の主要データフロー

```
json/{year}.json ──┐
data/{year}.csv ───┴─► edge_list/{year}.csv (STEP1)
                            │
                    ┌───────┴────────────────────────┐
                    ▼                                ▼
        cited_image_pairs/{year}.jsonl (2a)   edge_list_with_class/{year}.csv (2c)
                    │                                │
          ┌─────────┤                                │
          ▼         ▼                                ▼
  judge_cited_pairs  filter_pairs_by_class ──► class/{CLASS}/cited_image_pairs/
          │                                          │
          ▼                                   build_class_vectors → build_rank_index
  qwen_similarity_results/{year}.jsonl                │
          │                                    compute_ranks (V4)
          ├──► extract_yes_pairs (STEP4)              │
          │                                    rank_results/{sim_func}/{year}.jsonl
          └──────────────────────────────────► join_judgments (V5)
                                                      │
                                            rank_judgments/{sim_func}/all.jsonl
                                                      │
                                              ┌───────┴───────┐
                                              ▼               ▼
                                       rank_analysis     graph_analysis
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
