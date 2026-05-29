---
name: network
description: USPTO D18クラス設計特許の引用ネットワーク構築・グラフ分析を行う。引用ペアJSONLを起点にネットワークを構築し、中心性・コミュニティ・時系列変化などを分析する場合に使う。
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
