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

# Prompt templates
# prompt_template_zh = """
# 你需要实现：
# 1. 客观打分能力：（选择、判断、填空）；对给出步骤分数或者打分参考的解答题进行打分；
# 2. 主观打分能力：对课程大作业、实验报告等从不同维度，例如工作量、完整性、知识运用程度等维度进行综合评估打分；
# 3. 个性化反馈能力：可以针对学生答题情况生成具体、有建设性的反馈意见，例如可能涉及的知识盲区，学习建议等；【打分+建议】

# 请针对以下学科和难度级别自由生成一个合适的问题和学生的回答，针对学生的答案给出评分。问题类型为{question_type}。
# 如果类型为简答题，对于特定的某些学科，必要的话给出代码和数学计算过程。不要返回多余的内容。

# 学科：{subject}
# 难度级别：{level}

# 以json格式返回
# "问题":""
# "学生的答案":""
# "评分":""
# "评分细节":""
# "个性化反馈":""
# """
prompt_template_zh = """
你需要实现：
1. 请针对以下学科、教育阶段和题目类型，生成一个适合出现在该阶段试卷中的题目及其标准答案，并生成具体的评分细则。注意题目的合理性。
- 1.1 对于数学、物理、计算机科学等学科中需要计算推导的题目，在标准答案中给出必要的数学和代码过程。但不要返回多余的内容。
- 1.2 评分细则应当包含题目总分值和得分标准。如：
    - 对于单选题和判断题，错答不得分；
    - 对于多选题，多选、漏选、错选均不得分，或漏选可得部分分数，多选、错选不得分；
    - 对于简答题，给出具体给分点，例如知识点运用、逻辑合理性、答案完整性等。
2. 针对生成的题目，生成一个在考试或作业中可能出现的学生回答。
3. 针对题目的评分细则和学生回答，生成评分和评分细节。
4. 针对学生答题情况生成具体、有建设性的反馈意见，例如可能涉及的知识盲区，学习建议等。

学科：{subject}
教育阶段：{level}
题目类型：{question_type}

以json格式返回
"问题":""
"标准答案":""
"评分细则":""
"学生的答案":""
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
1. Generate a question suitable for an exam at the given educational stage, along with its standard answer and specific grading criteria, based on the specified subject, educational level, and question type. Ensure the reasonableness of the question.
- 1.1 For subjects such as mathematics, physics, and computer science that require calculation or derivation, provide necessary mathematical steps or code processes in the standard answer. Do not include any extraneous content.
- 1.2 The grading criteria should include the total score and scoring standards. For example:
   - For multiple-choice question with single correct answers and True/False questions, incorrect answers receive no points.
   - For multiple-choice question with multiple correct answers, selecting all incorrect options, missing correct options, or selecting wrong options results in no points, or partial points may be awarded for incomplete selections, while incorrect or extra selections receive no points.
   - For short-answer questions, specify scoring points such as knowledge application, logical reasoning, and answer completeness.
2. Based on the generated question, create a sample student response that might appear in an exam or assignment.
3. Evaluate the sample student response according to the grading criteria and provide a score and detailed scoring breakdown.
4. Generate specific and constructive feedback based on the student's response, such as potential knowledge gaps and learning suggestions.

Subject: {subject}
Educational Level: {level}
Question Type: {question_type}

Return the result in JSON format:
"Question": "",
"Standard Answer": "",
"Grading Criteria": "",
"Student's Answer": "",
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
            required_keys = ["Question", "Standard Answer", "Grading Criteria", "Student's Answer", "Score", "Scoring Details", "Personalized Feedback"]
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
            required_keys = ["问题", "标准答案","评分细则", "学生的答案", "评分", "评分细节", "个性化反馈"]
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

def process_single_question(subject: str, level: str, question_type: str, is_english: bool,
                           output_file: str, attempt: int) -> bool:
    """Process a single question generation attempt"""
    prompt_template = prompt_template_en if is_english else prompt_template_zh
    prompt = prompt_template.format(
        subject=subject,
        level=level,
        question_type=question_type
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
                "Question": qa_data["Question"],
                "StandardAnswer": qa_data["Standard Answer"],
                "GradingCriteria": qa_data["Grading Criteria"],
                "StudentAnswer": qa_data["Student's Answer"],
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
                "Question": qa_data["问题"],
                "StandardAnswer": qa_data["标准答案"],
                "GradingCriteria": qa_data["评分细则"],
                "StudentAnswer": qa_data["学生的答案"],
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

def process_subject_combinations(subject: str, level: str, is_english: bool,
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

def process_all_subjects(subject_list: List[Tuple[str, str]], is_english: bool,
                        output_file: str, thread_count: int = 5):
    """Process all subject-level combinations"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Create empty file or clear existing content
    with open(output_file, 'w', encoding='utf-8') as f:
        pass

    for idx, (subject, level) in enumerate(subject_list, 1):
        print(f"\nProcessing [{idx}/{len(subject_list)}] {subject}-{level}")
        process_subject_combinations(subject, level, is_english, output_file, thread_count)

