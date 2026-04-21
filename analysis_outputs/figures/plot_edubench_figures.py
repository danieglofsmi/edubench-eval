from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

RESULTS_FILE = Path('/Users/liangxinyue/Downloads/edubench/results_merge.jsonl')
BASE_DIR = Path('/Users/liangxinyue/Downloads/edubench/analysis_outputs')
FIG_DIR = BASE_DIR / 'figures'
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC', 'SimHei', 'Noto Sans CJK SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 180
plt.rcParams['savefig.dpi'] = 300

EVAL_ORDER = ['EduBenchEvaluator', 'deepseek-r1', 'deepseek-v3', 'gpt-4o', 'qwq-plus']
TASK_ORDER = [
    'automatic_grading',
    'error_correction',
    'idea_provision',
    'personalized_content_creation',
    'personalized_learning_support',
    'problem_solving',
    'psychological_support',
    'question_generation',
    'teaching_material_generation',
]
LANGS = ['en', 'zh']
CALIBRATION_BINS = [(1.0, 1.99), (2.0, 2.99), (3.0, 3.99), (4.0, 4.49), (4.5, 5.0)]
SELF_FAMILY_EVALUATORS = ['deepseek-r1', 'deepseek-v3']


def read_csv(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_jsonl(path: Path):
    rows = []
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def to_float(x: str) -> float:
    return float(x) if x not in (None, '') else float('nan')


def detect_language(text: str) -> str:
    return 'zh' if re.search(r'[\u4e00-\u9fff]', text or '') else 'en'


def valid_humans(row):
    return [row['evaluate'].get(k) for k in ['human_1', 'human_2', 'human_3'] if row['evaluate'].get(k) is not None]


def human_mean(row):
    hs = valid_humans(row)
    return sum(hs) / len(hs)


def aggregate_by_language(rows):
    task_evaluator = []
    metric_evaluator = []
    affinity = []
    calibration = []

    for lang in LANGS:
        lang_rows = [r for r in rows if detect_language(r['question']) == lang]

        for task in TASK_ORDER:
            task_rows = [r for r in lang_rows if r['task'] == task]
            for ev in EVAL_ORDER:
                ev_rows = [r for r in task_rows if r['evaluate'].get(ev) is not None]
                if not ev_rows:
                    continue
                diffs = [abs(r['evaluate'][ev] - human_mean(r)) for r in ev_rows]
                signed = [r['evaluate'][ev] - human_mean(r) for r in ev_rows]
                exact = sum(1 for r in ev_rows if r['evaluate'][ev] == round(human_mean(r)))
                task_evaluator.append({
                    'language': lang,
                    'task': task,
                    'evaluator': ev,
                    'n': len(ev_rows),
                    'mae_to_human_mean': sum(diffs) / len(diffs),
                    'signed_bias_vs_human_mean': sum(signed) / len(signed),
                    'exact_match_rate': exact / len(ev_rows),
                })

        metric_names = sorted({r['metric'] for r in lang_rows})
        for metric in metric_names:
            metric_rows = [r for r in lang_rows if r['metric'] == metric]
            if not metric_rows:
                continue
            hm = [human_mean(r) for r in metric_rows]
            for ev in EVAL_ORDER:
                ev_rows = [r for r in metric_rows if r['evaluate'].get(ev) is not None]
                if not ev_rows:
                    continue
                diffs = [abs(r['evaluate'][ev] - human_mean(r)) for r in ev_rows]
                signed = [r['evaluate'][ev] - human_mean(r) for r in ev_rows]
                metric_evaluator.append({
                    'language': lang,
                    'metric': metric,
                    'n': len(metric_rows),
                    'human_mean_score': sum(hm) / len(hm),
                    'evaluator': ev,
                    'mae_to_human_mean': sum(diffs) / len(diffs),
                    'signed_bias_vs_human_mean': sum(signed) / len(signed),
                })

        for ev in EVAL_ORDER:
            for low, high in CALIBRATION_BINS:
                bin_rows = [r for r in lang_rows if r['evaluate'].get(ev) is not None and low <= human_mean(r) <= high]
                if not bin_rows:
                    continue
                human_vals = [human_mean(r) for r in bin_rows]
                pred_vals = [r['evaluate'][ev] for r in bin_rows]
                calibration.append({
                    'language': lang,
                    'evaluator': ev,
                    'bin_label': f'{low:.2f}-{high:.2f}',
                    'n': len(bin_rows),
                    'human_mean_in_bin': sum(human_vals) / len(human_vals),
                    'predicted_mean_in_bin': sum(pred_vals) / len(pred_vals),
                    'calibration_gap_pred_minus_human': (sum(pred_vals) / len(pred_vals)) - (sum(human_vals) / len(human_vals)),
                    'mae_in_bin': sum(abs(r['evaluate'][ev] - human_mean(r)) for r in bin_rows) / len(bin_rows),
                })

        for ev in SELF_FAMILY_EVALUATORS:
            own_name = ev
            own_rows = [r for r in lang_rows if r['model'] == own_name and r['evaluate'].get(ev) is not None]
            other_rows = [r for r in lang_rows if r['model'] != own_name and r['evaluate'].get(ev) is not None]
            own_signed = [r['evaluate'][ev] - human_mean(r) for r in own_rows]
            other_signed = [r['evaluate'][ev] - human_mean(r) for r in other_rows]
            own_mae = [abs(x) for x in own_signed]
            other_mae = [abs(x) for x in other_signed]
            if own_rows and other_rows:
                affinity.append({
                    'language': lang,
                    'evaluator': ev,
                    'comparison': 'own_vs_other_overall',
                    'group': 'own',
                    'n': len(own_rows),
                    'signed_bias_vs_human_mean': sum(own_signed) / len(own_signed),
                    'mae_to_human_mean': sum(own_mae) / len(own_mae),
                })
                affinity.append({
                    'language': lang,
                    'evaluator': ev,
                    'comparison': 'own_vs_other_overall',
                    'group': 'other',
                    'n': len(other_rows),
                    'signed_bias_vs_human_mean': sum(other_signed) / len(other_signed),
                    'mae_to_human_mean': sum(other_mae) / len(other_mae),
                })
                affinity.append({
                    'language': lang,
                    'evaluator': ev,
                    'comparison': 'own_minus_other',
                    'group': 'delta',
                    'n': '',
                    'signed_bias_vs_human_mean': (sum(own_signed) / len(own_signed)) - (sum(other_signed) / len(other_signed)),
                    'mae_to_human_mean': (sum(own_mae) / len(own_mae)) - (sum(other_mae) / len(other_mae)),
                })

    return task_evaluator, metric_evaluator, affinity, calibration


def make_task_evaluator_mae_heatmap(task_rows, lang):
    values = np.full((len(TASK_ORDER), len(EVAL_ORDER)), np.nan)
    for r in task_rows:
        i = TASK_ORDER.index(r['task'])
        j = EVAL_ORDER.index(r['evaluator'])
        values[i, j] = r['mae_to_human_mean']

    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    im = ax.imshow(values, cmap='YlOrRd', aspect='auto')
    ax.set_xticks(range(len(EVAL_ORDER)))
    ax.set_xticklabels(EVAL_ORDER, rotation=20, ha='right')
    ax.set_yticks(range(len(TASK_ORDER)))
    ax.set_yticklabels(TASK_ORDER)
    ax.set_title(f'Task × Evaluator MAE to Human Mean ({lang})')

    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if not np.isnan(values[i, j]):
                ax.text(j, i, f'{values[i, j]:.2f}', ha='center', va='center', fontsize=8, color='black')

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('MAE')
    fig.tight_layout()
    fig.savefig(FIG_DIR / f'task_evaluator_mae_heatmap_{lang}.png', bbox_inches='tight')
    fig.savefig(FIG_DIR / f'task_evaluator_mae_heatmap_{lang}.pdf', bbox_inches='tight')
    plt.close(fig)


def make_metric_evaluator_mae_heatmap_top12(metric_rows, lang):
    metric_count = {}
    for r in metric_rows:
        metric_count.setdefault(r['metric'], int(r['n']))
    top_metrics = [k for k, _ in sorted(metric_count.items(), key=lambda x: (-x[1], x[0]))[:12]]

    values = np.full((len(top_metrics), len(EVAL_ORDER)), np.nan)
    for r in metric_rows:
        if r['metric'] in top_metrics:
            i = top_metrics.index(r['metric'])
            j = EVAL_ORDER.index(r['evaluator'])
            values[i, j] = r['mae_to_human_mean']

    fig, ax = plt.subplots(figsize=(11.2, 7.0))
    im = ax.imshow(values, cmap='PuRd', aspect='auto')
    ax.set_xticks(range(len(EVAL_ORDER)))
    ax.set_xticklabels(EVAL_ORDER, rotation=20, ha='right')
    ax.set_yticks(range(len(top_metrics)))
    ax.set_yticklabels(top_metrics)
    ax.set_title(f'Top-12 Metric × Evaluator MAE Heatmap ({lang})')

    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if not np.isnan(values[i, j]):
                ax.text(j, i, f'{values[i, j]:.2f}', ha='center', va='center', fontsize=7, color='black')

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('MAE')
    fig.tight_layout()
    fig.savefig(FIG_DIR / f'metric_evaluator_mae_heatmap_top12_{lang}.png', bbox_inches='tight')
    fig.savefig(FIG_DIR / f'metric_evaluator_mae_heatmap_top12_{lang}.pdf', bbox_inches='tight')
    plt.close(fig)


def make_calibration_curves(cal_rows, lang):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    for ev in EVAL_ORDER:
        sub = [r for r in cal_rows if r['evaluator'] == ev]
        x = [r['human_mean_in_bin'] for r in sub]
        y_pred = [r['predicted_mean_in_bin'] for r in sub]
        gap = [r['calibration_gap_pred_minus_human'] for r in sub]
        axes[0].plot(x, y_pred, marker='o', linewidth=2, label=ev)
        axes[1].plot(x, gap, marker='o', linewidth=2, label=ev)

    min_x = min(r['human_mean_in_bin'] for r in cal_rows)
    max_x = max(r['human_mean_in_bin'] for r in cal_rows)
    axes[0].plot([min_x, max_x], [min_x, max_x], linestyle='--', color='gray', label='Perfect calibration')
    axes[0].set_title(f'Calibration Curve: Predicted vs Human ({lang})')
    axes[0].set_xlabel('Human mean score')
    axes[0].set_ylabel('Evaluator predicted mean')
    axes[0].legend(fontsize=8, loc='upper left')

    axes[1].axhline(0, linestyle='--', color='gray')
    axes[1].set_title(f'Calibration Gap by Score Bin ({lang})')
    axes[1].set_xlabel('Human mean score')
    axes[1].set_ylabel('Predicted - Human')
    axes[1].legend(fontsize=8, loc='upper right')

    fig.tight_layout()
    fig.savefig(FIG_DIR / f'calibration_curves_{lang}.png', bbox_inches='tight')
    fig.savefig(FIG_DIR / f'calibration_curves_{lang}.pdf', bbox_inches='tight')
    plt.close(fig)


def make_affinity_barplots(aff_rows, lang):
    rows = [r for r in aff_rows if r['comparison'] == 'own_vs_other_overall']
    evaluators = sorted({r['evaluator'] for r in rows})
    groups = ['own', 'other']
    colors = {'own': '#d95f02', 'other': '#1b9e77'}

    signed = {ev: {g: np.nan for g in groups} for ev in evaluators}
    maes = {ev: {g: np.nan for g in groups} for ev in evaluators}
    for r in rows:
        signed[r['evaluator']][r['group']] = r['signed_bias_vs_human_mean']
        maes[r['evaluator']][r['group']] = r['mae_to_human_mean']

    x = np.arange(len(evaluators))
    width = 0.33
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.8))

    for idx, g in enumerate(groups):
        axes[0].bar(x + (idx - 0.5) * width, [signed[ev][g] for ev in evaluators], width=width, color=colors[g], label=g)
        axes[1].bar(x + (idx - 0.5) * width, [maes[ev][g] for ev in evaluators], width=width, color=colors[g], label=g)

    axes[0].axhline(0, linestyle='--', color='gray')
    axes[0].set_title(f'Evaluator Self-Family Affinity: Signed Bias ({lang})')
    axes[0].set_ylabel('Signed bias vs human mean')
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(evaluators)
    axes[0].legend()

    axes[1].set_title(f'Evaluator Self-Family Affinity: MAE ({lang})')
    axes[1].set_ylabel('MAE to human mean')
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(evaluators)
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(FIG_DIR / f'evaluator_affinity_barplots_{lang}.png', bbox_inches='tight')
    fig.savefig(FIG_DIR / f'evaluator_affinity_barplots_{lang}.pdf', bbox_inches='tight')
    plt.close(fig)


