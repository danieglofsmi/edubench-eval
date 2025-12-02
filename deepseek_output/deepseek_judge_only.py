import os
import json
from openai import OpenAI
import re
import time
from datetime import datetime
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Configure OpenAI API for DeepSeek
# openai.api_key = os.getenv("OPENAI_API_KEY", "sk-0aa096f0c9f4494f807e56b4a5d342ea")
ds_key = "sk-2403a97b97e8498bb1b4e9accf1fa7c7"
client = OpenAI(api_key=ds_key, base_url="https://api.deepseek.com")

prompt_template_zh = """
你需要实现：
1. 针对题目的评分细则和学生回答，生成评分和评分细节。
2. 针对学生答题情况生成具体、有建设性的反馈意见，例如可能涉及的知识盲区，学习建议等，语言积极、富有建设性。

学科：{subject}
教育阶段：{level}
题目类型：{question_type}
问题：{question}
标准答案：{standard_answer}
评分细则：{grading_criteria}
学生的答案：{student_answer}

以json格式返回
"评分":""
"评分细节":""
"个性化反馈":""
"""


# prompt_template_en = """
# You need to implement:
# 1. Objective scoring capability (e.g., multiple-choice, true/false, fill-in-the-blank); provide step-by-step scoring or grading references for problem-solving questions.
# 2. Subjective scoring capability: Evaluate comprehensive assignments, lab reports, etc., based on various dimensions such as workload, completeness, and knowledge application.
# 3. Personalized feedback capability: Generate specific and constructive feedback for students' answers, including potential knowledge gaps and learning suggestions.

# Please freely generate an appropriate question and a student's answer for the given subject and difficulty level. Provide a score for the student's answer. The question type is {question_type}.
# If the type is a short-answer question, include code or mathematical calculations where necessary for certain subjects. Do not include any extra content.
# You should use English.

# Subject: {subject}
# Difficulty Level: {level}

# Return in JSON format:
# "Question": ""
# "Student's Answer": ""
# "Score": ""
# "Scoring Details": ""
# "Personalized Feedback": ""
# """

prompt_template_en = """
You need to accomplish the following:
1. Evaluate the sample student response according to the grading criteria and provide a score and detailed scoring breakdown.
2. Generate specific and constructive feedback based on the student's response, such as potential knowledge gaps and learning suggestions. Your response should be positive and constructive.

Subject: {subject}
Educational Level: {level}
Question Type: {question_type}
Question: {question}
Standard Answer: {standard_answer}
Grading Criteria: {grading_criteria}
Student's Answer: {student_answer}

Return the result in JSON format:
"Score": "",
"Scoring Details": "",
"Personalized Feedback": ""
"""

# Thread-safe file writing
file_lock = threading.Lock()

