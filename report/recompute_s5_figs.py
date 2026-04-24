"""
Generate all Section 5 figures from the recomputed CSV files.
"""
import csv, os
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = Path('/Users/liangxinyue/Downloads/edubench/deep_analysis_outputs')
FIG = OUT / 'figures'

AUTO_EVALS = ['EduBenchEvaluator', 'deepseek-r1', 'deepseek-v3', 'gpt-4o', 'qwq-plus']
COLORS = {'EduBenchEvaluator': '#e74c3c', 'deepseek-r1': '#3498db', 'deepseek-v3': '#2ecc71',
           'gpt-4o': '#9b59b6', 'qwq-plus': '#f39c12'}

def read_csv(name):
    with open(OUT / name, encoding='utf-8') as f:
        return list(csv.DictReader(f))

# ── Fig 1: s5_score_bin_accuracy ─────────────────────────────────────────
print("Generating s5_score_bin_accuracy.png ...")
data = read_csv('s5_score_bin_accuracy.csv')
fig, ax = plt.subplots(figsize=(10, 6))
bins = [1, 2, 3, 4, 5]
x = np.arange(len(bins))
width = 0.15
for i, ev in enumerate(AUTO_EVALS):
    vals = []
    for b in bins:
        row = [r for r in data if r['evaluator'] == ev and r['score_bin'] == str(b)]
        vals.append(float(row[0]['accuracy']) * 100 if row else 0)
    ax.bar(x + i * width, vals, width, label=ev, color=COLORS[ev])
ax.set_xlabel('Human Score (rounded)')
ax.set_ylabel('Accuracy (%)')
ax.set_title('Score Bin Accuracy by Evaluator (Test Set, n=2218)')
ax.set_xticks(x + width * 2)
ax.set_xticklabels(bins)
ax.legend(fontsize=8)
ax.set_ylim(0, 100)
plt.tight_layout()
fig.savefig(FIG / 's5_score_bin_accuracy.png', dpi=150)
plt.close()
print("  done")

# ── Fig 2: s5_calibration_curves ─────────────────────────────────────────
print("Generating s5_calibration_curves.png ...")
data = read_csv('s5_calibration_fine.csv')
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot([1, 5], [1, 5], 'k--', alpha=0.3, label='Perfect calibration')
for ev in AUTO_EVALS:
    ev_data = [r for r in data if r['evaluator'] == ev]
    hm = [float(r['human_mean_in_bin']) for r in ev_data]
    pm = [float(r['pred_mean_in_bin']) for r in ev_data]
    ax.plot(hm, pm, 'o-', label=ev, color=COLORS[ev], markersize=5)
ax.set_xlabel('Human Mean Score (binned)')
ax.set_ylabel('Predicted Mean Score')
ax.set_title('Calibration Curves (Test Set, n=2218)')
ax.legend(fontsize=8)
ax.set_xlim(0.8, 5.2)
ax.set_ylim(0.8, 5.2)
plt.tight_layout()
fig.savefig(FIG / 's5_calibration_curves.png', dpi=150)
plt.close()
print("  done")

# ── Fig 3: s5_evaluator_ranking ──────────────────────────────────────────
print("Generating s5_evaluator_ranking.png ...")
data = read_csv('s5_evaluator_ranking.csv')
fig, axes = plt.subplots(1, 4, figsize=(16, 5))
metrics = [('mae', 'MAE ↓', True), ('exact_match', 'Exact Match ↑', False),
           ('kendall_tau', "Kendall's τ ↑", False), ('binned_agreement', 'Binned Agree ↑', False)]
for ax, (col, title, invert) in zip(axes, metrics):
    evs = [r['evaluator'] for r in data]
    vals = [float(r[col]) for r in data]
    colors = [COLORS[e] for e in evs]
    ax.barh(evs, vals, color=colors)
    ax.set_title(title)
    if invert:
        ax.invert_xaxis()
    ax.tick_params(axis='y', labelsize=8)
