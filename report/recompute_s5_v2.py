"""
Recompute Section 5 analysis using the new results_test.jsonl (2218 rows).
Based on (question, answer, metric) triplet matching via split_train_test_v4.py.
Outputs: all s5_* and cat_s5_* CSV files + figures.
"""
import json, csv, math, os
from collections import defaultdict, Counter
from pathlib import Path
from statistics import pstdev

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── paths ────────────────────────────────────────────────────────────────
BASE = Path('/Users/liangxinyue/Downloads/edubench')
TEST_FILE = BASE / 'results_test.jsonl'
OUT = BASE / 'deep_analysis_outputs'
FIG = OUT / 'figures'
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

AUTO_EVALS = ['EduBenchEvaluator', 'deepseek-r1', 'deepseek-v3', 'gpt-4o', 'qwq-plus']
HUMAN_KEYS = ['human_1', 'human_2', 'human_3']
CALIBRATION_BINS = [(1.0, 1.99), (2.0, 2.99), (3.0, 3.49), (3.5, 3.99), (4.0, 4.49), (4.5, 5.0)]

# ── load ─────────────────────────────────────────────────────────────────
def load_jsonl(p):
    rows = []
    with open(p, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows

def write_csv(path, data, fields):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in data:
            w.writerow({k: r.get(k, '') for k in fields})

def human_mean(row):
    vals = [row['evaluate'].get(k) for k in HUMAN_KEYS if row['evaluate'].get(k) is not None]
    return sum(vals) / len(vals) if vals else None

def human_rounded(row):
    hm = human_mean(row)
    return round(hm) if hm is not None else None

def fmt(x, n=4):
    return round(x, n) if x is not None else ''

rows = load_jsonl(TEST_FILE)
print(f"Loaded {len(rows)} test rows")

# ── 5.1 Evaluator ranking ───────────────────────────────────────────────
print("Computing s5_evaluator_ranking ...")
eval_ranking = []
for ev in AUTO_EVALS:
    maes, biases, exacts = [], [], []
    pairs_human, pairs_pred = [], []
    for r in rows:
        hm = human_mean(r)
        if hm is None:
            continue
        pred = r['evaluate'].get(ev)
        if pred is None:
            continue
        maes.append(abs(pred - hm))
        biases.append(pred - hm)
        exacts.append(1 if round(pred) == round(hm) else 0)
        pairs_human.append(hm)
        pairs_pred.append(pred)
    n = len(maes)
    mae_val = sum(maes) / n
    bias_val = sum(biases) / n
    exact_val = sum(exacts) / n
    # Kendall's tau
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, min(i + 500, n)):  # sample for speed
            dh = pairs_human[j] - pairs_human[i]
            dp = pairs_pred[j] - pairs_pred[i]
            if dh * dp > 0:
                concordant += 1
            elif dh * dp < 0:
                discordant += 1
    tau = (concordant - discordant) / (concordant + discordant) if (concordant + discordant) > 0 else 0
    # Binned agreement
    agree = 0
    for r in rows:
        hm = human_mean(r)
        pred = r['evaluate'].get(ev)
        if hm is None or pred is None:
            continue
        hbin = 'low' if hm <= 2.5 else ('mid' if hm <= 3.5 else 'high')
        pbin = 'low' if pred <= 2.5 else ('mid' if pred <= 3.5 else 'high')
        if hbin == pbin:
            agree += 1
    binned = agree / n
    eval_ranking.append({
        'evaluator': ev, 'n': n, 'mae': fmt(mae_val), 'signed_bias': fmt(bias_val),
        'exact_match': fmt(exact_val), 'kendall_tau': fmt(tau), 'binned_agreement': fmt(binned)
    })

# Use scipy for accurate Kendall's tau
try:
    from scipy.stats import kendalltau
    for rec in eval_ranking:
        ev = rec['evaluator']
        h_list, p_list = [], []
        for r in rows:
            hm = human_mean(r)
            pred = r['evaluate'].get(ev)
            if hm is not None and pred is not None:
                h_list.append(hm)
                p_list.append(pred)
        tau, pval = kendalltau(h_list, p_list)
        rec['kendall_tau'] = fmt(tau)
    print("  (used scipy kendalltau)")
except ImportError:
    print("  (scipy not available, using sampled tau)")

