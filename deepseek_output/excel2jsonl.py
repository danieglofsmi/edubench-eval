import pandas as pd
import json
import os
import re

def process_excel_to_jsonl(excel_path, output_zh_jsonl_path, output_en_jsonl_path):
    """
    处理Excel文件，提取E列为空且F列不为空的行，按语言类型分别转换为指定格式的JSONL文件
    自动识别question内容的语言类型，中文使用中文前缀后缀并存入中文文件，英文同理
    新增：A列为id，B列为level字段
    """
    # 读取Excel文件，保留原始数据结构
    df = pd.read_excel(excel_path)
    
    # 列索引映射（更新：A列为id，B列为level）
    COLUMN_MAPPING = {
        'id_col': 0,               # A列：原Unnamed: 0（包含zh-query1等ID）
        'level_col': 1,            # B列：原Unnamed: 1（包含博士/大学/高中等层级）
        'question_col': 2,         # C列：题目、标答、评分细则、学生回答
        'response_col': 3,         # D列：模型判题结果
        'problem_flag_col': 4,     # E列：数据问题标记（空值判断依据）
        'first_criteria_col': 5    # F列：首个评分标准列，作为非空判断依据
    }
    
    # 评分标准列配置（每对列：分数列+理由列）
    CRITERIA_CONFIG = [
        {'score_col': 5, 'reason_col': 6, 'default_name': '指令遵循与任务完成'},
        {'score_col': 7, 'reason_col': 8, 'default_name': '内容相关性与范围控制'},
        {'score_col': 9, 'reason_col': 10, 'default_name': '基础事实准确性'},
        {'score_col': 11, 'reason_col': 12, 'default_name': '推理过程严谨性'},
        {'score_col': 13, 'reason_col': 14, 'default_name': '错误识别与纠正精确性'},
        {'score_col': 15, 'reason_col': 16, 'default_name': '激励引导与积极反馈'}
    ]
    
    # 中英文前缀后缀配置
    # 中文前缀后缀
    QUESTION_PREFIX_ZH = (
        "你需要完成以下任务："
        "1. 根据评分细则评估学生的作答情况，给出分数和详细的评分说明。"
        "2. 基于学生的作答情况生成具体且有建设性的反馈，包括可能存在的知识盲区和学习建议。"
        "你的回复应积极正面且具有建设性。"
    )
    QUESTION_SUFFIX_ZH = (
        '请以JSON格式返回结果："Score": "", "Scoring Details": "", "Personalized Feedback": ""'
    )
    
    # 英文前缀后缀
    QUESTION_PREFIX_EN = (
        "You need to accomplish the following: "
        "1. Evaluate the sample student response according to the grading criteria and provide a score and detailed scoring breakdown. "
        "2. Generate specific and constructive feedback based on the student's response, such as potential knowledge gaps and learning suggestions. "
        "Your response should be positive and constructive."
    )
    QUESTION_SUFFIX_EN = (
        'Return the result in JSON format: "Score": "", "Scoring Details": "", "Personalized Feedback": ""'
    )
    
    def is_chinese_text(text):
        """
        判断文本是否为中文（包含一定比例的中文字符）
        """
        if not text:
            return False
        # 匹配中文字符（包括中文汉字、标点）
        chinese_pattern = re.compile(r'[\u4e00-\u9fa5\uff0c\uff1f\uff01\uff1b\uff1a""''《》（）【】]')
        chinese_chars = chinese_pattern.findall(text)
        # 中文字符占比超过30%则判定为中文
        return len(chinese_chars) / len(text) > 0.3
    
    # 打开两个JSONL文件准备写入（中文和英文）
    with open(output_zh_jsonl_path, 'w', encoding='utf-8') as zh_jsonl_file, \
         open(output_en_jsonl_path, 'w', encoding='utf-8') as en_jsonl_file:
         
        zh_count = 0  # 中文数据计数
        en_count = 0  # 英文数据计数
        
        # 遍历每一行数据进行处理
        for _, row in df.iterrows():
            # 1. 筛选符合条件的行：E列为空且F列不为空（F列为数字分数）
            problem_flag = row.iloc[COLUMN_MAPPING['problem_flag_col']]
            first_criteria_score = row.iloc[COLUMN_MAPPING['first_criteria_col']]
            
            if (pd.isna(problem_flag) and 
                not pd.isna(first_criteria_score) and 
                str(first_criteria_score).strip().isdigit()):
                
                # 2. 提取并处理id字段（A列）
                id_value = row.iloc[COLUMN_MAPPING['id_col']]
                if pd.isna(id_value):
                    continue  # 跳过无ID的行
                id_clean = str(id_value).strip()
                
                # 3. 提取并处理level字段（B列）
                level_value = row.iloc[COLUMN_MAPPING['level_col']]
                level_clean = str(level_value).strip() if not pd.isna(level_value) else "未知层级"
                
                # 4. 提取并处理question字段（自动识别语言，拼接对应前缀后缀）
                question_raw = row.iloc[COLUMN_MAPPING['question_col']]
                question_clean = ""
                is_chinese = False
                if not pd.isna(question_raw):
                    question_str = str(question_raw).strip()
                    # 自动识别语言类型
                    is_chinese = is_chinese_text(question_str)
                    if is_chinese:
                        # 中文内容：使用中文前缀后缀
                        question_clean = f"{QUESTION_PREFIX_ZH}\n\n{question_str}\n\n{QUESTION_SUFFIX_ZH}"
                    else:
                        # 英文内容：使用英文前缀后缀
                        question_clean = f"{QUESTION_PREFIX_EN}\n\n{question_str}\n\n{QUESTION_SUFFIX_EN}"
                
                # 5. 提取并处理response字段
                response_raw = row.iloc[COLUMN_MAPPING['response_col']]
                response_clean = str(response_raw).strip() if not pd.isna(response_raw) else ""
                
                # 6. 构建scores列表（处理所有评分标准列）
                scores_list = []
                for criteria in CRITERIA_CONFIG:
                    # 提取分数和理由
                    score_val = row.iloc[criteria['score_col']]
                    reason_val = row.iloc[criteria['reason_col']]
                    
                    # 分数为空则跳过该指标
                    if pd.isna(score_val):
                        continue
                    
                    criteria_name = criteria['default_name']
                    
                    # 处理理由（为空时设置默认值）
                    reason_clean = str(reason_val).strip() if not pd.isna(reason_val) else "No specific reason provided."
                    
                    # 处理分数（确保数字类型）
                    score_clean = int(score_val) if str(score_val).strip().isdigit() else str(score_val)
                    
                    # 添加到scores列表
                    scores_list.append({
                        "criterion": criteria_name,
                        "score": score_clean,
                        "reason": reason_clean
                    })
                
                # 7. 生成JSON对象并根据语言写入对应文件
                if scores_list:
                    json_object = {
                        "id": id_clean,
                        "level": level_clean,
                        "model": "DeepSeek-V3.2-Exp",
                        "question": question_clean,
                        "response": response_clean,
                        "scores": scores_list
                    }
                    # 根据语言类型写入不同文件
                    if is_chinese:
                        zh_jsonl_file.write(json.dumps(json_object, ensure_ascii=False) + '\n')
                        zh_count += 1
                    else:
                        en_jsonl_file.write(json.dumps(json_object, ensure_ascii=False) + '\n')
                        en_count += 1
    
    # 输出处理结果统计
    print(f"数据处理完成！")
    print(f"输入文件：{os.path.basename(excel_path)}")
    print(f"中文输出文件：{os.path.basename(output_zh_jsonl_path)}，有效行数：{zh_count}")
    print(f"英文输出文件：{os.path.basename(output_en_jsonl_path)}，有效行数：{en_count}")
    print(f"总有效数据行数：{zh_count + en_count}")


if __name__ == "__main__":
    # 输入Excel路径和输出JSONL路径（中文和英文）
    INPUT_EXCEL = "deepseek_output/judge-内部标注 (1).xlsx"  # 输入文件路径
    OUTPUT_ZH_JSONL = "deepseek_output/processed_excel_data_1_zh.jsonl"  # 中文输出文件路径
    OUTPUT_EN_JSONL = "deepseek_output/processed_excel_data_1_en.jsonl"  # 英文输出文件路径
    
    # 调用处理函数
    process_excel_to_jsonl(INPUT_EXCEL, OUTPUT_ZH_JSONL, OUTPUT_EN_JSONL)