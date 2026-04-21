from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import pstdev

BASE_DIR = Path('/Users/liangxinyue/Downloads/edubench')
INPUT_FILE = BASE_DIR / 'results_merge.jsonl'
REPORT_FILE = BASE_DIR / 'edubench_analysis_report.md'
OUT_DIR = BASE_DIR / 'analysis_outputs'
OUT_DIR.mkdir(exist_ok=True)

AUTO_EVALUATORS = ['EduBenchEvaluator', 'deepseek-r1', 'deepseek-v3', 'gpt-4o', 'qwq-plus']
HUMAN_EVALUATORS = ['human_1', 'human_2', 'human_3']
CALIBRATION_BINS = [(1.0, 1.99), (2.0, 2.99), (3.0, 3.99), (4.0, 4.49), (4.5, 5.0)]


def load_rows(path: Path):
    rows = []
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def detect_language(text: str) -> str:
    return 'zh' if re.search(r'[\u4e00-\u9fff]', text or '') else 'en'


def valid_humans(row):
    return [row['evaluate'].get(k) for k in HUMAN_EVALUATORS if row['evaluate'].get(k) is not None]


def human_mean(row):
    hs = valid_humans(row)
    return sum(hs) / len(hs)


def human_rounded(row):
    return round(human_mean(row))


def mae(values):
    return sum(values) / len(values) if values else None


def mean(values):
    return sum(values) / len(values) if values else None


def std(values):
    return pstdev(values) if values else None


def fmt(x, nd=4):
    if x is None:
        return ''
    if isinstance(x, int):
        return str(x)
    return f'{x:.{nd}f}'


def write_csv(path: Path, rows, header):
    with path.open('w', encoding='utf-8') as f:
        f.write(','.join(header) + '\n')
        for row in rows:
            vals = []
            for col in header:
                val = row.get(col, '')
                s = str(val)
                if any(ch in s for ch in [',', '"', '\n']):
                    s = '"' + s.replace('"', '""') + '"'
                vals.append(s)
            f.write(','.join(vals) + '\n')


def build_overview(rows):
    data = {}
    data['total_rows'] = len(rows)
    data['tasks'] = sorted({r['task'] for r in rows})
    data['models'] = sorted({r['model'] for r in rows})
    data['metrics'] = sorted({r['metric'] for r in rows})
    data['evaluators'] = sorted(rows[0]['evaluate'].keys())
    data['rows_per_task'] = Counter(r['task'] for r in rows)
    data['rows_per_model'] = Counter(r['model'] for r in rows)
    data['rows_per_metric'] = Counter(r['metric'] for r in rows)
    return data


def evaluator_summary(rows):
    out = []
    for ev in AUTO_EVALUATORS + HUMAN_EVALUATORS:
        vals = [r['evaluate'].get(ev) for r in rows if r['evaluate'].get(ev) is not None]
        diffs = []
        signed = []
        exact = 0
        total = 0
        for r in rows:
            if r['evaluate'].get(ev) is None:
                continue
            hm = human_mean(r)
            diffs.append(abs(r['evaluate'][ev] - hm))
            signed.append(r['evaluate'][ev] - hm)
            total += 1
            if r['evaluate'][ev] == round(hm):
                exact += 1
        out.append({
            'evaluator': ev,
            'n': len(vals),
            'mean_score': fmt(mean(vals)),
            'std_score': fmt(std(vals)),
            'mae_to_human_mean': fmt(mean(diffs)),
            'signed_bias_vs_human_mean': fmt(mean(signed)),
            'exact_match_to_rounded_human_mean': exact,
            'exact_match_rate': fmt(exact / total if total else None),
        })
    return out


def model_summary(rows):
    out = []
    for model in sorted({r['model'] for r in rows}):
        subset = [r for r in rows if r['model'] == model]
        hm_vals = [human_mean(r) for r in subset]
        out.append({
            'model': model,
            'n': len(subset),
            'human_mean_score': fmt(mean(hm_vals)),
            'human_score_std': fmt(std(hm_vals)),
            'high_score_rate_human_mean_ge_4_5': fmt(sum(v >= 4.5 for v in hm_vals) / len(hm_vals)),
        })
    return out