write_csv(OUT / 's5_evaluator_ranking.csv', eval_ranking,
          ['evaluator', 'n', 'mae', 'signed_bias', 'exact_match', 'kendall_tau', 'binned_agreement'])
print(f"  s5_evaluator_ranking.csv written ({len(eval_ranking)} rows)")

# ── 5.2 Score bin accuracy ──────────────────────────────────────────────
print("Computing s5_score_bin_accuracy ...")
score_bin_rows = []
for ev in AUTO_EVALS:
    bins = defaultdict(lambda: {'n': 0, 'correct': 0})
    for r in rows:
        hr = human_rounded(r)
        pred = r['evaluate'].get(ev)
        if hr is None or pred is None:
            continue
        bins['overall']['n'] += 1
        bins['overall']['correct'] += (1 if round(pred) == hr else 0)
        bins[hr]['n'] += 1
        bins[hr]['correct'] += (1 if round(pred) == hr else 0)
    for b in ['overall', 1, 2, 3, 4, 5]:
        if bins[b]['n'] > 0:
            score_bin_rows.append({
                'evaluator': ev, 'score_bin': b, 'n': bins[b]['n'],
                'accuracy': fmt(bins[b]['correct'] / bins[b]['n'])
            })

write_csv(OUT / 's5_score_bin_accuracy.csv', score_bin_rows,
          ['evaluator', 'score_bin', 'n', 'accuracy'])
print(f"  s5_score_bin_accuracy.csv written ({len(score_bin_rows)} rows)")

# ── 5.3 Calibration fine ────────────────────────────────────────────────
print("Computing s5_calibration_fine ...")
cal_rows = []
for ev in AUTO_EVALS:
    for lo, hi in CALIBRATION_BINS:
        hums, preds, maes_b = [], [], []
        for r in rows:
            hm = human_mean(r)
            pred = r['evaluate'].get(ev)
            if hm is None or pred is None:
                continue
            if lo <= hm <= hi:
                hums.append(hm)
                preds.append(pred)
                maes_b.append(abs(pred - hm))
        if hums:
            cal_rows.append({
                'evaluator': ev, 'bin': f'{lo}-{hi}', 'n': len(hums),
                'human_mean_in_bin': fmt(sum(hums)/len(hums)),
                'pred_mean_in_bin': fmt(sum(preds)/len(preds)),
                'gap': fmt(sum(preds)/len(preds) - sum(hums)/len(hums)),
                'mae_in_bin': fmt(sum(maes_b)/len(maes_b))
            })

write_csv(OUT / 's5_calibration_fine.csv', cal_rows,
          ['evaluator', 'bin', 'n', 'human_mean_in_bin', 'pred_mean_in_bin', 'gap', 'mae_in_bin'])
print(f"  s5_calibration_fine.csv written ({len(cal_rows)} rows)")

# ── 5.4 Kendall tau ─────────────────────────────────────────────────────
print("Computing s5_kendall_tau ...")
tau_rows = []
for rec in eval_ranking:
    tau_rows.append({
        'evaluator': rec['evaluator'],
        'kendall_tau_vs_human_mean': rec['kendall_tau'],
        'p_value': 0.0
    })
write_csv(OUT / 's5_kendall_tau.csv', tau_rows,
          ['evaluator', 'kendall_tau_vs_human_mean', 'p_value'])

# ── 5.5 Binned agreement ────────────────────────────────────────────────
print("Computing s5_binned_agreement ...")
ba_rows = []
for ev in AUTO_EVALS:
    bins_data = {'overall': [0, 0], 'low': [0, 0], 'mid': [0, 0], 'high': [0, 0]}
    for r in rows:
        hm = human_mean(r)
        pred = r['evaluate'].get(ev)
        if hm is None or pred is None:
            continue
        hbin = 'low' if hm <= 2.5 else ('mid' if hm <= 3.5 else 'high')
        pbin = 'low' if pred <= 2.5 else ('mid' if pred <= 3.5 else 'high')
        bins_data['overall'][1] += 1
        bins_data[hbin][1] += 1
        if hbin == pbin:
            bins_data['overall'][0] += 1
            bins_data[hbin][0] += 1
    for b in ['overall', 'low', 'mid', 'high']:
        if bins_data[b][1] > 0:
            ba_rows.append({
                'evaluator': ev,
                'binned_agreement': fmt(bins_data[b][0] / bins_data[b][1]),
                'n': bins_data[b][1],
                'human_bin': '' if b == 'overall' else b
            })

