import numpy as np
from scipy import stats
import pandas as pd
import math
import json
import os
import scipy
from sklearn.metrics import cohen_kappa_score
from collections import defaultdict
from scipy.stats import kendalltau, spearmanr

# edubench 数据中的评估者列表（4个模型评估者 + 3个人类 + 1个EduBenchEvaluator + 人类均值）
models = ["deepseek-r1", "gpt-4o", "qwq-plus", "deepseek-v3", "human_1", "human_2", "human_3", "EduBenchEvaluator", "human_mean"]

dim_columns = ['Content Relevance & Scope Control', 'Reasoning Process Rigor',
       'Error Identification & Correction Precision',
       'Scenario Element Integration', 'Clarity, Simplicity & Inspiration',
       'Basic Factual Accuracy', 'Role & Tone Consistency',
       'Personalization, Adaptation & Learning Support',
       'Higher-Order Thinking & Skill Development',
       'Motivation, Guidance & Positive Feedback', 'Domain Knowledge Accuracy',
       'Instruction Following & Task Completion']

# ============================================================
# 以下计算函数与原 correlation/correlation.py 保持完全一致，不做任何修改
# ============================================================

def save_to_json(data, file_path, indent=4, ensure_ascii=False):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)

def compute_kappa_single_point(scores_a, scores_b):
    """
    计算单个问题的 Kappa 系数
    """
    return cohen_kappa_score(scores_a, scores_b)

def compute_kappa_dataset(all_scores_a, all_scores_b):
    """
    对整个数据集计算平均 Kappa 系数
    忽略长度不一致或为空的样本
    """
    kappas = []
    for scores_a, scores_b in zip(all_scores_a, all_scores_b):
        if len(scores_a) != len(scores_b) or len(scores_a) == 0:
            continue
        kappa = compute_kappa_single_point(scores_a, scores_b)
        if math.isnan(kappa):
            continue
        kappas.append(kappa)
    
    return np.mean(kappas) if kappas else float('nan')

def compute_spearman_single_point(scores_a, scores_b):
    """
    计算单个问题的Spearman相关系数
    """
    return stats.spearmanr(scores_a, scores_b)

def compute_spearman_dataset(all_scores_a, all_scores_b):
    correlations = []
    for scores_a, scores_b in zip(all_scores_a, all_scores_b):
        corr, _ = compute_spearman_single_point(scores_a, scores_b)
        if math.isnan(corr):
            continue
        correlations.append(corr)
    return np.mean(correlations)

def create_score_matrices(df):
    score_matrices = {}
    for dim in dim_columns:
        pivot_df = pd.pivot_table(
            df, 
            values=dim, 
            index='question_id',
            columns='gen_model'
        )
        score_matrices[dim] = pivot_df.values.tolist()
    return score_matrices


def compute_rank_correlation(score_1, score_2, method='kendall'):
    """
    输入两个二维列表，表示两个模型/评分者对 N 个问题的打分，
    每个问题对应 4 个回复的分数。
    
    参数:
        score_1: 第一个评分者的二维列表 (N x 4)
        score_2: 第二个评分者的二维列表 (N x 4)
        method: 指定要计算的相关性类型：
                - 'kendall'：Kendall's W
                - 'spearman'：Spearman 等级相关系数
    
    返回:
        平均相关性得分（float）
    """

    def to_rank(scores):
        """将一组数值转换为 rank（处理并列）"""
        return scipy.stats.rankdata(scores, method='average').tolist()

    kendalls = []
    spearmans = []
    count = 0
    for s1, s2 in zip(score_1, score_2):
        # 转换为 rank
        r1 = to_rank(s1)
        r2 = to_rank(s2)

        # 计算 Kendall's W
        tau, _ = kendalltau(r1, r2)
        kendall_w = (tau + 1) / 2
        if math.isnan(kendall_w):
            # kendalls.append(0)
            # print(r1)
            # print(r2)
            # print(s1)
            # print(s2)
            # exit()
            continue
        else:
            kendalls.append(kendall_w)

        # 计算 Spearman

        rho, _ = spearmanr(s1, s2)
        if math.isnan(rho):
            continue
        else:
            spearmans.append(rho)
    # print(f"kendall fail:{count/len(score_1)}")
    if method == 'kendall':
        return np.mean(kendalls) if kendalls else float('nan')
    elif method == 'spearman':
        return np.mean(spearmans) if spearmans else float('nan')
    else:
        raise ValueError("method 必须是 'kendall' 或 'spearman'")