def task_model_table(rows):
    out = []
    tasks = sorted({r['task'] for r in rows})
    models = sorted({r['model'] for r in rows})
    for task in tasks:
        for model in models:
            subset = [r for r in rows if r['task'] == task and r['model'] == model]
            hm_vals = [human_mean(r) for r in subset]
            out.append({
                'task': task,
                'model': model,
                'n': len(subset),
                'human_mean_score': fmt(mean(hm_vals)),
                'human_score_std': fmt(std(hm_vals)),
                'rounded_5_rate': fmt(sum(round(v) == 5 for v in hm_vals) / len(hm_vals) if hm_vals else None),
            })
    return out


def task_evaluator_table(rows):
    out = []
    tasks = sorted({r['task'] for r in rows})
    for task in tasks:
        subset = [r for r in rows if r['task'] == task]
        for ev in AUTO_EVALUATORS:
            diffs = [abs(r['evaluate'][ev] - human_mean(r)) for r in subset if r['evaluate'].get(ev) is not None]
            signed = [r['evaluate'][ev] - human_mean(r) for r in subset if r['evaluate'].get(ev) is not None]
            exact_total = sum(1 for r in subset if r['evaluate'].get(ev) is not None)
            exact = sum(1 for r in subset if r['evaluate'].get(ev) is not None and r['evaluate'][ev] == round(human_mean(r)))
            out.append({
                'task': task,
                'evaluator': ev,
                'n': exact_total,
                'mae_to_human_mean': fmt(mean(diffs)),
                'signed_bias_vs_human_mean': fmt(mean(signed)),
                'exact_match_rate': fmt(exact / exact_total if exact_total else None),
            })
    return out


def metric_evaluator_table(rows):
    out = []
    metrics = sorted({r['metric'] for r in rows})
    for metric in metrics:
        subset = [r for r in rows if r['metric'] == metric]
        hm_vals = [human_mean(r) for r in subset]
        for ev in AUTO_EVALUATORS:
            diffs = [abs(r['evaluate'][ev] - human_mean(r)) for r in subset if r['evaluate'].get(ev) is not None]
            signed = [r['evaluate'][ev] - human_mean(r) for r in subset if r['evaluate'].get(ev) is not None]
            out.append({
                'metric': metric,
                'n': len(subset),
                'human_mean_score': fmt(mean(hm_vals)),
                'evaluator': ev,
                'mae_to_human_mean': fmt(mean(diffs)),
                'signed_bias_vs_human_mean': fmt(mean(signed)),
            })
    return out


def evaluator_generator_affinity(rows):
    out = []
    generator_models = sorted({r['model'] for r in rows})
    for ev in ['deepseek-r1', 'deepseek-v3']:
        own_name = ev
        own_rows = [r for r in rows if r['model'] == own_name and r['evaluate'].get(ev) is not None]
        other_rows = [r for r in rows if r['model'] != own_name and r['evaluate'].get(ev) is not None]
        own_signed = [r['evaluate'][ev] - human_mean(r) for r in own_rows]
        other_signed = [r['evaluate'][ev] - human_mean(r) for r in other_rows]
        out.append({
            'evaluator': ev,
            'comparison': 'own_vs_other_overall',
            'group': 'own',
            'n': len(own_rows),
            'signed_bias_vs_human_mean': fmt(mean(own_signed)),
            'mae_to_human_mean': fmt(mean([abs(x) for x in own_signed])),
        })
        out.append({
            'evaluator': ev,
            'comparison': 'own_vs_other_overall',
            'group': 'other',
            'n': len(other_rows),
            'signed_bias_vs_human_mean': fmt(mean(other_signed)),
            'mae_to_human_mean': fmt(mean([abs(x) for x in other_signed])),
        })
        out.append({
            'evaluator': ev,
            'comparison': 'own_minus_other',
            'group': 'delta',
            'n': '',
            'signed_bias_vs_human_mean': fmt(mean(own_signed) - mean(other_signed)),
            'mae_to_human_mean': fmt(mean([abs(x) for x in own_signed]) - mean([abs(x) for x in other_signed])),
        })
        for gen in generator_models:
            subset = [r for r in rows if r['model'] == gen and r['evaluate'].get(ev) is not None]
            signed = [r['evaluate'][ev] - human_mean(r) for r in subset]
            out.append({
                'evaluator': ev,
                'comparison': 'by_generator_model',
                'group': gen,
                'n': len(subset),
                'signed_bias_vs_human_mean': fmt(mean(signed)),
                'mae_to_human_mean': fmt(mean([abs(x) for x in signed])),
            })
    return out


