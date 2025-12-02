import json
import pandas as pd
import random
import re

# 生成excel

# 定义评分标准和规则
scoring_criteria = [
    {
        "name": "## 指令遵循与任务完成",
        "description": "是否完全理解并执行了用户的指令？是否完成了指定的核心任务（如解题、纠错、出题）？输出的格式是否符合要求？",
        "rules": [
            "5分： 完全理解并精准执行所有指令，完美达成核心任务目标，格式完全符合要求。",
            "4分： 准确理解主要指令，正确执行任务，核心目标达成度高，格式基本符合要求，可能有极少细节遗漏或偏差。",
            "3分： 理解了指令大意但可能忽略部分细节，任务基本完成但存在一些不准确或遗漏之处，格式有明显尝试但存在较多偏差。",
            "2分： 对指令理解有偏差，任务完成度低或有严重错误，格式多数不符合要求。",
            "1分： 完全误解或无视指令，任务未完成或完全错误，格式混乱或不相关。"
        ]
    },
    {
        "name": "## 内容相关性与范围控制",
        "description": "输出内容是否紧密围绕指定的知识点、主题或问题？是否控制在要求的难度、范围或学科领域内？",
        "rules": [
            "5分： 内容与指定知识点/主题/问题高度相关，且严格控制在要求的难度、范围、学科内，无冗余或无关信息。",
            "4分： 内容主体相关，范围控制良好，可能包含极少量轻微超纲或关联度稍弱的信息。",
            "3分： 内容大部分相关，但包含一些偏离主题或超出范围的部分，范围控制不够精确。",
            "2分： 内容相关性较差，包含较多无关信息，或严重超出指定范围。",
            "1分： 内容基本不相关，或完全脱离指定范围。"
        ]
    },
    {
        "name": "## 基础事实准确性",
        "description": "涉及的概念定义、公式、日期、专有名词、代码语法、法律条文等客观信息是否准确无误？",
        "rules": [
            "5分： 所有涉及的客观事实（定义、公式、日期、名词、代码语法等）完全准确无误。",
            "4分： 绝大部分事实准确，可能存在个别极其微小的、非关键性的笔误或疏漏。",
            "3分： 大部分事实准确，但存在少量明显的事实错误，需要核查。",
            "2分： 包含较多或关键性的事实错误，信息不可靠。",
            "1分： 充斥着大量事实错误，信息完全错误或误导。"
        ]
    },
    {
        "name": "## 推理过程严谨性",
        "description": "对于需要推理、演算、论证的内容（如数学解题步骤、代码逻辑、法律分析、案例解释），其逻辑链条是否完整、严密、无懈可击？",
        "rules": [
            "5分： 推理逻辑链条完整、清晰、严密，步骤正确无误，论证充分有力，无逻辑跳跃或漏洞。",
            "4分： 推理过程主体正确且逻辑清晰，可能在个别步骤的表述或论证细节上略有瑕疵，但不影响最终结论的有效性。",
            "3分： 推理过程大体可见，但存在一些逻辑不清、步骤缺失或论证不足之处，结论可能受到影响。",
            "2分： 推理过程存在明显的逻辑错误、步骤混乱或严重缺失，难以得出正确或可靠的结论。",
            "1分： 几乎没有有效的推理过程，逻辑混乱，步骤完全错误或不相关。"
        ]
    },
    {
        "name": "## 错误识别与纠正精确性",
        "description": "在纠错场景下，定位错误是否准确（无漏报、无误报）？给出的纠正建议是否正确且最优？",
        "rules": [
            "5分： 精准定位所有错误（无遗漏、无误报），给出的纠正建议完全正确、清晰且是最优或非常好的方案。",
            "4分： 准确定位了大部分主要错误，纠正建议基本正确有效，可能遗漏极少数次要错误或建议不够完美。",
            "3分： 定位了部分错误但有明显遗漏或误报，纠正建议部分正确但可能不够清晰、完整或并非最佳方案。",
            "2分： 错误定位不准确，遗漏了关键错误或大量误报，纠正建议存在错误或难以理解。",
            "1分： 完全未能识别错误，或给出了完全错误的纠正建议，起到了误导作用。"
        ]
    },
    {
        "name": "## 激励引导与积极反馈",
        "description": "交互中是否体现出对学生的鼓励和支持？是否倾向于使用积极、建设性的语言？在答疑或辅导时，是有效引导思考还是直接给出答案？",
        "rules": [
            "5分： 始终体现出强烈的鼓励和支持态度，语言积极、富有建设性；在需要时提供非常有效的启发式引导，而非直接给答案。",
            "4分： 整体体现出鼓励和支持，语言积极正面；能提供有效的引导，偶尔可能过于直接。",
            "3分： 兼具鼓励和中性/批评性语言，积极性一般；引导有时有效，有时直接给答案或引导不足。",
            "2分： 缺乏鼓励和支持，语言偏中性甚至略显负面；很少提供有效引导，倾向于直接给答案或不给帮助。",
            "1分： 语言消极、打击性强，完全没有鼓励；无视引导需求，或提供错误引导。"
        ]
    }
]


