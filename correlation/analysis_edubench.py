import pandas as pd
import json
import os

# ============================================================
# 以下函数与原 correlation/analysis.py 保持完全一致，不做修改
# ============================================================

def save_to_json(data, file_path, indent=4, ensure_ascii=False):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)

def fill_missing_with_mean(df):
    """
    用列的平均值填充CSV文件中的空值并保存
    """
    for column in df.select_dtypes(include=['number']).columns:
        if df[column].isnull().any():
            mean_value = df[column].mean()
            df[column].fillna(mean_value, inplace=True)
    return df

def split_and_fill_data(input_file: str = None, output_folder: str = '.'):
    """
    1. 划分不同模型的数据
    2. 使用模型数据填充下空白数据
    """
    df = pd.read_csv(input_file)
    if 'human' in input_file:
        df = fill_missing_with_mean(df)
        df.to_csv(input_file.replace(".csv", "filled.csv"), index=False)
    os.makedirs(output_folder, exist_ok=True)
    for eval_model, group in df.groupby('eval_model'):
        # 1. 补充数据
        group = fill_missing_with_mean(group)
        # 2. 保存数据
        output_file = os.path.join(output_folder, f"eval_score_{eval_model}.csv")
        group.to_csv(output_file, index=False)

# ============================================================
# 以下为针对 edubench/results_merge_enriched.jsonl 的新数据处理代码
# ============================================================

# edubench 数据中的评估维度（与原脚本 dim_columns 保持一致的命名）
DIM_COLUMNS = [
    'Content Relevance & Scope Control',
    'Reasoning Process Rigor',
    'Error Identification & Correction Precision',
    'Scenario Element Integration',
    'Clarity, Simplicity & Inspiration',
    'Basic Factual Accuracy',
    'Role & Tone Consistency',
    'Personalization, Adaptation & Learning Support',
    'Higher-Order Thinking & Skill Development',
    'Motivation, Guidance & Positive Feedback',
    'Domain Knowledge Accuracy',
    'Instruction Following & Task Completion',
]

def load_jsonl(file_path):
    """读取 JSONL 文件，返回记录列表"""
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def build_wide_df(records):
    """
    将 JSONL 记录转换为宽表格式，与原脚本 CSV 格式对齐。

    原脚本 pivot_table 逻辑：
        index='question_id', columns='gen_model', values=<dim>
    即：同一个 question_id 下，不同 gen_model 各有一个该维度的分数。

    edubench 数据结构：
        - 每条记录对应一个 (question, gen_model, metric) 三元组
        - 每个 question 有 5 个 gen_model
        - 每个 (question, gen_model) 有若干个 metric（不一定全部12个）

    因此，正确的 question_id 应对应 (question, metric) 组合，
    这样 pivot 后每行是一个 (question, metric) 对，
    每列是一个 gen_model，值是该评估者对该 gen_model 在该 metric 上的打分。
    每行有 5 个值（5 个 gen_model），与原脚本逻辑一致。

    输出列：
        question_id, gen_model, eval_model, task, language,
        <dim_1>, <dim_2>, ..., <dim_12>

    注意：每行只有一个维度有值（对应该记录的 metric），其余维度为 NaN，
    经过 fill_missing_with_mean 后用均值填充。
    """
    rows = []
    for rec in records:
        question = rec['question']
        gen_model = rec['model']
        dim = rec.get('metric_unified', rec.get('metric', ''))
        evaluate = rec.get('evaluate', {})
        task = rec.get('task', '')
        language = rec.get('language', '')

        for eval_model, score in evaluate.items():
            row = {
                'question': question,
                'gen_model': gen_model,
                'eval_model': eval_model,
                'task': task,
                'language': language,
            }
            # 只填充当前记录对应的维度，其余维度留 NaN
            for d in DIM_COLUMNS:
                row[d] = score if d == dim else None
            rows.append(row)

    df = pd.DataFrame(rows)

    # 对同一个 (question, gen_model, eval_model) 的多条记录（不同 metric）进行聚合，
    # 每个维度取其对应的非 NaN 值（每个维度最多只有一条记录有值）
    group_keys = ['question', 'gen_model', 'eval_model', 'task', 'language']
    df = df.groupby(group_keys, as_index=False)[DIM_COLUMNS].first()

    # 生成 question_id：对 (question, metric) 组合编号
    # 但由于我们已经聚合到 (question, gen_model, eval_model) 级别，
    # question_id 应对应 question（每个 question 下有多个 gen_model）
    # 这样 pivot_table(index='question_id', columns='gen_model') 才能得到
    # 每行有多个 gen_model 值的矩阵
    question_map = {q: i+1 for i, q in enumerate(df['question'].unique())}
    df['question_id'] = df['question'].map(question_map)

    return df


def convert_jsonl_to_split_csvs(jsonl_path: str, output_folder: str):
    """
    读取 edubench JSONL 文件，按 eval_model 拆分并用均值填充空值，
    输出格式与原 split_and_fill_data 产出的 CSV 完全一致。
    """
    print(f"[analysis_edubench] 读取数据: {jsonl_path}")
    records = load_jsonl(jsonl_path)
    print(f"[analysis_edubench] 共 {len(records)} 条记录")

    df = build_wide_df(records)
    print(f"[analysis_edubench] 宽表行数: {len(df)}, 列数: {len(df.columns)}")

    os.makedirs(output_folder, exist_ok=True)

    for eval_model, group in df.groupby('eval_model'):
        group = group.copy()
        # 用均值填充空值（与原 fill_missing_with_mean 逻辑一致）
        group = fill_missing_with_mean(group)
        output_file = os.path.join(output_folder, f"eval_score_{eval_model}.csv")
        group.to_csv(output_file, index=False)
        print(f"[analysis_edubench] 已保存: {output_file}  (行数: {len(group)})")

    print(f"[analysis_edubench] 全部完成，输出目录: {output_folder}")


def generate_human_mean_csv(scores_folder: str, human_names: list = None):
    """
    读取已拆分的三个人类打分 CSV，对每行的各维度分数取均值，
    生成 eval_score_human_mean.csv，eval_model 列标记为 'human_mean'。

    参数:
        scores_folder: eval_scores_split_and_fill 目录路径
        human_names:   三个人类评估者的名称列表，默认 ['human_1', 'human_2', 'human_3']
    """
    if human_names is None:
        human_names = ['human_1', 'human_2', 'human_3']

    dfs = []
    for name in human_names:
        path = os.path.join(scores_folder, f"eval_score_{name}.csv")
        df = pd.read_csv(path)
        dfs.append(df)

    # 以 human_1 的结构为基准（行顺序、question_id、gen_model 等元信息列完全一致）
    base = dfs[0].copy()

    # 对每个维度列，取三个人类打分的逐行均值
    for dim in DIM_COLUMNS:
        scores = pd.concat([d[dim] for d in dfs], axis=1)
        base[dim] = scores.mean(axis=1)

    base['eval_model'] = 'human_mean'

    output_file = os.path.join(scores_folder, "eval_score_human_mean.csv")
    base.to_csv(output_file, index=False)
    print(f"[analysis_edubench] 已保存: {output_file}  (行数: {len(base)})")


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    JSONL_PATH = os.path.join(BASE_DIR, "..", "results_merge_enriched.jsonl")
    OUTPUT_FOLDER = os.path.join(BASE_DIR, "eval_scores_split_and_fill")
    convert_jsonl_to_split_csvs(JSONL_PATH, OUTPUT_FOLDER)
    generate_human_mean_csv(OUTPUT_FOLDER)