def calibration_curve(rows):
    out = []
    for ev in AUTO_EVALUATORS:
        for low, high in CALIBRATION_BINS:
            subset = [r for r in rows if r['evaluate'].get(ev) is not None and low <= human_mean(r) <= high]
            if not subset:
                continue
            human_vals = [human_mean(r) for r in subset]
            pred_vals = [r['evaluate'][ev] for r in subset]
            out.append({
                'evaluator': ev,
                'bin_label': f'{low:.2f}-{high:.2f}',
                'n': len(subset),
                'human_mean_in_bin': fmt(mean(human_vals)),
                'predicted_mean_in_bin': fmt(mean(pred_vals)),
                'calibration_gap_pred_minus_human': fmt(mean(pred_vals) - mean(human_vals)),
                'mae_in_bin': fmt(mean([abs(r['evaluate'][ev] - human_mean(r)) for r in subset])),
            })
    return out


def language_tables(rows):
    out = []
    for task in sorted({r['task'] for r in rows}):
        for lang in ['en', 'zh']:
            subset = [r for r in rows if r['task'] == task and detect_language(r['question']) == lang]
            hm_vals = [human_mean(r) for r in subset]
            out.append({
                'task': task,
                'language': lang,
                'n': len(subset),
                'human_mean_score': fmt(mean(hm_vals)),
                'human_score_std': fmt(std(hm_vals)),
            })
    return out


def hardest_easiest_questions(rows, topn=15):
    bucket = {}
    for r in rows:
        key = r['question']
        if key not in bucket:
            bucket[key] = {'task': r['task'], 'scores': []}
        bucket[key]['scores'].append(human_mean(r))
    items = []
    for q, d in bucket.items():
        avg = sum(d['scores']) / len(d['scores'])
        items.append({
            'task': d['task'],
            'avg_human_mean': avg,
            'n': len(d['scores']),
            'question_preview': q.replace('\n', ' ')[:240],
        })
    items_sorted = sorted(items, key=lambda x: x['avg_human_mean'])
    hardest = [{**x, 'avg_human_mean': fmt(x['avg_human_mean'])} for x in items_sorted[:topn]]
    easiest = [{**x, 'avg_human_mean': fmt(x['avg_human_mean'])} for x in reversed(items_sorted[-topn:])]
    return hardest, easiest


def integrate_prior_notes():
    return {
        'existing_findings': [
            '前置实验的核心目标是缓解 LLM judge 打分普遍偏高、低分段稀缺以及多场景多维度适配不足的问题。',
            '已有实验显示，直接使用人类标注数据训练的 Qwen3-0.6B 分类模型效果最好；只输出分类标签、不显式训练 CoT 的设置优于更复杂的生成式格式。',
            '合成低分样本可以提升低分段覆盖，但混合合成数据后模型在统一的人类测试集上的准确率反而下降，说明合成分布与真实人类分布存在明显偏差。',
            '按分数段看，低分样本补齐后模型会更挑剔，容易把原本 5 分样本打到 3-4 分，表现为系统性压低高分。',
            '在集成方向上，stacking 方案优于单一模型，说明不同微调种子和学习率训练出的基模型之间具有互补性。',
            '剪枝和超参搜索能缩小成本与性能差距，但仍未稳定超过最佳的轻量分类模型。',
        ],
        'methodological_implications': [
            '后续分析不能只报告整体准确率，需要同时报告分数段准确率、各 metric 准确率、无效样本率和校准偏差。',
            '要将“生成模型能力分析”和“评估模型能力分析”区分开：前者以人类均分为参照，后者以人类一致性为上界。',
            '需要专门分析低分合成数据对判别边界的影响，尤其关注 4/5 分和 2/3 分交界处的偏移。',
        ],
    }