def make_task_bias_heatmap(task_rows, lang):
    values = np.full((len(TASK_ORDER), len(EVAL_ORDER)), np.nan)
    for r in task_rows:
        i = TASK_ORDER.index(r['task'])
        j = EVAL_ORDER.index(r['evaluator'])
        values[i, j] = r['signed_bias_vs_human_mean']

    vmax = np.nanmax(np.abs(values))
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    im = ax.imshow(values, cmap='coolwarm', vmin=-vmax, vmax=vmax, aspect='auto')
    ax.set_xticks(range(len(EVAL_ORDER)))
    ax.set_xticklabels(EVAL_ORDER, rotation=20, ha='right')
    ax.set_yticks(range(len(TASK_ORDER)))
    ax.set_yticklabels(TASK_ORDER)
    ax.set_title(f'Task × Evaluator Signed Bias Heatmap ({lang})')

    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            if not np.isnan(values[i, j]):
                ax.text(j, i, f'{values[i, j]:.2f}', ha='center', va='center', fontsize=8, color='black')

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Signed bias (pred - human)')
    fig.tight_layout()
    fig.savefig(FIG_DIR / f'task_evaluator_bias_heatmap_{lang}.png', bbox_inches='tight')
    fig.savefig(FIG_DIR / f'task_evaluator_bias_heatmap_{lang}.pdf', bbox_inches='tight')
    plt.close(fig)


def write_manifest():
    files = sorted(p.name for p in FIG_DIR.iterdir() if p.is_file())
    manifest_path = FIG_DIR / 'manifest.txt'
    manifest_path.write_text('\n'.join(files), encoding='utf-8')


def main():
    rows = load_jsonl(RESULTS_FILE)
    task_evaluator, metric_evaluator, affinity, calibration = aggregate_by_language(rows)

    for lang in LANGS:
        task_rows = [r for r in task_evaluator if r['language'] == lang]
        metric_rows = [r for r in metric_evaluator if r['language'] == lang]
        aff_rows = [r for r in affinity if r['language'] == lang]
        cal_rows = [r for r in calibration if r['language'] == lang]

        make_task_evaluator_mae_heatmap(task_rows, lang)
        make_metric_evaluator_mae_heatmap_top12(metric_rows, lang)
        make_calibration_curves(cal_rows, lang)
        make_affinity_barplots(aff_rows, lang)
        make_task_bias_heatmap(task_rows, lang)

    write_manifest()
    print('Generated language-specific figures in', FIG_DIR)


if __name__ == '__main__':
    main()
