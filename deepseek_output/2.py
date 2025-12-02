import pandas as pd
import re
import json
import os

# 取出来没标的数据，把选择题和判断题挑出来把标准答案改成学生答案，分数和反馈清空，写成jsonl文件

def extract_field_from_text(text, field_name):
    """从文本中提取指定字段内容（如Subject、Level等）"""
    if pd.isna(text):
        return ""
    
    text_str = str(text)
    # 构建字段匹配正则（支持中英文格式，不区分大小写）
    pattern = re.compile(
        rf'{field_name}:\s*([\s\S]*?)(?=\n\w+:\s*|$)', 
        re.IGNORECASE
    )
    match = pattern.search(text_str)
    
    if match:
        # 清理提取结果中的多余空格和换行
        result = match.group(1).strip()
        return result.replace('\n', ' ').replace('  ', ' ')
    return ""

def detect_language(text):
    """检测文本语言（中文返回Chinese，英文返回English）"""
    if pd.isna(text):
        return "Unknown"
    
    text_str = str(text)
    # 匹配中文字符的正则
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    chinese_chars = chinese_pattern.findall(text_str)
    
    # 若中文字符数超过总字符数的30%，判定为中文
    if len(chinese_chars) / len(text_str.replace(' ', '')) > 0.3:
        return "Chinese"
    return "English"

def extract_score_details(text):
    """从模型判题文本中提取Score、ScoringDetails、PersonalizedFeedback"""
    if pd.isna(text):
        return "", "", ""
    
    text_str = str(text)
    score = ""
    scoring_details = ""
    feedback = ""
    
    # 提取Score
    score_match = re.search(r'Score:\s*([^\n]+)', text_str, re.IGNORECASE)
    if score_match:
        score = score_match.group(1).strip()
    
    # 提取ScoringDetails
    scoring_match = re.search(
        r'ScoringDetails:\s*([\s\S]*?)(?=PersonalizedFeedback:|$)', 
        text_str, 
        re.IGNORECASE
    )
    if scoring_match:
        scoring_details = scoring_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
    
    # 提取PersonalizedFeedback
    feedback_match = re.search(
        r'PersonalizedFeedback:\s*([\s\S]*)$', 
        text_str, 
        re.IGNORECASE
    )
    if feedback_match:
        feedback = feedback_match.group(1).strip().replace('\n', ' ').replace('  ', ' ')
    
    return score, scoring_details, feedback