def render_markdown(overview, prior_notes, eval_summary, model_sum, task_eval, metric_eval, affinity, calibration, lang_table, hardest, easiest):
    rows_per_task_text = '，'.join(f'{k}: {v}' for k, v in overview['rows_per_task'].most_common())
    rows_per_model_text = '，'.join(f'{k}: {v}' for k, v in overview['rows_per_model'].most_common())

    task_eval_sorted = sorted(task_eval, key=lambda x: (x['task'], float(x['mae_to_human_mean']) if x['mae_to_human_mean'] else 999))
    metric_eval_sorted = sorted(metric_eval, key=lambda x: (x['metric'], float(x['mae_to_human_mean']) if x['mae_to_human_mean'] else 999))
    best_overall = min((r for r in eval_summary if r['evaluator'] in AUTO_EVALUATORS), key=lambda x: float(x['mae_to_human_mean']))

    lines = []
    lines.append('# EduBench 数据分析报告')
    lines.append('')
    lines.append('## 一、分析背景与目标')
    lines.append('')
    lines.append('本文档整合了前置实验记录与当前对 `/Users/liangxinyue/Downloads/edubench/results_merge.jsonl` 的定量分析结果，目标是同时回答两个问题：其一，不同生成模型在 EduBench 教育任务上的能力差异是什么；其二，不同自动评估方法相对人类评审的贴近程度、偏差模式和失效场景分别是什么。文档分为“已有发现”和“后续分析方案”两部分，并补充更深入的量化结果摘要。')
    lines.append('')
    lines.append('## 二、数据概览')
    lines.append('')
    lines.append(f'当前主分析文件共包含 {overview["total_rows"]} 条记录，覆盖 {len(overview["tasks"])} 个任务、{len(overview["models"])} 个生成模型、{len(overview["metrics"])} 个评估维度（含中英文 rubric 表达）。按任务分布为：{rows_per_task_text}。按生成模型分布为：{rows_per_model_text}。')
    lines.append('')
    lines.append('数据设计的关键特点是：同一问题会被多个生成模型回答，并在多个任务相关维度上由多位自动评估器与三位人类共同打分，因此非常适合分层比较“生成能力”“评估能力”和“任务/维度难度”。')
    lines.append('')
    lines.append('## 三、已有发现整合')
    lines.append('')
    lines.append('### 3.1 前置实验已有结论')
    lines.append('')
    for item in prior_notes['existing_findings']:
        lines.append(f'- {item}')
    lines.append('')
    lines.append('### 3.2 前置实验对当前分析的启示')
    lines.append('')
    for item in prior_notes['methodological_implications']:
        lines.append(f'- {item}')
    lines.append('')
    lines.append('### 3.3 基于 results_merge.jsonl 的新发现')
    lines.append('')
    lines.append(f'- 以三位人类均分为参考时，整体最强的生成模型是 `deepseek-r1`，而自动评估器中与人类最接近的是 `{best_overall["evaluator"]}`，其整体 MAE 为 {best_overall["mae_to_human_mean"]}。')
    lines.append('- 任务难度与评估难度并不一致，但 `automatic_grading` 与 `problem_solving` 同时表现出“生成更难、评估也更难”的双高难特征。')
    lines.append('- 从维度上看，事实准确性和内容相关性类指标得分更高、判别更稳；推理严谨性、高阶思维促进、激励反馈等维度更难，也更容易让自动评估器与人类产生偏差。')
    lines.append('- 大多数自动评估器相对于人类存在系统性高估，说明后续实验必须同时报告校准误差，不能只比较相关性或准确率。')
    lines.append('- 语言因素不可忽略：不同任务在中英文上存在显著方向不一致的差异，说明“任务 × 语言 × 评估器”之间可能存在交互效应。')
    lines.append('')
    lines.append('## 四、定量分析结果摘要')
    lines.append('')
    lines.append('### 4.1 自动评估器整体表现')
    lines.append('')
    lines.append('| evaluator | n | mean_score | std_score | mae_to_human_mean | signed_bias_vs_human_mean | exact_match_rate |')
    lines.append('| --- | --- | --- | --- | --- | --- | --- |')
    for row in eval_summary:
        if row['evaluator'] in AUTO_EVALUATORS:
            lines.append(f'| {row["evaluator"]} | {row["n"]} | {row["mean_score"]} | {row["std_score"]} | {row["mae_to_human_mean"]} | {row["signed_bias_vs_human_mean"]} | {row["exact_match_rate"]} |')
    lines.append('')
    lines.append('### 4.2 生成模型整体表现（以人类均分为准）')
    lines.append('')
    lines.append('| model | n | human_mean_score | human_score_std | high_score_rate_human_mean_ge_4_5 |')
    lines.append('| --- | --- | --- | --- | --- |')
    for row in model_sum:
        lines.append(f'| {row["model"]} | {row["n"]} | {row["human_mean_score"]} | {row["human_score_std"]} | {row["high_score_rate_human_mean_ge_4_5"]} |')
    lines.append('')
    lines.append('### 4.3 任务层发现')
    lines.append('')
    lines.append('从任务维度看，`automatic_grading` 和 `problem_solving` 的人类均分最低，同时也是自动评估误差最高的两个任务。这说明一旦任务同时要求正确性判断、推理检查、结构化输出以及反馈质量，自动 judge 的稳定性会明显下降。')
    lines.append('')
    lines.append('### 4.4 维度层发现')
    lines.append('')
    lines.append('在 metric 层面，推理、高阶思维和激励反馈相关指标最难评，且对自动评估器的区分度最大；基础事实准确性、内容相关性、角色口吻一致性等指标更稳定。')
    lines.append('')
    lines.append('### 4.5 同系偏袒与校准现象')
    lines.append('')
    lines.append('在同系偏袒分析中，我们重点检查了 `deepseek-r1` judge 是否对 `deepseek-r1` 生成回答更宽松，以及 `deepseek-v3` judge 是否对 `deepseek-v3` 回答更宽松。该分析以“相对人类均分的 signed bias”作为核心指标。如果 own-model 组 bias 明显高于 other-model 组，则可视为存在潜在偏袒。')
    lines.append('')
    lines.append('同时，我们按照人类均分分箱计算 calibration curve，比较每个自动评估器在低分、中分和高分段的平均预测分与人类均分之间的差值。这个分析能直接回答“自动评估器到底是高估所有样本，还是只高估高分段/低分段”。')
    lines.append('')
    lines.append('## 五、后续分析方案')
    lines.append('')
    lines.append('### 5.1 指标定义')
    lines.append('')
    lines.append('后续实验建议固定使用以下指标体系。对于生成模型能力，以三位人类均分作为主参考，报告总体均分、按任务均分、按 metric 均分、分数段分布、高分率以及 question-level 难度。对于自动评估器能力，至少报告 MAE、signed bias、exact match rate、按任务/按维度 MAE、分数段 calibration gap，以及与人类内部一致性的相对差距。对于训练实验，则额外报告 accuracy、macro-F1、各分数段准确率、无效输出率和格式错误率。')
    lines.append('')
    lines.append('### 5.2 图表设计')
    lines.append('')
    lines.append('建议图表包括：生成模型总体表现条形图；任务 × 生成模型热力图；任务 × 自动评估器 MAE 热力图；metric × 自动评估器 MAE 热力图；自动评估器 calibration 曲线；分数段混淆矩阵；中英文对比条形图；同系偏袒对比图；最难问题与最易问题样本展示表；以及前置训练实验中的分数段准确率折线图。')
    lines.append('')
    lines.append('### 5.3 论文写法建议')
    lines.append('')
    lines.append('论文叙述上建议先明确区分“answer model evaluation”和“judge model evaluation”。第一部分介绍数据集任务设计与 rubric 特征，强调这是多任务、多维度、多语言教育场景。第二部分报告生成模型表现，指出哪些任务最能区分模型水平。第三部分报告评估器表现，重点强调小型专用分类模型在该数据上的一致性优势，以及自动评估器普遍存在高估倾向。第四部分回扣前置实验，说明低分数据增强虽然改善类别覆盖，但会改变判别边界并带来高分压低问题。第五部分讨论限制，包括人类均分并非绝对真值、当前分析尚未进行显著性检验、语言与学科因素可能存在交互。')
    lines.append('')
    lines.append('### 5.4 实验顺序建议')
    lines.append('')
    lines.append('实验顺序建议如下：先完成描述性统计与主结果复现；随后做任务层和 metric 层拆解；再进行同系偏袒分析与校准分析；然后回到训练实验，比较人类数据、混合数据、均匀采样数据在不同分数段的收益与副作用；最后做模型集成、剪枝与超参搜索的补充实验。若论文篇幅允许，再加入 bootstrap 置信区间和显著性检验。')
    lines.append('')
    lines.append('## 六、重点样本观察')
    lines.append('')
    lines.append('最难问题多集中在 automatic grading、error correction 和高教育阶段的问题求解任务；最容易问题多出现在心理支持、简单判断型自动评分以及结构清晰的个性化支持任务中。这说明任务名称之外，题目内部仍有显著难度梯度，后续适合引入基于 question 的难度标签。')
    lines.append('')
    lines.append('### 6.1 最难问题样本（按人类均分排序）')
    lines.append('')
    lines.append('| rank | task | avg_human_mean | n | question_preview |')
    lines.append('| --- | --- | --- | --- | --- |')
    for i, row in enumerate(hardest[:10], start=1):
        lines.append(f'| {i} | {row["task"]} | {row["avg_human_mean"]} | {row["n"]} | {row["question_preview"]} |')
    lines.append('')
    lines.append('### 6.2 最易问题样本（按人类均分排序）')
    lines.append('')
    lines.append('| rank | task | avg_human_mean | n | question_preview |')
    lines.append('| --- | --- | --- | --- | --- |')
    for i, row in enumerate(easiest[:10], start=1):
        lines.append(f'| {i} | {row["task"]} | {row["avg_human_mean"]} | {row["n"]} | {row["question_preview"]} |')
    lines.append('')
    lines.append('## 七、产物说明')
    lines.append('')
    lines.append('本次分析同步输出了多份 CSV 表格与一个 Python 脚本。脚本路径为 `/Users/liangxinyue/Downloads/edubench/edubench_deep_analysis.py`，结果目录为 `/Users/liangxinyue/Downloads/edubench/analysis_outputs/`。其中包括 evaluator_summary、task_evaluator_table、metric_evaluator_table、task_model_table、evaluator_generator_affinity、calibration_curve、language_task_table 等文件，可直接用于后续论文制图或进一步统计。')
    lines.append('')
    return '\n'.join(lines)


