# ネットワーク分析プロジェクト

## プロジェクト概要

USPTO デザイン特許の引用ネットワーク・グラフ分析パイプライン。

- **データ**: USPTO特許コーパス、引用ペア画像類似度判定済みデータ
- **入力**: `/mnt/eightthdd/uspto/qwen_similarity_results/{year}.jsonl`（2007〜2022）
- **出力**: グラフ指標・ネットワーク分析結果
- **使用ライブラリ**: networkx, pandas, scipy, matplotlib, numpy

## データスキーマ（入力 JSONL の主要フィールド）

| フィールド | 内容 |
|---|---|
| `source_images` / `target_images` | 引用元・引用先の特許画像パス |
| `image_type_used` | 使用図タイプ（front / overview / perspective） |
| `similarity` | 視覚的類似度（"Yes" / "No"） |
| `confidence` | 確信度（1〜5） |
| `reason` | 判断理由（英語） |
| `error` | エラー時のみ付与 |

## 禁止事項

- 実験結果の JSONL・CSV を上書きしない（必ず別ファイルで保存）
- `/mnt/eightthdd/` 以下のデータを直接編集しない

## 検証基準（成功基準）

グラフ構築が完了した時：
- ノード数・エッジ数がログに記録されていること
- 孤立ノードの割合が確認できること
- 主要指標（次数分布・PageRank上位10件）が出力されること

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
