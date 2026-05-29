#!/usr/bin/env python3
"""
コサイン類似度 CDF（Similar / Non-similar / All / Random の4線）。

入力:
  /mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl
  /mnt/eightthdd/uspto/class/D18/rank_index/perspective/vectors_l2norm.npy
出力: output/fig_sim_cdf.png

Random ペア:
  perspective rank_index（959特許）の全 C(959,2)=459,361 組み合わせの
  コサイン類似度を行列積で一括計算し、PCG64（seed=42）で 1,000 件を
  重複なし一様抽出する（物理慣例: 固定シード・uniform without replacement）。
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

JUDGMENTS_PATH = Path(
    "/mnt/eightthdd/uspto/class/D18/rank_judgments/cosine_numpy/all.jsonl"
)
RANK_INDEX_DIR = Path(
    "/mnt/eightthdd/uspto/class/D18/rank_index/perspective"
)
OUT_PATH    = Path(__file__).parent / "output" / "fig_sim_cdf.png"
RANDOM_N    = 1000
RANDOM_SEED = 42

# PRL / Nature Physics 準拠（SKILL.md 準拠）
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
    "savefig.bbox":        "tight",
}


def load_records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def sample_random_pairs(index_dir: Path, n: int, seed: int) -> np.ndarray:
    """
    rank_index の L2 正規化済みベクトルから全 C(N,2) ペアのコサイン類似度を
    行列積で一括計算し、n 件を一様無作為抽出（重複なし）して返す。

    物理慣例:
      - PCG64 アルゴリズム（numpy デフォルト）+ 固定シードで再現性を確保
      - rng.choice(..., replace=False) で uniform without replacement
    """
    vecs = np.load(index_dir / "vectors_l2norm.npy")   # (N, D) float32, L2正規化済み
    N = len(vecs)

    # 全ペアのコサイン類似度行列（L2正規化済み → 内積 = コサイン類似度）
    S = (vecs @ vecs.T).astype(np.float64)             # (N, N)

    # 上三角（対角除く）→ 全 C(N,2) 一意ペアの類似度
    rows, cols  = np.triu_indices(N, k=1)
    all_sims    = S[rows, cols]                         # shape (C(N,2),)

    # 一様無作為抽出（固定シード seed で再現可能）
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(all_sims), size=n, replace=False)
    return all_sims[idx]


def ecdf(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """経験的 CDF: x の昇順ソート値と P(X ≤ x) を返す。"""
    x = np.sort(data)
    y = np.arange(1, len(x) + 1) / len(x)
    # 先頭に (x[0], 0) を付加して CDF が 0 から始まるようにする
    x = np.concatenate([[x[0]], x])
    y = np.concatenate([[0.0],  y])
    return x, y


def plot_cdf(records: list[dict], rand_sims: np.ndarray, out_path: Path) -> None:
    plt.rcParams.update(RC)

    judged   = [r for r in records if r["judgment"] != "Unknown"]
    yes_recs = [r for r in judged if r["judgment"] == "Yes"]
    no_recs  = [r for r in judged if r["judgment"] == "No"]

    all_sims = np.array([r["similarity"] for r in judged],   dtype=float)
    yes_sims = np.array([r["similarity"] for r in yes_recs], dtype=float)
    no_sims  = np.array([r["similarity"] for r in no_recs],  dtype=float)

    n_all  = len(all_sims)
    n_yes  = len(yes_sims)
    n_no   = len(no_sims)
    n_rand = len(rand_sims)

    layers = [
        (rand_sims, f"Random ($N={n_rand}$)",       "#555555", ":",  1.0, 1),
        (all_sims,  f"All ($N={n_all}$)",           "#888888", "-",  0.9, 2),
        (no_sims,   f"Non-similar ($N={n_no}$)",    "#d62728", "--", 1.2, 3),
        (yes_sims,  f"Similar ($N={n_yes}$)",       "#2166ac", "-",  1.4, 4),
    ]

    fig, ax = plt.subplots(figsize=(3.5, 3.5))

    for sims, label, color, ls, lw, zo in layers:
        x, y = ecdf(sims)
        ax.plot(x, y, color=color, ls=ls, lw=lw, label=label, zorder=zo)

    ax.set_xlabel("Cosine similarity")
    ax.set_ylabel("CDF")
    ax.set_xlim(0.35, 1.02)
    ax.set_ylim(-0.02, 1.05)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(0.1))
    ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(5))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(0.2))
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator(4))
    ax.legend(fontsize=9, framealpha=0.85, edgecolor="gray", loc="upper left")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    print(f"-> {out_path}")


def main() -> None:
    print("Loading records (all types)...")
    records   = load_records(JUDGMENTS_PATH)
    n_total   = len(records)
    n_unknown = sum(1 for r in records if r["judgment"] == "Unknown")
    n_judged  = n_total - n_unknown
    n_yes     = sum(1 for r in records if r["judgment"] == "Yes")
    n_no      = sum(1 for r in records if r["judgment"] == "No")
    print(f"  total={n_total}  unknown={n_unknown}  judged={n_judged}  yes={n_yes}  no={n_no}")

    print(f"Sampling {RANDOM_N} random pairs from rank_index (seed={RANDOM_SEED})...")
    rand_sims = sample_random_pairs(RANK_INDEX_DIR, RANDOM_N, RANDOM_SEED)
    print(f"  random sims: min={rand_sims.min():.4f}  max={rand_sims.max():.4f}"
          f"  mean={rand_sims.mean():.4f}  median={np.median(rand_sims):.4f}")

    print("Plotting CDF...")
    plot_cdf(records, rand_sims, OUT_PATH)
    print("Done.")


if __name__ == "__main__":
    main()