def process_jsonl_files(file_path, output_excel_path, sample_size=165):
    """
    处理两个JSONL文件，随机选择数据并生成Excel文件
    
    参数:
    file1_path (str): 第一个JSONL文件路径
    file2_path (str): 第二个JSONL文件路径
    output_excel_path (str): 输出的Excel文件路径
    sample_size (int): 从每个文件随机选择的数据条数，默认165
    """
    
    def read_jsonl_file(file_path):
        """读取JSONL文件并返回数据列表"""
        data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            item = json.loads(line)
                            data.append(item)
                        except json.JSONDecodeError:
                            print(f"警告: 跳过无效的JSON行 in {file_path}")
        except FileNotFoundError:
            print(f"错误: 文件 {file_path} 不存在")
            return []
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}")
            return []
        return data
    
    def process_item(item):
        """处理单个数据项，生成Excel需要的两列数据"""
        # 第一列数据：用\n拼接的字段（key:value形式）
        col1_content = item.get('Level', '')
        col2_fields = [
            f"Subject: {item.get('Subject', '')}",
            f"Level: {item.get('Level', '')}",
            f"QuestionType: {item.get('QuestionType', '')}",
            f"Question: {item.get('Question', '')}",
            f"StandardAnswer: {item.get('StandardAnswer', '')}",
            f"GradingCriteria: {item.get('GradingCriteria', '')}",
            f"StudentAnswer: {item.get('StudentAnswer', '')}"
        ]
        col2_content = '\n'.join(col2_fields)

        # 第二列数据：用\n拼接的字段（key:value形式）
        col3_fields = [
            f"Score: {item.get('Score', '')}",
            f"ScoringDetails: {item.get('ScoringDetails', '')}",
            f"PersonalizedFeedback: {item.get('PersonalizedFeedback', '')}"
        ]
        col3_content = '\n'.join(col3_fields)
        
        return col1_content, col2_content, col3_content
    
    # 读取两个文件的数据
    print("正在读取文件...")
    # data1 = read_jsonl_file(file1_path)
    # data2 = read_jsonl_file(file2_path)

    data = read_jsonl_file(file_path)
    if not data:
        print("文件读取失败，请检查文件路径和格式")
        return
    
    print(f"文件读取到 {len(data)} 条数据")
    
    sampled_data = data

    # 处理数据
    print("正在处理数据...")
    excel_data = []
    
    # 处理第一个文件的数据
    zh_i = 1
    en_i = 1
    for i, item in enumerate(sampled_data, 1):  #索引从 1 开始计数
        col1, col2, col3 = process_item(item)
        if item['Language']=='Chinese':
            excel_data.append({
                '文件来源': f'zh-query{zh_i}',
                '层次': col1,
                '题目信息': col2,
                '评分信息': col3
            })
            zh_i += 1
        elif item['Language']=='English':
            excel_data.append({
                '文件来源': f'en-query{en_i}',
                '层次': col1,
                '题目信息': col2,
                '评分信息': col3
            })
            en_i += 1
        else:
            print(f"警告: 未知语言类型 {item['Language']}，跳过该条数据")



    # 为第一行数据添加评分标准列
    if excel_data:  # 确保有数据
        for i, criteria in enumerate(scoring_criteria, 1):
            # 构建评分标准内容
            criteria_content = f"{criteria['name']}\n{criteria['description']}\n\n评分规则:\n"
            for rule in criteria['rules']:
                criteria_content += f"- {rule}\n"
            
            column_name = f"评分标准{i}"
            excel_data[0][column_name] = criteria_content

        # 为其他行的评分标准列赋空值，保持列数一致
        for j in range(1, len(excel_data)):
            for i in range(1, len(scoring_criteria) + 1):
                column_name = f"评分标准{i}"
                excel_data[j][column_name] = ""

    # 然后继续原有的创建DataFrame和保存Excel的代码
    print("正在生成Excel文件...")
    df = pd.DataFrame(excel_data)

    # 设置Excel写入参数，确保格式正确
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='数据汇总', index=False)
        
        # 调整列宽
        worksheet = writer.sheets['数据汇总']
        worksheet.column_dimensions['A'].width = 10  # 文件来源列
        worksheet.column_dimensions['B'].width = 10  # 第一列
        worksheet.column_dimensions['C'].width = 30  # 第二列
        worksheet.column_dimensions['D'].width = 30  # 第三列
        
        # 调整评分标准列的宽度
        for i in range(len(scoring_criteria)):
            col_letter = chr(67 + i)  # 从D列开始（A=65, B=66, C=67, D=68...）
            worksheet.column_dimensions[col_letter].width = 40

    print(f"处理完成！")
    print(f"从文件随机选择了 {sample_size} 条数据")
    print(f"总共 {len(excel_data)} 条数据已保存到: {output_excel_path}")
    print(f"添加了 {len(scoring_criteria)} 个评分标准列")