def compute_pairwise_correlation(tgt_save_path, model_score_file_1,model_score_file_2,model1,model2,corr="spearman"):
    df_1 = pd.read_csv(model_score_file_1)
    df_2 = pd.read_csv(model_score_file_2)

    score_matrix_mdoel_1 = create_score_matrices(df_1)
    score_matrix_mdoel_2 = create_score_matrices(df_2)
    correlation_score = {}
    tgt_save_path = f"{tgt_save_path}/{model1}_{model2}.json"
    correlation_score["eval_model"] = (model1,model2)
    score_mean = 0
    for dim in dim_columns:
        tmp_score_1 = score_matrix_mdoel_1[dim]
        tmp_score_2 = score_matrix_mdoel_2[dim]
        # if corr == "spearman":
        #     score = compute_spearman_dataset(tmp_score_1, tmp_score_2)
        # if corr == "kappa":
        #     score = compute_kappa_dataset(tmp_score_1, tmp_score_2)
        score = compute_rank_correlation(tmp_score_1, tmp_score_2, method=corr)
        if math.isnan(score):
            print(f"math.isnan(score):{math.isnan(score)}")
            score = 0
        correlation_score[dim] = score
        score_mean += score
    score_mean = round(score_mean/len(dim_columns), 4)
    correlation_score["mean"] = score_mean
    save_to_json(correlation_score, tgt_save_path)


def save_matrix(data_dir_path):
    output_dir = os.path.join(data_dir_path, "matrix_output")
    os.makedirs(output_dir, exist_ok=True)
    dim_columns_tmp = dim_columns + ["mean"]
    matrices = {dim: defaultdict(dict) for dim in dim_columns_tmp}
    for filename in os.listdir(data_dir_path):
        if filename.endswith(".json"):
            file_path = os.path.join(data_dir_path, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            model_a, model_b = data["eval_model"]
            for dim in dim_columns_tmp:
                score = data[dim]
                matrices[dim][model_a][model_b] = score
                matrices[dim][model_b][model_a] = score
    for dim in dim_columns_tmp:
        matrix = matrices[dim]
        full_matrix = []
        full_matrix_latex = []
        full_matrix.append(","+",".join(models))
        for row_model in models:
            row = [row_model]
            for col_model in models:
                if row_model == col_model:
                    row.append("-")
                    continue
                val = matrix.get(row_model, {}).get(col_model, float('nan'))
                row.append(str(round(val,2)))
            full_matrix.append(','.join(row))
            full_matrix_latex.append("&".join(row[1:]))

        # 写入文件
        save_dim = dim.replace(" ", "_").replace("&", "and")
        output_file = os.path.join(output_dir, f"{save_dim}.csv")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(full_matrix))
        
        output_file_2 = os.path.join(output_dir, f"{save_dim}.txt")
        with open(output_file_2, 'w', encoding='utf-8') as f:
            f.write('\n'.join(full_matrix_latex))    


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    corr = "kendall"
    model_list = models
    scores_dir = os.path.join(BASE_DIR, "eval_scores_split_and_fill")
    tgt_base = os.path.join(BASE_DIR, f"corr_res_{corr}_split_and_fill")

    for model1 in model_list:
        for model2 in model_list:
            model_score_file_1 = os.path.join(scores_dir, f"eval_score_{model1}.csv")
            model_score_file_2 = os.path.join(scores_dir, f"eval_score_{model2}.csv")

            if not os.path.exists(model_score_file_1):
                print(f"[SKIP] 文件不存在: {model_score_file_1}")
                continue
            if not os.path.exists(model_score_file_2):
                print(f"[SKIP] 文件不存在: {model_score_file_2}")
                continue

            print(f"[correlation_edubench] 计算: {model1} vs {model2}")
            compute_pairwise_correlation(tgt_base, model_score_file_1, model_score_file_2, model1, model2, corr)
        save_matrix(tgt_base)