def main():
    # 1. 读取Excel文件（使用默认列索引，E列为索引4，F列为索引5）
    input_file = "deepseek_output/judge-内部标注-part2.xlsx"  # 输入文件路径
    output_jsonl = "deepseek_output/judge-2-process.jsonl"  # 输出JSONL文件路径
    
    if not os.path.exists(input_file):
        print(f"错误：输入文件 {input_file} 不存在")
        return
    
    # 读取Excel，不使用第一行作为表头
    df = pd.read_excel(input_file, header=None)
    print(f"成功读取数据，总行数：{len(df)}")
    
    # 2. 筛选F列（索引5）为空且E列（索引4）为空的行
    filtered_df = df[(df[4].isna()) & (df[5].isna())].copy()
    print(f"筛选出E列空且F列空的行数：{len(filtered_df)}")
    
    if len(filtered_df) == 0:
        print("警告：未找到符合条件的行")
        return
    
    # 3. 处理数据并生成JSONL
    jsonl_data = []
    choice_questions_zh = []  # 存储中文选择题用于后续修改
    choice_questions_en = []  # 存储英文选择题用于后续修改
    judge_questions_zh = []   # 存储中文判断题用于后续修改
    judge_questions_en = []   # 存储英文判断题用于后续修改
    
    for idx, row in filtered_df.iterrows():
        # 提取核心字段（C列为索引2，D列为索引3）
        question_text = row[2]  # 题目信息列（包含Subject、Question等）
        judge_text = row[3]     # 模型判题列（包含Score、Feedback等）
        
        # 提取各字段内容
        subject = extract_field_from_text(question_text, "Subject")
        edu_level = extract_field_from_text(question_text, "Level")  # EducationalLevel
        question_type = extract_field_from_text(question_text, "QuestionType")
        question_content = extract_field_from_text(question_text, "Question")
        standard_answer = extract_field_from_text(question_text, "StandardAnswer")
        grading_criteria = extract_field_from_text(question_text, "GradingCriteria")
        student_answer = extract_field_from_text(question_text, "StudentAnswer")
        
        # 从模型判题列提取评分相关字段
        score, scoring_details, personalized_feedback = extract_score_details(judge_text)
        
        # 检测语言
        language = detect_language(question_content)
        
        # 构建单条数据
        data = {
            "Subject": subject,
            "EducationalLevel": edu_level,
            "QuestionType": question_type,
            "Question": question_content,
            "StandardAnswer": standard_answer,
            "GradingCriteria": grading_criteria,
            "StudentAnswer": student_answer,
            "Score": score,
            "ScoringDetails": scoring_details,
            "PersonalizedFeedback": personalized_feedback,
            "Language": language
        }
        
        jsonl_data.append(data)
        
    #     # 分类存储选择题和判断题（用于后续修改）
    #     if "选择题" in question_type:
    #         choice_questions_zh.append(data)
    #     elif "Multiple Choice" in question_type:
    #         choice_questions_en.append(data)
    #     elif "判断题" in question_type:
    #         judge_questions_zh.append(data)
    #     elif "True/False" in question_type:
    #         judge_questions_en.append(data)
    
    # print(f"生成基础JSONL数据条数：{len(jsonl_data)}")
    # print(f"筛选出选择题数量：{len(choice_questions_zh) + len(choice_questions_en)}")
    # print(f"筛选出判断题数量：{len(judge_questions_zh) + len(judge_questions_en)}")
    
    # # 4. 检查选择题和判断题数量是否满足需求
    # required_choice_zh = 20
    # required_choice_en = 26
    # required_judge_zh = 25
    # required_judge_en = 28
    
    # if len(choice_questions_zh) < required_choice_zh:
    #     print(f"警告：中文选择题数量不足{required_choice_zh}道，仅找到{len(choice_questions_zh)}道")
    #     return
    # if len(choice_questions_en) < required_choice_en:
    #     print(f"警告：英文选择题数量不足{required_choice_en}道，仅找到{len(choice_questions_en)}道")
    #     return
    # if len(judge_questions_zh) < required_judge_zh:
    #     print(f"警告：中文判断题数量不足{required_judge_zh}道，仅找到{len(judge_questions_zh)}道")
    #     return
    # if len(judge_questions_en) < required_judge_en:
    #     print(f"警告：英文判断题数量不足{required_judge_en}道，仅找到{len(judge_questions_en    )}道")
    #     return
    
    # # 5. 修改指定数量的选择题和判断题
    # # 修改49道选择题
    # for i in range(required_choice_zh):
    #     q = choice_questions_zh[i]
    #     q["StudentAnswer"] = q["StandardAnswer"]  # 学生答案设为标准答案
    #     q["Score"] = ""                           # 分数设为空
    #     q["ScoringDetails"] = ""                  # 评分细节设为空
    #     q["PersonalizedFeedback"] = ""            # 个性化反馈设为空

    # for i in range(required_choice_en):
    #     q = choice_questions_en[i]
    #     q["StudentAnswer"] = q["StandardAnswer"]  # 学生答案设为标准答案
    #     q["Score"] = ""                           # 分数设为空
    #     q["ScoringDetails"] = ""                  # 评分细节设为空
    #     q["PersonalizedFeedback"] = ""            # 个性化反馈设为空
    
    # # 修改53道判断题
    # for i in range(required_judge_zh):
    #     q = judge_questions_zh[i]
    #     q["StudentAnswer"] = q["StandardAnswer"]  # 学生答案设为标准答案
    #     q["Score"] = ""                           # 分数设为空
    #     q["ScoringDetails"] = ""                  # 评分细节设为空
    #     q["PersonalizedFeedback"] = ""            # 个性化反馈设为空
    
    # for i in range(required_judge_en):
    #     q = judge_questions_en[i]
    #     q["StudentAnswer"] = q["StandardAnswer"]  # 学生答案设为标准答案
    #     q["Score"] = ""                           # 分数设为空
    #     q["ScoringDetails"] = ""                  # 评分细节设为空
    #     q["PersonalizedFeedback"] = ""            # 个性化反馈设为空

    
    # 6. 写入JSONL文件
    with open(output_jsonl, 'w', encoding='utf-8') as f:
        for data in jsonl_data:
            json.dump(data, f, ensure_ascii=False)
            f.write('\n')
    
    print(f"成功写入JSONL文件：{output_jsonl}")
    print(f"最终文件包含数据条数：{len(jsonl_data)}")
    # print(f"已修改{required_choice_zh}道中文选择题、{required_choice_en}道英文选择题、{required_judge_zh}道中文判断题和{required_judge_en}道英文判断题")

if __name__ == "__main__":
    main()