def extract_level_to_b_column(input_file, output_file):
    """
    从C列提取Level字段的值到B列，并保存为新的Excel文件
    
    参数:
        input_file: 输入Excel文件路径
        output_file: 输出Excel文件路径
    """
    # 读取Excel文件
    df = pd.read_excel(input_file)
    
    # 确保B列存在（如果不存在则创建）
    if '层次' not in df.columns:
        df.insert(1, '层次', '')  # 在第2列位置插入B列
    
    # 正则表达式模式，用于匹配Level: 后面的内容
    pattern = r'Level:\s*([^\n,;]+)'  # 匹配Level: 后的内容，直到遇到换行、逗号或分号
    
    # 遍历每一行，提取Level值到B列
    for index, row in df.iterrows():
        c_column_value = str(row['题目/学生回答'])  # 获取C列的值并转为字符串
        match = re.search(pattern, c_column_value)
        if match:
            df.at[index, '层次'] = match.group(1).strip()  # 提取匹配内容并去除前后空格
        else:
            df.at[index, '层次'] = ''  # 如果没有找到Level字段，B列留空
    
    # 保存到新的Excel文件
    df.to_excel(output_file, index=False)
    print(f"处理完成，结果已保存到 {output_file}")


# 使用示例
if __name__ == "__main__":
    # 设置文件路径
    file1 = "deepseek_output/unique_questions.jsonl"  # 替换为你的第一个JSONL文件路径
    output_file = "deepseek_output/output3.xlsx" # 输出的Excel文件路径
    
    # 处理文件
    process_jsonl_files(file1,output_file, sample_size=14)
    # extract_level_to_b_column("deepseek_output/judge-内部标注.xlsx", output_file)

