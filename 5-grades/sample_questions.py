import json
import random
from collections import defaultdict

# 配置文件路径（请替换为你的输入文件路径）
input_file = "deepseek_output/processed_excel_data_2_zh.jsonl"  # 你的原始jsonl文件
output_file = "5-grades/judge_v3_questions_zh.jsonl"  # 输出的json文件

# 按principle分组存储去重后的question
principle_data = defaultdict(set)  # 使用set自动去重

# 读取jsonl文件并分组去重
with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line.strip())
            if "principle" in data and "question" in data:
                principle = data["principle"]
                question = data["question"]
                # 确保question是字符串类型（避免因类型不同导致的重复）
                if isinstance(question, str):
                    principle_data[principle].add(question)
        except json.JSONDecodeError:
            print(f"跳过格式错误的行：{line.strip()}")

# 处理每组数据（先转成列表，再随机选50条）
result = {}
for principle, unique_questions in principle_data.items():
    question_list = list(unique_questions)  # 集合转列表用于随机抽样
    sample_size = min(50, len(question_list))
    random.shuffle(question_list)
    selected_questions = question_list[:sample_size]
    result[principle] = selected_questions

# 保存结果
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# 输出统计信息
print(f"处理完成！共识别到 {len(principle_data)} 种不同的principle")
for principle, questions in result.items():
    print(f"- {principle}: 去重后共{len(principle_data[principle])}条，选择了{len(questions)}条（均不重复）")
print(f"结果已保存至 {output_file}")