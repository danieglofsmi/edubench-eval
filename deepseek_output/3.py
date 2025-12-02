import json
from typing import List, Set

def load_questions(file_path: str) -> Set[str]:
    """从JSONL文件中加载所有Question字段，返回集合（去重）"""
    questions = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:  # 跳过空行
                    continue
                try:
                    data = json.loads(line)
                    # 确保Question字段存在且为字符串
                    if isinstance(data.get('Question'), str):
                        questions.add(data['Question'])
                    else:
                        print(f"警告：文件 {file_path} 第 {line_num} 行缺少有效的 Question 字段，已跳过")
                except json.JSONDecodeError as e:
                    print(f"错误：文件 {file_path} 第 {line_num} 行JSON格式错误 - {str(e)}，已跳过")
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 不存在！")
        raise  # 抛出异常，终止程序
    return questions

def find_unique_data(source_file: str, compare_file: str, output_file: str) -> None:
    """
    找出source_file中Question不在compare_file中的数据，保存到output_file
    
    参数：
        source_file: 源JSONL文件（要筛选的文件）
        compare_file: 对比JSONL文件（用来判断是否存在的文件）
        output_file: 结果输出文件
    """
    print(f"开始处理：源文件={source_file}，对比文件={compare_file}，输出文件={output_file}")
    
    # 1. 加载对比文件的所有Question
    print("正在加载对比文件的Question字段...")
    compare_questions = load_questions(compare_file)
    print(f"对比文件共加载 {len(compare_questions)} 个不重复的Question")
    
    # 2. 筛选源文件中的独有数据
    unique_count = 0
    print("正在筛选源文件中的独有数据...")
    with open(source_file, 'r', encoding='utf-8') as in_f, \
         open(output_file, 'w', encoding='utf-8') as out_f:
        
        for line_num, line in enumerate(in_f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                question = data.get('Question')
                # 只有当Question存在、为字符串，且不在对比集合中时，才视为独有数据
                if isinstance(question, str) and question not in compare_questions:
                    # 保持原始JSON格式写入（避免json.dumps重新格式化）
                    out_f.write(line + '\n')
                    unique_count += 1
            except json.JSONDecodeError as e:
                print(f"错误：源文件 {source_file} 第 {line_num} 行JSON格式错误 - {str(e)}，已跳过")
    
    # 3. 输出结果统计
    print(f"\n处理完成！")
    print(f"源文件中独有的Question数量：{unique_count}")
    print(f"独有数据已保存到：{output_file}")


SOURCE_FILE = "deepseek_output/judge-1-process.jsonl"       # 你的第一个JSONL文件（要找出其中独有的数据）
COMPARE_FILE = "deepseek_output/deepseek_generated_20251124_204411.jsonl"      # 你的第二个JSONL文件（用来对比的文件）
OUTPUT_FILE = "deepseek_output/unique_questions.jsonl"  # 输出结果的JSONL文件


if __name__ == "__main__":
    find_unique_data(SOURCE_FILE, COMPARE_FILE, OUTPUT_FILE)