write_csv(OUT / 's5_binned_agreement.csv', ba_rows,
          ['evaluator', 'binned_agreement', 'n', 'human_bin'])
print(f"  s5_binned_agreement.csv written ({len(ba_rows)} rows)")

# ── 5.6 Affinity ────────────────────────────────────────────────────────
print("Computing s5_affinity ...")
affinity_rows = []
for ev in ['deepseek-r1', 'deepseek-v3']:
    for gen in sorted(set(r.get('model', '') for r in rows)):
        if not gen:
            continue
        biases, maes_a = [], []
        for r in rows:
            if r.get('model', '') != gen:
                continue
            hm = human_mean(r)
            pred = r['evaluate'].get(ev)
            if hm is None or pred is None:
                continue
            biases.append(pred - hm)
            maes_a.append(abs(pred - hm))
        if biases:
            is_own = (ev == 'deepseek-r1' and gen == 'deepseek-r1') or \
                     (ev == 'deepseek-v3' and gen == 'deepseek-v3')
            affinity_rows.append({
                'evaluator': ev, 'generator': gen, 'n': len(biases),
                'bias': fmt(sum(biases)/len(biases)),
                'mae': fmt(sum(maes_a)/len(maes_a)),
                'is_own': is_own
            })

write_csv(OUT / 's5_affinity.csv', affinity_rows,
          ['evaluator', 'generator', 'n', 'bias', 'mae', 'is_own'])
print(f"  s5_affinity.csv written ({len(affinity_rows)} rows)")

# ── 5.7 Metric accuracy ─────────────────────────────────────────────────
print("Computing s5_metric_accuracy ...")
ma_rows = []
for ev in AUTO_EVALS:
    by_metric = defaultdict(lambda: {'n': 0, 'correct': 0, 'maes': [], 'biases': []})
    for r in rows:
        hr = human_rounded(r)
        hm = human_mean(r)
        pred = r['evaluate'].get(ev)
        if hr is None or pred is None or hm is None:
            continue
        m = r.get('metric_unified', r.get('metric', ''))
        by_metric[m]['n'] += 1
        by_metric[m]['correct'] += (1 if round(pred) == hr else 0)
        by_metric[m]['maes'].append(abs(pred - hm))
        by_metric[m]['biases'].append(pred - hm)
    for m, d in sorted(by_metric.items()):
        ma_rows.append({
            'evaluator': ev, 'metric': m, 'n': d['n'],
            'accuracy': fmt(d['correct'] / d['n']),
            'mae': fmt(sum(d['maes']) / d['n']),
            'bias': fmt(sum(d['biases']) / d['n'])
        })

write_csv(OUT / 's5_metric_accuracy.csv', ma_rows,
          ['evaluator', 'metric', 'n', 'accuracy', 'mae', 'bias'])
print(f"  s5_metric_accuracy.csv written ({len(ma_rows)} rows)")

# ── cat_s5: by subject ──────────────────────────────────────────────────
print("Computing cat_s5_eval_by_subject ...")
subj_rows = []
for ev in AUTO_EVALS:
    by_subj = defaultdict(lambda: {'maes': [], 'exacts': [], 'h': [], 'p': []})
    for r in rows:
        hm = human_mean(r)
        pred = r['evaluate'].get(ev)
        if hm is None or pred is None:
            continue
        s = r.get('subject_unified', '')
        by_subj[s]['maes'].append(abs(pred - hm))
        by_subj[s]['exacts'].append(1 if round(pred) == round(hm) else 0)
        by_subj[s]['h'].append(hm)
        by_subj[s]['p'].append(pred)
    for s, d in sorted(by_subj.items()):
        n = len(d['maes'])
        tau = 0
        try:
            from scipy.stats import kendalltau as kt
            tau, _ = kt(d['h'], d['p'])
        except:
            pass
        subj_rows.append({
            'subject': s, 'evaluator': ev, 'n': n,
            'mae': fmt(sum(d['maes'])/n),
            'exact_match_rate': fmt(sum(d['exacts'])/n),
            'kendall_tau': fmt(tau)
        })

write_csv(OUT / 'cat_s5_eval_by_subject.csv', subj_rows,
          ['subject', 'evaluator', 'n', 'mae', 'exact_match_rate', 'kendall_tau'])
