import json
import os

# 配置路径（请替换为你的原jsonl文件路径）
input_file_path = "groupby_metric_v3_eval_zh.jsonl"  # 原文件路径
output_dir = "5-grades"
output_file_path = os.path.join(output_dir, "5_groupby_metric_v3_eval_zh.jsonl")

# 创建目标目录（若不存在）
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 转换规则：10分制转5分制
def convert_score(original_score):
    if 1 <= original_score <= 2:
        return 1
    elif 3 <= original_score <= 4:
        return 2
    elif 5 <= original_score <= 6:
        return 3
    elif 7 <= original_score <= 8:
        return 4
    elif 9 <= original_score <= 10:
        return 5
    else:
        return original_score  # 异常分数保持不变

# 读取原文件并转换
with open(input_file_path, "r", encoding="utf-8") as infile, \
     open(output_file_path, "w", encoding="utf-8") as outfile:
    for line in infile:
        try:
            data = json.loads(line.strip())
            # 只处理存在score字段且为数字的情况
            if "score" in data and isinstance(data["score"], (int, float)):
                data["score"] = convert_score(data["score"])
            # 写入修改后的数据
            outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
        except json.JSONDecodeError:
            # 跳过格式错误的行
            print(f"跳过格式错误的行：{line.strip()}")

print(f"转换完成！新文件已保存至：{output_file_path}")