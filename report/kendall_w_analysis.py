"""
kendall_w_analysis.py

计算 results_merge.jsonl 中评分者一致性（Kendall's W）：
  1. human 三者之间的 Kendall's W
  2. 各模型打分 vs 人类均分 的 Kendall's W
  3. 每个 human vs 各模型 的 Kendall's W（矩阵形式）

可选：用三个 human 均值补全偏离过大的异常分数（threshold 参数控制）。
"""

import json
import numpy as np
from scipy import stats
from collections import defaultdict
from pathlib import Path

RESULTS_PATH = Path("results_test.jsonl")

MODEL_KEYS = ["deepseek-r1", "deepseek-v3", "gpt-4o", "qwq-plus", "EduBenchEvaluator"]
HUMAN_KEYS = ["human_1", "human_2", "human_3"]


# ─────────────────────────────────────────────
# 核心工具函数
# ─────────────────────────────────────────────

# def kendall_w(matrix: np.ndarray) -> float:
#     """
#     通用 Kendall's W。
#     matrix shape = (n_samples, m_raters)，每列为一个评分者的分数序列。
#     对每列分别计秩（平均秩处理并列），再套标准公式：
#       W = 12S / (m² * (n³ - n))
#     """
#     n, m = matrix.shape
#     ranked = np.apply_along_axis(stats.rankdata, 0, matrix)
#     rank_sums = ranked.sum(axis=1)
#     S = np.sum((rank_sums - rank_sums.mean()) ** 2)
#     return float(12 * S / (m ** 2 * (n ** 3 - n)))


def kendall_w(matrix: np.ndarray) -> float:
    """带并列修正的 Kendall's W。"""
    n, m = matrix.shape
    ranked = np.apply_along_axis(stats.rankdata, 0, matrix)
    rank_sums = ranked.sum(axis=1)
    S = np.sum((rank_sums - rank_sums.mean()) ** 2)

    # 计算每个评分者的并列修正项 T_j
    T = 0.0
    for j in range(m):
        col = matrix[:, j]
        _, counts = np.unique(col, return_counts=True)
        T += np.sum(counts ** 3 - counts) / 12.0

    W = 12 * S / (m ** 2 * (n ** 3 - n) - m * T)
    return float(W)


def fill_outlier_with_human_mean(ev: dict, threshold: float = 2.0) -> dict:
    """
    对 human_1/2/3 中偏离其余两者均值超过 threshold 的分数，
    用另外两者的均值替换。三者均不为 None 时才处理。
    返回补全后的新字典，不修改原始数据。
    """
    ev = dict(ev)
    scores = [ev.get(k) for k in HUMAN_KEYS]
    if any(s is None for s in scores):
        return ev
    for i, key in enumerate(HUMAN_KEYS):
        others_mean = sum(scores[j] for j in range(3) if j != i) / 2
        if abs(scores[i] - others_mean) > threshold:
            ev[key] = others_mean
    return ev


def load_evaluate_records(results_path: Path, fill_outlier: bool = False,
                           threshold: float = 2.0) -> list[dict]:
    """读取 results_merge.jsonl，返回每条记录的 evaluate 字典列表。"""
    records = []
    with open(results_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line).get("evaluate", {})
            if fill_outlier:
                ev = fill_outlier_with_human_mean(ev, threshold)
            records.append(ev)
    return records


def build_matrix(records: list[dict], col_keys: list[str],
                 require_all: bool = True) -> np.ndarray:
    """
    从 evaluate 记录列表中提取指定列，构建评分矩阵。
    require_all=True 时只保留所有列均不为 None 的行。
    返回 shape=(n_valid, len(col_keys)) 的 ndarray。
    """
    rows = []
    for ev in records:
        row = [ev.get(k) for k in col_keys]
        if require_all and any(v is None for v in row):
            continue
        rows.append(row)
    return np.array(rows, dtype=float)


# ─────────────────────────────────────────────
# 三个分析函数
# ─────────────────────────────────────────────

def analyze_human_inter_rater(records: list[dict]) -> dict:
    """1. 计算 human_1/2/3 三者之间的 Kendall's W。"""
    matrix = build_matrix(records, HUMAN_KEYS)
    w = kendall_w(matrix)
    result = {"kendall_w": round(w, 4), "n_samples": len(matrix)}

    print("=" * 50)
    print("1. Human Inter-Rater Kendall's W")
    print(f"   raters : {', '.join(HUMAN_KEYS)}")
    print(f"   W      : {w:.4f}")
    print(f"   samples: {len(matrix)}")
    return result