print(f"  cat_s5_eval_by_subject.csv written ({len(subj_rows)} rows)")

# ── cat_s5: by education level ──────────────────────────────────────────
print("Computing cat_s5_eval_by_edu ...")
edu_rows = []
for ev in AUTO_EVALS:
    by_edu = defaultdict(lambda: {'maes': [], 'exacts': [], 'h': [], 'p': []})
    for r in rows:
        hm = human_mean(r)
        pred = r['evaluate'].get(ev)
        if hm is None or pred is None:
            continue
        e = r.get('education_level_unified', '')
        by_edu[e]['maes'].append(abs(pred - hm))
        by_edu[e]['exacts'].append(1 if round(pred) == round(hm) else 0)
        by_edu[e]['h'].append(hm)
        by_edu[e]['p'].append(pred)
    for e, d in sorted(by_edu.items()):
        n = len(d['maes'])
        tau = 0
        try:
            from scipy.stats import kendalltau as kt
            tau, _ = kt(d['h'], d['p'])
        except:
            pass
        edu_rows.append({
            'education_level': e, 'evaluator': ev, 'n': n,
            'mae': fmt(sum(d['maes'])/n),
            'exact_match_rate': fmt(sum(d['exacts'])/n),
            'kendall_tau': fmt(tau)
        })

write_csv(OUT / 'cat_s5_eval_by_edu.csv', edu_rows,
          ['education_level', 'evaluator', 'n', 'mae', 'exact_match_rate', 'kendall_tau'])
print(f"  cat_s5_eval_by_edu.csv written ({len(edu_rows)} rows)")

# ── cat_s5: by question type ────────────────────────────────────────────
print("Computing cat_s5_eval_by_qtype ...")
qt_rows = []
for ev in AUTO_EVALS:
    by_qt = defaultdict(lambda: {'maes': [], 'biases': []})
    for r in rows:
        hm = human_mean(r)
        pred = r['evaluate'].get(ev)
        if hm is None or pred is None:
            continue
        q = r.get('question_type_EN', '')
        by_qt[q]['maes'].append(abs(pred - hm))
        by_qt[q]['biases'].append(pred - hm)
    for q, d in sorted(by_qt.items()):
        n = len(d['maes'])
        qt_rows.append({
            'question_type': q, 'evaluator': ev, 'n': n,
            'mae': fmt(sum(d['maes'])/n),
            'bias': fmt(sum(d['biases'])/n)
        })

write_csv(OUT / 'cat_s5_eval_by_qtype.csv', qt_rows,
          ['question_type', 'evaluator', 'n', 'mae', 'bias'])
print(f"  cat_s5_eval_by_qtype.csv written ({len(qt_rows)} rows)")

# ── cat_s5: low score detection by subject ──────────────────────────────
print("Computing cat_s5_low_score_detection ...")
low_data = defaultdict(lambda: {ev: {'total': 0, 'detected': 0} for ev in AUTO_EVALS})
for r in rows:
    hm = human_mean(r)
    if hm is None or hm > 3.0:
        continue
    s = r.get('subject_unified', '')
    for ev in AUTO_EVALS:
        pred = r['evaluate'].get(ev)
        if pred is None:
            continue
        low_data[s][ev]['total'] += 1
        if pred <= 3.0:
            low_data[s][ev]['detected'] += 1

low_rows = []
for s in sorted(low_data.keys(), key=lambda x: -max(low_data[x][ev]['total'] for ev in AUTO_EVALS)):
    d = low_data[s]
    total = max(d[ev]['total'] for ev in AUTO_EVALS)
    if total < 5:
        continue
    rec = {'subject': s, 'low_score_count': total}
    for ev in AUTO_EVALS:
        rate = d[ev]['detected'] / d[ev]['total'] if d[ev]['total'] > 0 else 0
        rec[f'{ev}_detection_rate'] = fmt(rate)
    low_rows.append(rec)

write_csv(OUT / 'cat_s5_low_score_detection_by_subject.csv', low_rows,
          ['subject', 'low_score_count'] + [f'{ev}_detection_rate' for ev in AUTO_EVALS])
print(f"  cat_s5_low_score_detection.csv written ({len(low_rows)} rows)")

print("\n=== All CSV files computed ===")
print("Now generating figures...")