def send_request(prompt: str) -> Optional[str]:
    """Send request to DeepSeek API and return the result"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.3,
            max_tokens=2048,
        )

        if response.choices:
            response_text = response.choices[0].message.content
            # Clean response by removing possible markdown code blocks
            cleaned_response = re.sub(r'```(json)?\s*|\s*```', '', response_text).strip()
            print(cleaned_response)
            return cleaned_response
    except Exception as e:
        print(f"API request failed: {e}")
        return None

def fix_json(response: str) -> Optional[str]:
    """Attempt to fix common JSON formatting errors"""
    try:
        # Try parsing directly
        json.loads(response)
        return response
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}, attempting to fix...")

    try:
        # Replace single quotes with double quotes
        fixed_response = response.replace("'", '"')
        json.loads(fixed_response)
        return fixed_response
    except json.JSONDecodeError:
        pass

    try:
        # Attempt to fix missing commas or colons
        fixed_response = re.sub(r'(?<=[}\]"\'\w])\s*(?=[{\["\'\w])', ', ', response)
        fixed_response = re.sub(r'(?<=[:])\s*(?=[{\["\'\w])', ' ', fixed_response)
        json.loads(fixed_response)
        return fixed_response
    except json.JSONDecodeError:
        pass

    print("Unable to fix JSON formatting errors")
    return None

def validate_response(response: str, is_english: bool) -> bool:
    """Validate whether the API response is valid"""
    try:
        # Attempt to fix JSON format
        fixed_response = fix_json(response)
        if not fixed_response:
            return False

        data = json.loads(fixed_response)

        if is_english:
            # English validation
            required_keys = ["Score", "Scoring Details", "Personalized Feedback"]
            if not all(key in data for key in required_keys):
                print("Validation failed: Missing required fields")
                return False

            # Check if field types are correct
            if not all(isinstance(data[key], str) for key in required_keys):
                print("Validation failed: Field type error")
                return False

            # Check if fields are empty strings
            if any(not data[key] for key in required_keys):
                print("Validation failed: Fields are empty")
                return False
        else:
            # Chinese validation
            required_keys = ["评分", "评分细节", "个性化反馈"]
            if not all(key in data for key in required_keys):
                print("验证失败：缺少必要字段")
                return False

            # Check if field types are correct
            if not all(isinstance(data[key], str) for key in required_keys):
                print("验证失败：字段类型错误")
                return False

            # Check if fields are empty strings
            if any(not data[key] for key in required_keys):
                print("验证失败：字段为空")
                return False

        return True
    except Exception as e:
        print(f"Validation failed: JSON parsing error - {e}")
        return False

def process_single_question(subject: str, level: str, question_type: str, question: str, standard_answer: str,
                            grading_criteria: str, student_answer: str, is_english: bool,
                           output_file: str, attempt: int) -> bool:
    """Process a single question generation attempt"""
    prompt_template = prompt_template_en if is_english else prompt_template_zh
    prompt = prompt_template.format(
        subject=subject,
        level=level,
        question_type=question_type,
        question=question,
        standard_answer=standard_answer,
        grading_criteria=grading_criteria,
        student_answer=student_answer,
    )

    response = send_request(prompt)
    if not response or not validate_response(response, is_english):
        print(f"Generation failed: {subject}-{level}-{question_type} (Attempt {attempt})")
        return False

    try:
        qa_data = json.loads(response)

        # Convert to consistent English keys regardless of language
        if is_english:
            result = {
                "Subject": subject,
                "Level": level,
                "QuestionType": question_type,
                "Question": question,
                "StandardAnswer": standard_answer,
                "GradingCriteria": grading_criteria,
                "StudentAnswer": student_answer,
                "Score": qa_data["Score"],
                "ScoringDetails": qa_data["Scoring Details"],
                "PersonalizedFeedback": qa_data["Personalized Feedback"],
                "Language": "English"
            }
        else:
            result = {
                "Subject": subject,
                "Level": level,
                "QuestionType": question_type,
                "Question": question,
                "StandardAnswer": standard_answer,
                "GradingCriteria": grading_criteria,
                "StudentAnswer": student_answer,
                "Score": qa_data["评分"],
                "ScoringDetails": qa_data["评分细节"],
                "PersonalizedFeedback": qa_data["个性化反馈"],
                "Language": "Chinese"
            }

        result["GenerationIndex"] = attempt
        result["GenerationTime"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with file_lock:  # Thread-safe file writing
            with open(output_file, 'a', encoding='utf-8') as outfile:
                outfile.write(json.dumps(result, ensure_ascii=False) + '\n')

        print(f"Saved successfully: {subject}-{level}-{question_type} (Attempt {attempt})")
        return True
    except Exception as e:
        print(f"Processing failed for {subject}-{level}-{question_type}: {e}")
        return False

def process_subject_combinations(subject: str, level: str, question_type: str, question: str, standard_answer: str,
                            grading_criteria: str, student_answer: str, is_english: bool,
                                output_file: str, thread_count: int = 5):
    """Process all question types for a single subject-level combination"""
    question_types = ["Multiple Choice", "True/False", "Short Answer"] if is_english else ["选择题", "判断题", "简答题"]

    # We need 4 successful generations for each question type
    tasks = []
    for qt in question_types:
        for attempt in range(1, 2):  # 4 attempts per question type
            tasks.append((subject, level, qt, attempt))

    completed = 0
    total = len(tasks)

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = []
        for subject, level, qt, attempt in tasks:
            futures.append(
                executor.submit(
                    process_single_question,
                    subject=subject,
                    level=level,
                    question_type=qt,
                    question=question,
                    standard_answer=standard_answer,
                    grading_criteria=grading_criteria,
                    student_answer=student_answer,
                    is_english=is_english,
                    output_file=output_file,
                    attempt=attempt
                )
            )

        for future in as_completed(futures):
            completed += 1
            if future.result():
                print(f"Progress: {completed}/{total} completed successfully")
            else:
                print(f"Progress: {completed}/{total} completed with failures")

def load_data(input_file: str) -> List[dict]:
    """
    从JSONL文件中读取数据，提取所需字段并返回字典列表
    
    Args:
        input_file: JSONL文件路径
        
    Returns:
        包含所需字段的字典列表，每个字典对应一条数据
    """
    data_list = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    # 解析单条JSON数据
                    data = json.loads(line)
                    
                    # 提取所需字段（根据process_single_question函数参数确定）
                    required_fields = {
                        "subject": data.get("Subject"),
                        "level": data.get("Level"),
                        "question_type": data.get("QuestionType"),
                        "question": data.get("Question"),
                        "standard_answer": data.get("StandardAnswer"),
                        "grading_criteria": data.get("GradingCriteria"),
                        "student_answer": data.get("StudentAnswer"),
                        "is_english": data.get("Language") == "English"
                    }
                    
                    # 检查必要字段是否存在
                    missing_fields = [k for k, v in required_fields.items() if v is None]
                    if missing_fields:
                        print(f"警告：第{line_num}行缺少字段 {missing_fields}，已跳过")
                        continue
                    
                    data_list.append(required_fields)
                    
                except json.JSONDecodeError as e:
                    print(f"警告：第{line_num}行JSON解析错误 - {e}，已跳过")
                except Exception as e:
                    print(f"警告：第{line_num}行处理错误 - {e}，已跳过")
                    
        print(f"成功从 {input_file} 加载 {len(data_list)} 条有效数据")
        return data_list
        
    except FileNotFoundError:
        print(f"错误：文件 {input_file} 不存在")
        return []
    except Exception as e:
        print(f"加载数据时发生错误：{e}")
        return []


def process_all_subjects(data_list: List[dict], output_file: str, thread_count: int = 5):
    """处理所有主题数据"""
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = []
        total = len(data_list)
        completed = 0
        
        for item in data_list:
            futures.append(
                executor.submit(
                    process_single_question,
                    subject=item["subject"],
                    level=item["level"],
                    question_type=item["question_type"],
                    question=item["question"],
                    standard_answer=item["standard_answer"],
                    grading_criteria=item["grading_criteria"],
                    student_answer=item["student_answer"],
                    is_english=item["is_english"],
                    output_file=output_file,
                    attempt=1  # 可以根据需要调整尝试次数
                )
            )
        
        for future in as_completed(futures):
            completed += 1
            status = "成功" if future.result() else "失败"
            print(f"处理进度：{completed}/{total}，状态：{status}")

def main():
    # Configuration
    output_dir = os.getenv("OUTPUT_DIR", "./deepseek_output")
    output_file = os.path.join(output_dir, f"deepseek_generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl")
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    thread_count = 5  # Adjust this number to control thread count


    # Process Chinese data
    input_file = "deepseek_output/judge-1-process.jsonl"
    data_list = load_data(input_file)
    print(f"\nStarting Chinese generation with {thread_count} threads...")


    process_all_subjects(data_list,
                        output_file=output_file, thread_count=thread_count)

    

if __name__ == "__main__":
    main()