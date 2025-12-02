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


prompt_template_en = """
我将提供一个教育场景下的任务以及相应回复。请根据给定的评估指标和评分规则对回复进行评分，并以JSON格式输出分数及评分依据。
# 评分指标和评分规则：
## 指令遵循与任务完成: 是否完全理解并执行了用户的指令？是否完成了指定的核心任务（如解题、纠错、出题）？输出的格式是否符合要求？
    - 评分规则: 
        "5分： 完全理解并精准执行所有指令，完美达成核心任务目标，格式完全符合要求。",
        "4分： 准确理解主要指令，正确执行任务，核心目标达成度高，格式基本符合要求，可能有极少细节遗漏或偏差。",
        "3分： 理解了指令大意但可能忽略部分细节，任务基本完成但存在一些不准确或遗漏之处，格式有明显尝试但存在较多偏差。",
        "2分： 对指令理解有偏差，任务完成度低或有严重错误，格式多数不符合要求。",
        "1分： 完全误解或无视指令，任务未完成或完全错误，格式混乱或不相关。"
## 内容相关性与范围控制: 输出内容是否紧密围绕指定的知识点、主题或问题？是否控制在要求的难度、范围或学科领域内？
    - 评分规则:
        "5分： 内容与指定知识点/主题/问题高度相关，且严格控制在要求的难度、范围、学科内，无冗余或无关信息。",
        "4分： 内容主体相关，范围控制良好，可能包含极少量轻微超纲或关联度稍弱的信息。",
        "3分： 内容大部分相关，但包含一些偏离主题或超出范围的部分，范围控制不够精确。",
        "2分： 内容相关性较差，包含较多无关信息，或严重超出指定范围。",
        "1分： 内容基本不相关，或完全脱离指定范围。"
## "基础事实准确性": 涉及的概念定义、公式、日期、专有名词、代码语法、法律条文等客观信息是否准确无误？
     - 评分规则:
        "5分： 所有涉及的客观事实（定义、公式、日期、名词、代码语法等）完全准确无误。",
        "4分： 绝大部分事实准确，可能存在个别极其微小的、非关键性的笔误或疏漏。",
        "3分： 大部分事实准确，但存在少量明显的事实错误，需要核查。",
        "2分： 包含较多或关键性的事实错误，信息不可靠。",
        "1分： 充斥着大量事实错误，信息完全错误或误导。"
## "推理过程严谨性": 对于需要推理、演算、论证的内容（如数学解题步骤、代码逻辑、法律分析、案例解释），其逻辑链条是否完整、严密、无懈可击？
    - 评分规则:
        "5分： 推理逻辑链条完整、清晰、严密，步骤正确无误，论证充分有力，无逻辑跳跃或漏洞。",
        "4分： 推理过程主体正确且逻辑清晰，可能在个别步骤的表述或论证细节上略有瑕疵，但不影响最终结论的有效性。",
        "3分： 推理过程大体可见，但存在一些逻辑不清、步骤缺失或论证不足之处，结论可能受到影响。",
        "2分： 推理过程存在明显的逻辑错误、步骤混乱或严重缺失，难以得出正确或可靠的结论。",
        "1分： 几乎没有有效的推理过程，逻辑混乱，步骤完全错误或不相关。"

## "错误识别与纠正精确性":"在纠错场景下，定位错误是否准确（无漏报、无误报）？给出的纠正建议是否正确且最优？
     - 评分规则:
        "5分： 精准定位所有错误（无遗漏、无误报），给出的纠正建议完全正确、清晰且是最优或非常好的方案。",
        "4分： 准确定位了大部分主要错误，纠正建议基本正确有效，可能遗漏极少数次要错误或建议不够完美。",
        "3分： 定位了部分错误但有明显遗漏或误报，纠正建议部分正确但可能不够清晰、完整或并非最佳方案。",
        "2分： 错误定位不准确，遗漏了关键错误或大量误报，纠正建议存在错误或难以理解。",
        "1分： 完全未能识别错误，或给出了完全错误的纠正建议，起到了误导作用。"

## "激励引导与积极反馈": 交互中是否体现出对学生的鼓励和支持？是否倾向于使用积极、建设性的语言？在答疑或辅导时，是有效引导思考还是直接给出答案？
    - 评分规则:
        "5分： 始终体现出强烈的鼓励和支持态度，语言积极、富有建设性；在需要时提供非常有效的启发式引导，而非直接给答案。",
        "4分： 整体体现出鼓励和支持，语言积极正面；能提供有效的引导，偶尔可能过于直接。",
        "3分： 兼具鼓励和中性/批评性语言，积极性一般；引导有时有效，有时直接给答案或引导不足。",
        "2分： 缺乏鼓励和支持，语言偏中性甚至略显负面；很少提供有效引导，倾向于直接给答案或不给帮助。",
        "1分： 语言消极、打击性强，完全没有鼓励；无视引导需求，或提供错误引导。"

请根据以上评估指标和评分规则对下面的问题回复进行评分，并以JSON格式输出分数及评分依据。
# 问题：{question}
# 答案：{response}
# 输出的JSON格式定义如下：
{
"detailed_scores": [
{
"principle": "principle 1",
"score": 0,
"reason": ""
},
...
]
}
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