def load_subject_list(is_english: bool) -> List[Tuple[str, str]]:
    """Return subject and level list in either English or Chinese"""
    if is_english:
        return [
            # Basic Education
            # *[(subj, level) for subj in ["Chinese", "Mathematics", "English", "Physics", "Chemistry", "Biology", "History", "Geography"]
            #   for level in ["Elementary School", "Middle School", "High School"]],
            
            # # Higher Education
            # *[(subj, level) for subj in [
            #     "Computer Science", "Automation",
            #     "Applied Economics"
            # ] for level in ["Undergraduate", "Master"]]

            # Higher Education
            *[(subj, level) for subj in [
                "Mathematics", "Physics", "Chemistry", "Biology",
                "Computer Science", "Automation",
                "Aquaculture", "Crop Science",
                "Applied Economics", "Theoretical Economics",
                "General Pedagogy", "Physical Education",
                "Law",
                "Business Administration", "Public Administration",
                "Basic Medicine", "Clinical Medicine",
                "Sociology", "Literature and Art", "Psychology", "History", "Military Science"
            ] for level in ["Undergraduate", "Master", "PhD"]]
        ]
    else:
        return [
            # 基础教育
            # *[(subj, level) for subj in ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理"]
            #   for level in ["小学", "初中", "高中"]],
            
            # 高等教育
            *[(subj, level) for subj in [
                "数学", "物理学", "化学", "生物学",
                "理论经济学","商业管理学", "公共管理学",
                "普通教育学", "体育教育学",
                "法学",
                "商业管理学", "公共管理学",
                "基础医学", "临床医学",
                "社会学", "文学与艺术", "心理学", "历史学", "军事学"
            ] for level in ["大学", "硕士", "博士"]]

            # # 高等教育
            # *[(subj, level) for subj in [
            #     "数学", "物理学", "化学", "生物学",
            #     "计算机科学", "自动控制",
            #     "水产养殖", "作物科学",
            #     "应用经济学", "理论经济学",
            #     "普通教育学", "体育教育学",
            #     "法学",
            #     "商业管理学", "公共管理学",
            #     "基础医学", "临床医学",
            #     "社会学", "文学与艺术", "心理学", "历史学", "军事学"
            # ] for level in ["大学", "硕士", "博士"]]
        ]

def main():
    # Configuration
    output_dir = os.getenv("OUTPUT_DIR", "./deepseek_output")
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    thread_count = 5  # Adjust this number to control thread count

    # Process English data
    # english_file = os.path.join(output_dir, f"en_judge_{current_time}.jsonl")
    # english_subjects = load_subject_list(is_english=True)
    # print(f"\nStarting English generation with {thread_count} threads...")
    # process_all_subjects(english_subjects, is_english=True,
    #                     output_file=english_file, thread_count=thread_count)

    # Process Chinese data
    chinese_file = os.path.join(output_dir, f"zh_judge_{current_time}.jsonl")
    chinese_subjects = load_subject_list(is_english=False)
    print(f"\nStarting Chinese generation with {thread_count} threads...")
    process_all_subjects(chinese_subjects, is_english=False,
                        output_file=chinese_file, thread_count=thread_count)

    print(f"\nProcessing completed. Results saved to:")
    print(f"- English: {english_file}")
    print(f"- Chinese: {chinese_file}")

    # 关机功能（添加在main函数最后）
    # try:
    #     if os.name == 'nt':  # Windows系统
    #         print("\n程序执行完成，准备关机...")
    #         print("系统将在30秒后关机，如需取消请运行: shutdown /a")
    #         os.system("shutdown /s /t 30")  # 30秒后关机
    #     else:  # Linux/Mac系统
    #         print("\n程序执行完成，准备关机...")
    #         print("系统将在1分钟后关机，如需取消请运行: sudo shutdown -c")
    #         os.system("sudo shutdown -h +1")  # 1分钟后关机
    # except Exception as e:
    #     print(f"\n关机命令执行失败: {e}")
    #     print("请手动关闭计算机")


if __name__ == "__main__":
    main()