fig.suptitle('Evaluator Ranking (Test Set, n=2218)', fontsize=13)
plt.tight_layout()
fig.savefig(FIG / 's5_evaluator_ranking.png', dpi=150)
plt.close()
print("  done")

# ── Fig 4: s5_affinity ───────────────────────────────────────────────────
print("Generating s5_affinity.png ...")
data = read_csv('s5_affinity.csv')
if data:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, ev in zip(axes, ['deepseek-r1', 'deepseek-v3']):
        ev_data = [r for r in data if r['evaluator'] == ev]
        gens = [r['generator'] for r in ev_data]
        biases = [float(r['bias']) for r in ev_data]
        colors_list = ['#e74c3c' if r['is_own'] == 'True' else '#3498db' for r in ev_data]
        ax.barh(gens, biases, color=colors_list)
        ax.set_title(f'{ev} as evaluator')
        ax.set_xlabel('Signed Bias')
        ax.axvline(0, color='gray', linestyle='--', alpha=0.5)
    fig.suptitle('Self-Affinity Analysis (Test Set)', fontsize=13)
    plt.tight_layout()
    fig.savefig(FIG / 's5_affinity.png', dpi=150)
    plt.close()
    print("  done")
else:
    print("  skipped (no data)")

# ── Fig 5: s5_metric_accuracy_heatmap ────────────────────────────────────
print("Generating s5_metric_accuracy_heatmap.png ...")
data = read_csv('s5_metric_accuracy.csv')
metrics_list = sorted(set(r['metric'] for r in data))
fig, ax = plt.subplots(figsize=(14, 8))
matrix = []
for m in metrics_list:
    row_vals = []
    for ev in AUTO_EVALS:
        match = [r for r in data if r['evaluator'] == ev and r['metric'] == m]
        row_vals.append(float(match[0]['accuracy']) if match else 0)
    matrix.append(row_vals)
matrix = np.array(matrix)
im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto', vmin=0.3, vmax=1.0)
ax.set_xticks(range(len(AUTO_EVALS)))
ax.set_xticklabels(AUTO_EVALS, rotation=45, ha='right', fontsize=9)
ax.set_yticks(range(len(metrics_list)))
ax.set_yticklabels(metrics_list, fontsize=8)
for i in range(len(metrics_list)):
    for j in range(len(AUTO_EVALS)):
        ax.text(j, i, f'{matrix[i,j]:.2f}', ha='center', va='center', fontsize=7)
plt.colorbar(im, ax=ax, label='Exact Match Rate')
ax.set_title('Metric × Evaluator Accuracy (Test Set, n=2218)')
plt.tight_layout()
fig.savefig(FIG / 's5_metric_accuracy_heatmap.png', dpi=150)
plt.close()
print("  done")

# ── Fig 6: cat_s5_eval_mae_subject ───────────────────────────────────────
print("Generating cat_s5_eval_mae_subject.png ...")
data = read_csv('cat_s5_eval_by_subject.csv')
subjects = sorted(set(r['subject'] for r in data))
fig, ax = plt.subplots(figsize=(14, 8))
matrix = []
for s in subjects:
    row_vals = []
    for ev in AUTO_EVALS:
        match = [r for r in data if r['evaluator'] == ev and r['subject'] == s]
        row_vals.append(float(match[0]['mae']) if match else 0)
    matrix.append(row_vals)
matrix = np.array(matrix)
im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto', vmin=0.2, vmax=1.0)
ax.set_xticks(range(len(AUTO_EVALS)))
ax.set_xticklabels(AUTO_EVALS, rotation=45, ha='right', fontsize=9)
ax.set_yticks(range(len(subjects)))
ax.set_yticklabels(subjects, fontsize=7)
plt.colorbar(im, ax=ax, label='MAE')
ax.set_title('Subject × Evaluator MAE (Test Set, n=2218)')
plt.tight_layout()
fig.savefig(FIG / 'cat_s5_eval_mae_subject.png', dpi=150)
plt.close()
print("  done")