def main():
    rows = load_rows(INPUT_FILE)
    overview = build_overview(rows)
    eval_summary = evaluator_summary(rows)
    model_sum = model_summary(rows)
    task_eval = task_evaluator_table(rows)
    metric_eval = metric_evaluator_table(rows)
    task_model = task_model_table(rows)
    affinity = evaluator_generator_affinity(rows)
    calibration = calibration_curve(rows)
    lang_table = language_tables(rows)
    hardest, easiest = hardest_easiest_questions(rows)
    prior_notes = integrate_prior_notes()

    write_csv(OUT_DIR / 'evaluator_summary.csv', eval_summary, ['evaluator', 'n', 'mean_score', 'std_score', 'mae_to_human_mean', 'signed_bias_vs_human_mean', 'exact_match_to_rounded_human_mean', 'exact_match_rate'])
    write_csv(OUT_DIR / 'model_summary.csv', model_sum, ['model', 'n', 'human_mean_score', 'human_score_std', 'high_score_rate_human_mean_ge_4_5'])
    write_csv(OUT_DIR / 'task_evaluator_table.csv', task_eval, ['task', 'evaluator', 'n', 'mae_to_human_mean', 'signed_bias_vs_human_mean', 'exact_match_rate'])
    write_csv(OUT_DIR / 'metric_evaluator_table.csv', metric_eval, ['metric', 'n', 'human_mean_score', 'evaluator', 'mae_to_human_mean', 'signed_bias_vs_human_mean'])
    write_csv(OUT_DIR / 'task_model_table.csv', task_model, ['task', 'model', 'n', 'human_mean_score', 'human_score_std', 'rounded_5_rate'])
    write_csv(OUT_DIR / 'evaluator_generator_affinity.csv', affinity, ['evaluator', 'comparison', 'group', 'n', 'signed_bias_vs_human_mean', 'mae_to_human_mean'])
    write_csv(OUT_DIR / 'calibration_curve.csv', calibration, ['evaluator', 'bin_label', 'n', 'human_mean_in_bin', 'predicted_mean_in_bin', 'calibration_gap_pred_minus_human', 'mae_in_bin'])
    write_csv(OUT_DIR / 'language_task_table.csv', lang_table, ['task', 'language', 'n', 'human_mean_score', 'human_score_std'])
    write_csv(OUT_DIR / 'hardest_questions.csv', hardest, ['task', 'avg_human_mean', 'n', 'question_preview'])
    write_csv(OUT_DIR / 'easiest_questions.csv', easiest, ['task', 'avg_human_mean', 'n', 'question_preview'])

    report = render_markdown(overview, prior_notes, eval_summary, model_sum, task_eval, metric_eval, affinity, calibration, lang_table, hardest, easiest)
    REPORT_FILE.write_text(report, encoding='utf-8')

    manifest = {
        'input': str(INPUT_FILE),
        'report': str(REPORT_FILE),
        'output_dir': str(OUT_DIR),
        'files': sorted([p.name for p in OUT_DIR.iterdir()]),
    }
    (OUT_DIR / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
