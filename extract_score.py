import json
import re
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np

EXCEPT_PATH = "train/old_label_exceptions.jsonl"
EXTRACT_PATH = "train/human_sft_infer_extracted.jsonl"
ACCURACY_RESULT_PATH = "accuracy_analysis_result.json"  

def read_json(json_file):
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data

def read_jsonl(jsonl_file):
    data = []
    with open(jsonl_file, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                try:
                    item = json.loads(line)
                    data.append(item)
                except json.JSONDecodeError:
                    continue
    return data

def parse_score_content(score_content):
    """统一处理score字段的解析逻辑（适配列表/字典两种格式）"""
    if not score_content:
        return None
    
    try:
        parsed = json.loads(score_content)
        return parsed
    except json.JSONDecodeError:
        pass

    # 去除```json标记
    cleaned = re.sub(r'^```json|```$', '', score_content, flags=re.IGNORECASE).strip()
    try:
        parsed = json.loads(cleaned)
        return parsed
    except json.JSONDecodeError:
        pass

    # 尝试提取JSON片段（处理混杂文本的情况）
    try:
        # 匹配列表/字典格式的JSON片段
        json_part = re.search(r'(\[.*\]|\{.*\})', score_content, re.DOTALL)
        if json_part:
            parsed = json.loads(json_part.group(1))
            return parsed
    except:
        pass

    # 最终尝试：替换单引号+清理转义字符
    try:
        final_clean = (
            cleaned.replace("'", '"')
            .replace('\\"', '"')
            .replace('\\(', '(')
            .replace('\\)', ')')
            .strip()
        )
        parsed = json.loads(final_clean)
        return parsed
    except:
        return None

def extract_json_from_parsed_data(parsed_data):
    """验证并提取标准化的评分数据（criterion/score/reason）"""
    # 确保是列表格式
    if not isinstance(parsed_data, list):
        return None
    
    # 验证每个元素的字段完整性
    valid_items = []
    for item in parsed_data:
        if isinstance(item, dict) and all(key in item for key in ["criterion", "score", "reason"]):
            # 确保score是数字类型
            if isinstance(item["score"], (int, float)):
                valid_items.append(item)
    
    return valid_items if valid_items else None

def calculate_accuracy(label_data, response_data):
    """
    对比label和response的评分数据，统计多维度准确率
    :param label_data: 解析后的label评分列表（extract_json_from_parsed_data返回值）
    :param response_data: 解析后的response评分列表（同上）
    :return: 准确率统计结果字典
    """
    # 转为字典便于匹配
    label_dict = {item["criterion"]: item["score"] for item in label_data}
    response_dict = {item["criterion"]: item["score"] for item in response_data}
    
    # 验证criterion一致性
    label_criterions = set(label_dict.keys())
    response_criterions = set(response_dict.keys())
    if label_criterions != response_criterions:
        raise ValueError(
            f"Criterion不匹配！\nLabel独有: {label_criterions - response_criterions}\nResponse独有: {response_criterions - label_criterions}"
        )
    
    # 初始化统计容器
    total_count = 0
    total_correct = 0
    criterion_stats = defaultdict(lambda: {"count": 0, "correct": 0})
    score_stats = defaultdict(lambda: {"count": 0, "correct": 0})

    # 遍历对比
    for criterion in label_dict:
        label_score = label_dict[criterion]
        response_score = response_dict[criterion]
        # 打分是否正确
        is_correct = 1 if label_score == response_score else 0
        # is_correct = 1 if abs(label_score - response_score) <= 1 else 0

        # 更新统计
        total_count += 1
        total_correct += is_correct
        criterion_stats[criterion]["count"] += 1
        criterion_stats[criterion]["correct"] += is_correct
        score_stats[label_score]["count"] += 1
        score_stats[label_score]["correct"] += is_correct

    # 计算准确率
    result = {
        "overall_accuracy": round(total_correct / total_count, 4) if total_count > 0 else 0.0,
        "criterion_accuracy": {k: round(v["correct"] / v["count"], 4) for k, v in criterion_stats.items()},
        "score_accuracy": {k: round(v["correct"] / v["count"], 4) for k, v in score_stats.items()},
        "details": {
            "total_samples": total_count,
            "total_correct": total_correct,
            "criterion_details": dict(criterion_stats),
            "score_details": dict(score_stats)
        }
    }
    return result

def process_dataset(data_path):
    """
    处理整个数据集，完成解析、准确率计算、结果输出
    :param data_path: 原始数据集路径（JSON格式）
    """
    # 初始化结果容器
    all_accuracy_results = []  # 每条数据的准确率结果
    global_stats = {
        "total_valid_samples": 0,
        "total_invalid_samples": 0,
        "average_overall_accuracy": 0.0,
        "criterion_global_stats": defaultdict(lambda: {"total_count": 0, "total_correct": 0}),
        "score_global_stats": defaultdict(lambda: {"total_count": 0, "total_correct": 0})
    }

    # 打开异常文件和提取文件
    with open(EXCEPT_PATH, 'w', encoding='utf-8') as except_f, \
         open(EXTRACT_PATH, 'w', encoding='utf-8') as extract_f:
        
        # 读取原始数据集
        dataset = read_jsonl(data_path)
        for idx, data in enumerate(dataset):
            try:
                # id = data.get('id', '')
                # instruction = data.get('instruction', '')
                label_content = data.get('label', '')
               
                id = data.get('id', str(idx))  # 用索引作为默认id
                instruction = data.get('prompt', '')  # 使用prompt作为instruction
                question = ""  # 原数据中没有question字段
                response_content = data.get('response', '')
                
                label_parsed = parse_score_content(label_content)
                response_parsed = parse_score_content(response_content)
                
                label_valid = extract_json_from_parsed_data(label_parsed)
                response_valid = extract_json_from_parsed_data(response_parsed)
                
                if not label_valid or not response_valid:
                    raise ValueError("Label/Response解析后无有效评分数据")
                
                # 4. 计算准确率
                accuracy_result = calculate_accuracy(label_valid, response_valid)
                all_accuracy_results.append({
                    "sample_index": idx,
                    "question": data.get('question', ''),
                    "model": data.get('model', ''),
                    "accuracy": accuracy_result
                })
                
                # 5. 更新全局统计
                global_stats["total_valid_samples"] += 1
                # 累加全局criterion统计
                for crit, stats in accuracy_result["details"]["criterion_details"].items():
                    global_stats["criterion_global_stats"][crit]["total_count"] += stats["count"]
                    global_stats["criterion_global_stats"][crit]["total_correct"] += stats["correct"]
                # 累加全局score统计
                for score, stats in accuracy_result["details"]["score_details"].items():
                    global_stats["score_global_stats"][score]["total_count"] += stats["count"]
                    global_stats["score_global_stats"][score]["total_correct"] += stats["correct"]
                
                # # 6. 写入提取文件
                # extract_f.write(json.dumps({
                #     "id": id,
                #     "instruction": instruction,
                #     "model": "human-sft",
                #     "label_scores": label_valid,
                #     "response_scores": response_valid,
                #     "accuracy": accuracy_result["overall_accuracy"]
                # }, ensure_ascii=False) + '\n')
            
            except Exception as e:
                # 记录异常样本
                global_stats["total_invalid_samples"] += 1
                except_f.write(json.dumps({
                    "id": id,
                    "error": str(e),
                    "raw_data": data
                }, ensure_ascii=False) + '\n')
                continue
    
    # 计算全局平均准确率
    if global_stats["total_valid_samples"] > 0:
        total_correct = sum([res["accuracy"]["details"]["total_correct"] for res in all_accuracy_results])
        total_count = sum([res["accuracy"]["details"]["total_samples"] for res in all_accuracy_results])
        global_stats["average_overall_accuracy"] = round(total_correct / total_count, 4)
        
        # 计算全局criterion准确率
        global_stats["criterion_global_accuracy"] = {
            crit: round(stats["total_correct"] / stats["total_count"], 4)
            for crit, stats in global_stats["criterion_global_stats"].items()
        }
        
        # 计算全局score准确率
        global_stats["score_global_accuracy"] = {
            score: round(stats["total_correct"] / stats["total_count"], 4)
            for score, stats in global_stats["score_global_stats"].items()
        }
    else:
        global_stats["criterion_global_accuracy"] = {}
        global_stats["score_global_accuracy"] = {}
    
    # 保存最终分析结果
    final_result = {
        "global_statistics": global_stats,
        "per_sample_accuracy": all_accuracy_results
    }
    # with open(ACCURACY_RESULT_PATH, 'w', encoding='utf-8') as f:
    #     json.dump(final_result, f, ensure_ascii=False, indent=2)
    
    # 打印汇总信息
    print("=" * 80)
    print("数据集处理完成！")
    print(f"有效样本数: {global_stats['total_valid_samples']}")
    print(f"无效样本数: {global_stats['total_invalid_samples']}")
    print(f"全局平均准确率: {global_stats['average_overall_accuracy']}")
    print("=" * 80)
    print("全局各Criterion准确率:")
    for crit, acc in global_stats["criterion_global_accuracy"].items():
        print(f"  {crit}: {acc}")
    print("=" * 80)
    print("全局各分数值准确率:")
    for score, acc in sorted(global_stats["score_global_accuracy"].items()):
        count = global_stats["score_global_stats"][score]["total_count"]
        print(f"  分数{score}: {acc} (总样本数: {count})")
    
    # plot_score_accuracy_and_count(global_stats, save_path="train/inference/sample_50/checkp-99/")
    



def plot_score_accuracy_and_count(global_stats, save_path="score_analysis_plot.png"):
    """
    绘制各分数值的准确率（条形图）和样本数（折线图），双Y轴展示
    :param global_stats: 全局统计字典（包含score_global_accuracy和score_global_stats）
    :param save_path: 图片保存路径
    """
    plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题
    
    # 提取数据并按分数排序
    score_accuracy = global_stats["score_global_accuracy"]
    score_stats = global_stats["score_global_stats"]
    
    # 按分数升序排列
    sorted_scores = sorted(score_accuracy.keys())
    accuracies = [score_accuracy[score] for score in sorted_scores]
    counts = [score_stats[score]["total_count"] for score in sorted_scores]
    
    # 创建画布和双Y轴
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # 绘制准确率条形图（左Y轴）
    x = np.arange(len(sorted_scores))
    bars = ax1.bar(x - 0.2, accuracies, width=0.4, label="acc", color="#2E86AB", alpha=0.8)
    ax1.set_xlabel("score", fontsize=12)
    ax1.set_ylabel("accuracy", fontsize=12, color="#2E86AB")
    ax1.tick_params(axis="y", labelcolor="#2E86AB")
    ax1.set_ylim(0, 1.05)  # 准确率范围0-1
    
    # 绘制样本数折线图（右Y轴）
    ax2 = ax1.twinx()
    line = ax2.plot(x + 0.2, counts, label="test sample counts", color="#E63946", marker="o", linewidth=2, markersize=8)
    ax2.set_ylabel("test sample counts", fontsize=12, color="#E63946")
    ax2.tick_params(axis="y", labelcolor="#E63946")
    ax2.set_ylim(0, max(counts) * 1.1)  # 样本数范围适配数据
    
    # 美化细节
    # 设置X轴刻度和标签
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(score) for score in sorted_scores], fontsize=10)
    
    # 添加数值标注（条形图上显示准确率，折线上显示样本数）
    for bar, acc in zip(bars, accuracies):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                 f"{acc:.2f}", ha="center", va="bottom", fontsize=9, color="#2E86AB")
    
    for i, count in enumerate(counts):
        ax2.text(x[i] + 0.2, count + max(counts)*0.02,
                 f"{count}", ha="center", va="bottom", fontsize=9, color="#E63946")
    
    # 添加标题和图例
    fig.suptitle("Accuracy for each score and sample distribution", fontsize=14, fontweight="bold")
    # 合并两个轴的图例
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=10)
    
    # 网格和背景
    ax1.grid(axis="y", alpha=0.3, linestyle="--")
    fig.tight_layout()  # 调整布局避免标签重叠
    
    # 保存图片
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"图表已保存至: {save_path}")




if __name__ == "__main__":
    # data_path = "train/inference/sample_50_6k/checkpoint-126/generated_predictions.jsonl" 
    data_path = "train/inference/sample_50/checkpoint-99/generated_predictions.jsonl"
    # data_path = "train/inference/generated_predictions.jsonl"
    # data_path = "train/inference/sample_50/checkpoint-99/testset-3274/generated_predictions.jsonl"
    # data_path = "train/inference/sample_50_6k_new_label/checkpoint-126/generated_predictions.jsonl"
    process_dataset(data_path)

    