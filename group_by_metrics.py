import json
import os
from pathlib import Path
import re
from collections import defaultdict

def process_jsonl_files_model(input_files, output_file):
    # 创建输出目录（如果输出文件包含路径）
    output_dir = os.path.dirname(output_file)
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 用于跟踪每个model的文件句柄（避免重复打开/关闭）
    model_file_handles = {}
    # 统计每个model的数据量
    model_count = {}
    
    # 打开输出文件，准备写入
    with open(output_file, 'w', encoding='utf-8') as out_f:
        total_count = 0  # 统计总处理条数
        
        for file_path in input_files:
            print(f"处理文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        # 解析原始数据
                        data = json.loads(line.strip())
                        
                        
                        # 提取必要字段
                        model = data.get("model")
                        question = data.get("question")
                        response = data.get("response")
                        detailed_scores = data.get("scores", [])

                        # score_str = data.get("scores", "")
                        
                        # # 清理score字段（去除代码块标记）
                        # score_clean = re.sub(r'^```json\s*|\s*```$', '', score_str.strip())
                        # score_json = json.loads(score_clean)
                        # detailed_scores = score_json.get("scores", [])
                        
                        
                        # 按principle拆分数据并写入
                        for item in detailed_scores:
                            try:
                                if "principle" in item:
                                    principle = item.get("principle")
                                elif "criterion" in item:
                                    principle = item.get("criterion")
                                elif "metric" in item:
                                    principle = item.get("metric")
                            except:
                                principle = None
                            score = item.get("score")
                            reason = item.get("reason")


                            # 构建新数据结构
                            new_data = {
                                "principle": principle,
                                "score": score,
                                "reason": reason,
                                "model": model,
                                "question": question,
                                "response": response
                            }
                            
                            # 写入合并文件（每行一条JSON）
                            out_f.write(json.dumps(new_data, ensure_ascii=False) + "\n")
                            total_count += 1
                            # # 处理当前model的输出文件
                            # if model not in model_file_handles:
                            #     # 生成安全的文件名（替换特殊字符）
                            #     safe_model_name = re.sub(r'[<>:"/\\|?*]', '_', model)
                            #     output_filename = f"{safe_model_name}_group_by_metric.jsonl"
                            #     output_path = os.path.join(output_dir, output_filename)
                            #     # 打开文件句柄（追加模式）
                            #     file_handle = open(output_path, 'a', encoding='utf-8')
                            #     model_file_handles[model] = file_handle
                            #     model_count[model] = 0  # 初始化计数
                            
                            # # 写入数据
                            # model_file_handles[model].write(json.dumps(new_data, ensure_ascii=False) + "\n")
                            # model_count[model] += 1
                            
                    except Exception as e:
                        print(f"处理第{line_num}行时出错: {str(e)}")
                        
                        continue
    
    print(f"处理完成，共生成 {total_count} 条数据，保存至: {output_file}")

def process_jsonl_files_human(input_files, output_file):
    # 创建输出目录（如果需要）
    output_dir = os.path.dirname(output_file)
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    total_count = 0  # 统计总处理条数
    eval_file_handles = {}
    eval_count = {}
    
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for file_path in input_files:
            print(f"处理中文文件: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        # 解析原始中文数据
                        data = json.loads(line.strip())
                        
                        # 提取对应字段（中文数据字段映射）
                        eval_value = data.get("eval", "unknown_eval")  # 获取eval字段值（作为分类依据）
                        model = data.get("gen")  # 模型名称对应 "gen" 字段
                        # 提取用户问题（从message中找user角色的content）
                        question = next(
                            (msg["content"] for msg in data.get("message", []) if msg.get("role") == "user"),
                            ""
                        )
                        # 提取模型回答（从message中找assistant角色的content）
                        response = next(
                            (msg["content"] for msg in data.get("message", []) if msg.get("role") == "assistant"),
                            ""
                        )
                        # 提取评分列表（对应 "scores" 字段）
                        detailed_scores = data.get("scores", [])
                        
                        # 按criterion拆分数据并转换格式
                        for item in detailed_scores:
                            # 中文的"criterion"对应英文的"principle"
                            new_data = {
                                "principle": item.get("criterion"),  # 原则名称
                                "score": item.get("score"),         # 分数
                                "reason": item.get("reason"),       # 评分理由
                                "model": model,                     # 模型名称
                                "question": question,               # 用户问题
                                "response": response                # 模型回答
                            }
                            
                            # 写入输出文件
                            out_f.write(json.dumps(new_data, ensure_ascii=False) + "\n")
                            total_count += 1

                            # # 处理当前eval值的输出文件
                            # if eval_value not in eval_file_handles:
                            #     # 生成安全文件名（替换特殊字符）
                            #     safe_eval_name = re.sub(r'[<>:"/\\|?*]', '_', eval_value)
                            #     output_filename = f"{safe_eval_name}.jsonl"
                            #     output_path = os.path.join(output_dir, output_filename)
                            #     # 打开文件句柄（追加模式）
                            #     file_handle = open(output_path, 'a', encoding='utf-8')
                            #     eval_file_handles[eval_value] = file_handle
                            #     eval_count[eval_value] = 0  # 初始化计数
                            
                            # # 写入数据
                            # eval_file_handles[eval_value].write(json.dumps(new_data, ensure_ascii=False) + "\n")
                            # eval_count[eval_value] += 1
                            
                    except Exception as e:
                        print(f"处理第{line_num}行时出错: {str(e)}")
                        continue
    
    print(f"中文数据转换完成，共生成 {total_count} 条数据，保存至: {output_file}")

def analyze_score_distribution(jsonl_file):
    """
    分析JSONL文件中各principle的score数值分布
    
    参数:
        jsonl_file: 输入的JSONL文件路径
    """
    # 数据结构：{principle: {score: count}}
    distribution = defaultdict(lambda: defaultdict(int))
    total_lines = 0
    error_lines = 0

    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            total_lines += 1
            try:
                data = json.loads(line.strip())
                principle = data.get("principle")
                score = data.get("score")
                
                if principle is None or score is None or score == 0:
                    print(f"第{line_num}行缺少principle或score字段或score=0，已跳过")
                    print(data)
                    error_lines += 1
                    continue
                
                # 确保score是整数（如果有小数会转换为整数）
                if isinstance(score, float):
                    score = int(score)
                if not isinstance(score, int):
                    print(f"第{line_num}行score格式错误（{score}），已跳过")
                    error_lines += 1
                    continue
                
                # 累计计数
                distribution[principle][score] += 1
                
            except Exception as e:
                print(f"第{line_num}行解析错误：{str(e)}，已跳过")
                error_lines += 1
                continue

    print(f"总数据量：{total_lines}条")
    print(f"有效数据：{total_lines - error_lines}条")
    print(f"错误数据：{error_lines}条\n")

    # 按principle排序输出
    for principle in sorted(distribution.keys()):
        print(f"原则：{principle}")
        print("  分数分布：")
        # 按分数升序排列
        for score in sorted(distribution[principle].keys()):
            count = distribution[principle][score]
            print(f"    分数{score}：{count}条")
        # 计算该原则的总数据量
        total = sum(distribution[principle].values())
        print(f"  该原则总数据量：{total}条\n")


if __name__ == "__main__":
    input_files = [
        # "download_raw/deepseek-r1_pointwise_filtered_zh_data_sampled.jsonl",
        # "download_raw/deepseek-v3_pointwise_filtered_en_data_sampled.jsonl",
    #     "download_raw/gpt-4o_pointwise_filtered_en_data_sampled.jsonl",
        # "download_raw/qwq-plus_pointwise_filtered_zh_data_sampled.jsonl"
    ]
    input_files = ["deepseek_output/processed_excel_data_1_en.jsonl"]
    output_file = "deepseek_output/processed_excel_data_2_en.jsonl"

    process_jsonl_files_model(input_files,output_file)


    # jsonl_path = "5-grades/5_groupby_metric_v3_eval_zh.jsonl"
    # analyze_score_distribution(jsonl_path)
