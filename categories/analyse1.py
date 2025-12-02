import re
from collections import defaultdict

def read_file(file_path):
    """读取文件内容"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def extract_files(text):
    """按 'File' 分割内容，提取每个 File 的部分"""
    # 使用正则表达式按 'File' 分割
    pattern = r"(File: [^\n]+)"
    files = re.split(pattern, text)
    files = [files[i] + files[i + 1] for i in range(1, len(files) - 1, 2)]
    return files

def extract_file_name(file_content):
    """从文件内容中提取 File 名称"""
    pattern = r"File: ([^\n]+)"
    match = re.search(pattern, file_content)
    return match.group(1).strip() if match else "Unknown"

def count_categories(file_content):
    """统计每个分类层级的数量"""
    # 提取括号内的元组
    pattern = r"\((.*?)\)\s*:\s*(\d+)"
    matches = re.findall(pattern, file_content)

    # 初始化字典
    result = defaultdict(lambda: defaultdict(int))

    # 统计每个分类层级的数量
    for match in matches:
        categories, count = match
        categories = categories.split("', '")
        count = int(count)

        # 动态处理多级分类
        current_dict = result
        for i, category in enumerate(categories):
            if i == len(categories) - 1:
                # 最后一层，直接累加数量
                current_dict[category] = count
                
            else:
                # 非最后一层，继续嵌套
                if category not in current_dict:
                    current_dict[category] = defaultdict(lambda: defaultdict(int))
                current_dict = current_dict[category]

    # 转换为普通字典并返回
    return dict(result)

def process_file(file_path):
    """处理文件，统计每个 File 的 Category counts"""
    # 读取文件内容
    text = read_file(file_path)

    # 提取每个 File 的内容
    files = extract_files(text)

    # 初始化结果字典
    results = {}

    # 遍历每个 File
    for file_content in files:
        # 提取 File 名称
        file_name = extract_file_name(file_content)
        # 统计 Category counts
        category_counts = count_categories(file_content)
        # 保存结果
        results[file_name] = category_counts

    return results


# 打开文件并统计符合条件的行数
def count_lines_with_prefix(file_path, prefix):
    count = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                # 检查行是否以指定的前缀开头
                if line.startswith(prefix):
                    count += 1
    except FileNotFoundError:
        print(f"文件 {file_path} 未找到，请检查路径是否正确。")
    except Exception as e:
        print(f"读取文件时发生错误：{e}")
    return count

# 文件路径
file_path = 'category_stats.txt'

prefix = '  ('  

# 调用函数并打印结果
line_count = count_lines_with_prefix(file_path, prefix)
print(f"文件 {file_path} 中以 '{prefix}' 开头的行数为：{line_count}")

# # 处理文件并获取结果
# results = process_file(file_path)


# 输出结果
# import json
# with open('EduBench/category.json','w', encoding='utf-8') as f:
#     json.dump(results,f, ensure_ascii=False, indent=2)