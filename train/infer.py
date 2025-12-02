import os
import json
from transformers import AutoModelForCausalLM, AutoTokenizer
from tqdm import tqdm

# 加载模型和分词器
model_name = "/home/bingxing2/home/scx7kyk/soft/LLaMA-Factory/saves/qwen2-7b/full/sft/checkpoint-1010"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)

# 输入文件夹路径和输出文件夹路径
input_folder = "/home/bingxing2/home/scx7kyk/lyg/edullm/example_data_20250425/example_zh_only_20250425/filtered_zh_data_sampled_annotation_without_model_name"
output_folder = "/home/bingxing2/home/scx7kyk/lyg/edullm/qwen_answer_zh"

# 创建输出文件夹（如果不存在）
os.makedirs(output_folder, exist_ok=True)

# 记录已处理的 question_id，避免重复推理
processed_question_ids = set()

# 获取所有 JSON 文件，并提取其中的 question_id
all_files = [f for f in os.listdir(input_folder) if f.endswith(".json")]

# 构建 {question_id: filename} 映射（自动去重，保留第一个遇到的文件）
unique_questions = {}
for filename in all_files:
    file_path = os.path.join(input_folder, filename)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        qid = data.get("question_id")
        if qid is not None and qid not in unique_questions:
            unique_questions[qid] = filename  # 只保留第一个出现的
    except Exception as e:
        print(f"[ERROR] Failed to read {filename}: {e}")

# 转换为列表用于进度条
qid_list = list(unique_questions.items())

# 使用 tqdm 添加进度条，只处理去重后的 question_id
for qid, filename in tqdm(qid_list, desc="Processing Unique Questions", total=len(qid_list)):
    if qid in processed_question_ids:
        continue  # 再次判断以防万一

    file_path = os.path.join(input_folder, filename)
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            tqdm.write(f"[ERROR] Failed to parse {filename}")
            continue

    question = data.get("question", "")
    if not question:
        tqdm.write(f"[SKIP] No question found in {filename}")
        continue

    # 构造 prompt
    messages = [
        {"role": "user", "content": question}
    ]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    # 生成回答
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=32768
    )
    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
    answer = tokenizer.decode(output_ids, skip_special_tokens=False)  # 原始输出，不跳特殊 token

    # 构建输出结构
    output_data = {
        "question_id": qid,
        "question": question,
        "answer": answer,
        "answer_id": 0  # 可扩展支持多答案
    }

    # 写入文件，命名方式为 answer_{question_id}_model_0.json
    output_filename = f"answer_{qid}_model_0.json"
    output_path = os.path.join(output_folder, output_filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

    # 标记该 question_id 已处理
    processed_question_ids.add(qid)

print("[INFO] 所有任务已完成！")