def analyze_model_vs_human_avg(records: list[dict]) -> dict:
    """2. 各模型打分 vs 人类均分 的 Kendall's W（2-rater 矩阵）。"""
    results = {}

    print("=" * 50)
    print("2. Model vs Human-Average Kendall's W")
    print(f"  {'Model':<22} {'W':>8}  {'N':>7}")
    print("-" * 42)

    for model_key in MODEL_KEYS:
        rows = []
        for ev in records:
            m_score = ev.get(model_key)
            h_scores = [ev.get(k) for k in HUMAN_KEYS]
            h_scores = [s for s in h_scores if s is not None]
            if m_score is None or not h_scores:
                continue
            rows.append([m_score, sum(h_scores) / len(h_scores)])

        if len(rows) < 2:
            w, n = float("nan"), 0
        else:
            w = kendall_w(np.array(rows, dtype=float))
            n = len(rows)

        results[model_key] = {"kendall_w": round(w, 4), "n_samples": n}
        print(f"  {model_key:<22} {w:>8.4f}  {n:>7}")

    return results


def analyze_per_human_vs_model(records: list[dict]) -> dict:
    """3. 每个 human vs 各模型 的 Kendall's W（矩阵展示）。"""
    results = {h: {} for h in HUMAN_KEYS}

    print("=" * 50)
    print("3. Per-Human vs Model Kendall's W")
    header = f"  {'':12}" + "".join(f"  {m:>22}" for m in MODEL_KEYS)
    print(header)
    print("-" * len(header))

    for human_key in HUMAN_KEYS:
        print(f"  {human_key:<12}", end="")
        for model_key in MODEL_KEYS:
            rows = []
            for ev in records:
                h_score = ev.get(human_key)
                m_score = ev.get(model_key)
                if h_score is None or m_score is None:
                    continue
                rows.append([h_score, m_score])

            if len(rows) < 2:
                w, n = float("nan"), 0
            else:
                w = kendall_w(np.array(rows, dtype=float))
                n = len(rows)

            results[human_key][model_key] = {"kendall_w": round(w, 4), "n_samples": n}
            print(f"  {w:>22.4f}", end="")
        print()

    return results

def analyze_human_2_inter_rater(records: list[dict]) -> dict:
    """1. 计算 human 两两之间以及三者整体的 Kendall's W。"""
    from itertools import combinations

    print("=" * 50)
    print("1. Human Inter-Rater Kendall's W")
    print(f"  {'Pair':<24} {'W':>8}  {'N':>7}")
    print("-" * 44)

    results = {}

    # 两两组合
    for h1, h2 in combinations(HUMAN_KEYS, 2):
        matrix = build_matrix(records, [h1, h2])
        w = kendall_w(matrix)
        key = f"{h1} vs {h2}"
        results[key] = {"kendall_w": round(w, 4), "n_samples": len(matrix)}
        print(f"  {key:<24} {w:>8.4f}  {len(matrix):>7}")

    # 三者整体
    matrix = build_matrix(records, HUMAN_KEYS)
    w = kendall_w(matrix)
    key = "human_1 vs human_2 vs human_3"
    results[key] = {"kendall_w": round(w, 4), "n_samples": len(matrix)}
    print(f"  {key:<24} {w:>8.4f}  {len(matrix):>7}")

    return results

# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────

def main(fill_outlier: bool = False, threshold: float = 2.0):
    print(f"\n[INFO] 数据文件: {RESULTS_PATH}")
    print(f"[INFO] 异常补全: {'开启' if fill_outlier else '关闭'}"
          + (f"（threshold={threshold}）" if fill_outlier else ""))
    print()

    records = load_evaluate_records(RESULTS_PATH, fill_outlier, threshold)
    print(f"[INFO] 总记录数: {len(records)}\n")

    # r1 = analyze_human_inter_rater(records)
    r1 = analyze_human_2_inter_rater(records)
    print()
    r2 = analyze_model_vs_human_avg(records)
    print()
    r3 = analyze_per_human_vs_model(records)

    return {"human_inter_rater": r1, "model_vs_human_avg": r2, "per_human_vs_model": r3}


if __name__ == "__main__":
    main(fill_outlier=True)   # 改为 True 可开启异常补全