# ── Fig 7: cat_s5_eval_mae_edu ───────────────────────────────────────────
print("Generating cat_s5_eval_mae_edu.png ...")
data = read_csv('cat_s5_eval_by_edu.csv')
edu_order = ['Elementary School', 'Middle School', 'High School', 'Undergraduate', 'Master', 'PhD']
edu_list = [e for e in edu_order if e in set(r['education_level'] for r in data)]
fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(edu_list))
width = 0.15
for i, ev in enumerate(AUTO_EVALS):
    vals = []
    for e in edu_list:
        match = [r for r in data if r['evaluator'] == ev and r['education_level'] == e]
        vals.append(float(match[0]['mae']) if match else 0)
    ax.bar(x + i * width, vals, width, label=ev, color=COLORS[ev])
ax.set_xlabel('Education Level')
ax.set_ylabel('MAE')
ax.set_title('Evaluator MAE by Education Level (Test Set, n=2218)')
ax.set_xticks(x + width * 2)
ax.set_xticklabels(edu_list, rotation=30, ha='right', fontsize=9)
ax.legend(fontsize=8)
plt.tight_layout()
fig.savefig(FIG / 'cat_s5_eval_mae_edu.png', dpi=150)
plt.close()
print("  done")

# ── Fig 8: cat_s5_eval_tau_edu ───────────────────────────────────────────
print("Generating cat_s5_eval_tau_edu.png ...")
data = read_csv('cat_s5_eval_by_edu.csv')
fig, ax = plt.subplots(figsize=(12, 6))
x = np.arange(len(edu_list))
width = 0.15
for i, ev in enumerate(AUTO_EVALS):
    vals = []
    for e in edu_list:
        match = [r for r in data if r['evaluator'] == ev and r['education_level'] == e]
        vals.append(float(match[0]['kendall_tau']) if match else 0)
    ax.bar(x + i * width, vals, width, label=ev, color=COLORS[ev])
ax.set_xlabel('Education Level')
ax.set_ylabel("Kendall's τ")
ax.set_title("Evaluator Kendall's τ by Education Level (Test Set, n=2218)")
ax.set_xticks(x + width * 2)
ax.set_xticklabels(edu_list, rotation=30, ha='right', fontsize=9)
ax.legend(fontsize=8)
plt.tight_layout()
fig.savefig(FIG / 'cat_s5_eval_tau_edu.png', dpi=150)
plt.close()
print("  done")

# ── Fig 9: cat_s5_eval_mae_qtype ────────────────────────────────────────
print("Generating cat_s5_eval_mae_qtype.png ...")
data = read_csv('cat_s5_eval_by_qtype.csv')
qtypes = sorted(set(r['question_type'] for r in data))
fig, ax = plt.subplots(figsize=(12, 7))
matrix = []
for q in qtypes:
    row_vals = []
    for ev in AUTO_EVALS:
        match = [r for r in data if r['evaluator'] == ev and r['question_type'] == q]
        row_vals.append(float(match[0]['mae']) if match else 0)
    matrix.append(row_vals)
matrix = np.array(matrix)
im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto', vmin=0.2, vmax=1.0)
ax.set_xticks(range(len(AUTO_EVALS)))
ax.set_xticklabels(AUTO_EVALS, rotation=45, ha='right', fontsize=9)
ax.set_yticks(range(len(qtypes)))
ax.set_yticklabels(qtypes, fontsize=8)
for i in range(len(qtypes)):
    for j in range(len(AUTO_EVALS)):
        ax.text(j, i, f'{matrix[i,j]:.3f}', ha='center', va='center', fontsize=7)
plt.colorbar(im, ax=ax, label='MAE')
ax.set_title('Question Type × Evaluator MAE (Test Set, n=2218)')
plt.tight_layout()
fig.savefig(FIG / 'cat_s5_eval_mae_qtype.png', dpi=150)
plt.close()
print("  done")

print("\n=== All figures generated ===")
