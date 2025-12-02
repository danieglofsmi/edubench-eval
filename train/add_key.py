import os
import json

# 设置路径
questions_folder = "/home/bingxing2/home/scx7kyk/lyg/edullm/example_data_20250425/example_en_only_20250425/filtered_en_data_sampled_annotation_without_model_name"
answers_folder = "/home/bingxing2/home/scx7kyk/lyg/edullm/qwen_answer_en"
output_folder = "/home/bingxing2/home/scx7kyk/lyg/edullm/qwen_answer_en_new"  # 输出文件夹

# 创建输出文件夹
os.makedirs(output_folder, exist_ok=True)

# 获取所有 question_id 及其 evaluation_metrics
question_metrics = {}

for filename in os.listdir(questions_folder):
    if filename.startswith("question_") and filename.endswith(".json"):
        try:
            parts = filename.split("_")
            qid = parts[1]  # 提取 question_id

            with open(os.path.join(questions_folder, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
                metrics = data.get("evaluation_metrics")

            if metrics is not None:
                question_metrics[qid] = metrics
            else:
                print(f"警告：{filename} 中没有 'evaluation_metrics'")
        except Exception as e:
            print(f"读取 {filename} 出错: {e}")

print(f"共找到 {len(question_metrics)} 个 question 的 evaluation_metrics")

# 处理 answers 文件夹中的每一个 answer 文件
for filename in os.listdir(answers_folder):
    if filename.startswith("answer_") and filename.endswith(".json"):
        try:
            parts = filename.split("_")
            aid = parts[1]  # 提取 answer_id
        except IndexError:
            continue

        if aid not in question_metrics:
            print(f"未找到对应 question 的 evaluation_metrics: answer_{aid}")
            continue

        input_path = os.path.join(answers_folder, filename)
        output_path = os.path.join(output_folder, filename)

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                answer_data = json.load(f)

            # 添加 evaluation_metrics 键
            answer_data["evaluation_metrics"] = question_metrics[aid]

            # 写入新文件
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(answer_data, f, indent=2, ensure_ascii=False)

            print(f"已处理并保存: {filename}")
        except Exception as e:
            print(f"处理 {filename} 出错: {e}")