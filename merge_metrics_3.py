import json
import os
from pathlib import Path
from collections import defaultdict

def process_three_files(file1, file2, file3, output_file):
    """
    处理三个JSONL文件，按principle、question和model共同分组，计算平均分并筛选数据
    
    参数:
        file1, file2, file3: 三个输入JSONL文件路径
        output_file: 筛选后的输出文件路径
    """
    # 创建输出目录（如果需要）
    output_dir = os.path.dirname(output_file)
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 用于按(principle, question, model)分组存储数据
    # 结构: {(principle, question, model): [data1, data2, data3]}
    grouped_data = defaultdict(list)
    
    # 读取并分组三个文件的数据
    for file_path in [file1, file2, file3]:
        # 提取文件名（不带路径和后缀）作为eval值
        eval_value = os.path.splitext(os.path.basename(file_path))[0]
        print(f"读取文件: {file_path}，将添加eval字段值: {eval_value}")

    #      # 提取文件名（不带路径和后缀）
    #     base_name = os.path.splitext(os.path.basename(file_path))[0]
    #     # 分割下划线，取第二个下划线后的内容（若不足则取完整文件名）
    #     parts = base_name.split('_')
    #     if len(parts) >= 3:
    #         # 从第三个元素开始拼接（索引2及以后）
    #         eval_value = '_'.join(parts[2:])
    #     else:
    #         # 不足三个部分时使用完整文件名作为 fallback
    #         eval_value = base_name


        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    # 添加eval字段（值为文件名不带后缀）
                    data["eval"] = eval_value

                    # 提取分组关键字段（新增model作为分组条件）
                    principle = data.get("principle")
                    question = data.get("question")
                    model = data.get("model")
                    question = data.get("question")
                    
                    # 检查关键字段是否完整
                    if not all([principle, question, model]):
                        missing = []
                        if not principle: missing.append("principle")
                        if not question: missing.append("question")
                        if not model: missing.append("model")
                        print(f"文件{file_path}第{line_num}行缺少字段：{missing}，已跳过")
                        continue
                    
                    # 按(principle, question, model)共同分组
                    key = (principle, question, model,question)
                    grouped_data[key].append(data)
                    
                except Exception as e:
                    print(f"文件{file_path}第{line_num}行解析错误: {str(e)}，已跳过")
                    continue
    
    # 处理分组数据，计算平均分并筛选
    total_groups = 0
    valid_groups = 0
    filtered_count = 0
    
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for (principle, question, model,question), items in grouped_data.items():
            total_groups += 1
            
            # 确保每组有3条数据（分别来自三个文件）
            if len(items) != 3:
                print(f"原则'{principle}'、模型'{model}'的分组数据量异常（{len(items)}条，需3条），已跳过")
                print(question)
                continue
            
            valid_groups += 1
            
            # 提取三个分数并计算平均值
            scores = [item.get("score", 0) for item in items]
            try:
                # 转换为整数分数
                scores = [int(score) for score in scores]
                score_mean = round(sum(scores) / 3)  # 四舍五入取整数
            except (ValueError, TypeError):
                print(f"原则'{principle}'、模型'{model}'的分数格式错误，已跳过")
                continue
            
            # # 确定平均分所在的分数段（10分内两分一段：1-2, 3-4, 5-6, 7-8, 9-10）
            # if score_mean <= 2:
            #     segment_start = 1
            # elif score_mean <= 4:
            #     segment_start = 3
            # elif score_mean <= 6:
            #     segment_start = 5
            # elif score_mean <= 8:
            #     segment_start = 7
            # else:  # 9-10
            #     segment_start = 9
            
            # 筛选
            for item in items:
                item_score = int(item.get("score", 0))
                
                # 与分数段相同
                if item_score == score_mean:
                    out_f.write(json.dumps(item, ensure_ascii=False) + "\n")
                    filtered_count += 1
                # else:
                #     print(f"原则'{principle}'、模型'{model}'的第{items.index(item)+1}条数据分数为{item_score}，不在平均分{score_mean}的分数段内，已跳过")

                    

                # # 判断是否在同一分数段
                # if (segment_start <= item_score <= segment_start + 1):

                #     # 补充平均分字段（方便查看）
                #     item_with_mean = item.copy()
                #     item_with_mean["score_mean"] = score_mean
                #     # 写入输出文件
                #     out_f.write(json.dumps(item_with_mean, ensure_ascii=False) + "\n")
                #     filtered_count += 1
    
    print(f"\n处理完成：")
    print(f"总分组数：{total_groups}")
    print(f"有效分组数（每组3条）：{valid_groups}")
    print(f"筛选后保留的数据条数：{filtered_count}")
    print(f"结果已保存至：{output_file}")

# 使用示例
if __name__ == "__main__":
    # 三个输入文件路径
    # file_paths = [
    #     "human_1.jsonl",
    #     "human_2.jsonl",
    #     "human_3.jsonl"
    # ]
    file_paths = [
        "5-grades/5_human_1.jsonl",
        "5-grades/5_human_2.jsonl",
        "5-grades/5_human_3.jsonl"
    ]
    
    # 执行处理
    process_three_files(*file_paths,output_file="5_merge_human_metric.jsonl")