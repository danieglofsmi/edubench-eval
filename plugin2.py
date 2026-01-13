import re
from typing import List
import json

from swift.plugin import ORM, orms
from swift.utils import get_logger
logger = get_logger()

def extract_label(output_text):
    """从output中提取label"""
    try:
        # 查找JSON部分
        json_start = output_text.find('[')
        json_end = output_text.rfind(']') + 1
        
        if json_start != -1 and json_end != 0:
            json_str = output_text[json_start:json_end]
            
            # 使用eval解析
            result_list = eval(json_str)
            
            if result_list and isinstance(result_list, list) and len(result_list) > 0:
                return result_list[0].get('score', None)
    except:
        pass
    
    # 如果以上方法失败，尝试正则匹配
    score_match = re.search(r'"score":\s*(\d+)', output_text)
    if score_match:
        return int(score_match.group(1))
    
    score_match = re.search(r"'score':\s*(\d+)", output_text)
    if score_match:
        return int(score_match.group(1))
    
    return None

def calculate_Format(input_str):
    """
    检查字符串格式是否符合要求：
    1. 包含完整合法的JSON结构（被```json和```包裹）
    2. JSON数据中包含criterion、score、reason三个字段
    
    Args:
        input_str (str): 需要检查的字符串
        
    Returns:
        float: 1=格式完全正确，0=缺少必填字段，0.5=字段完整但JSON格式错误
    """
    # 步骤1：提取```json和```之间的JSON内容
    json_pattern = r'```json([\s\S]*?)```'
    matches = re.findall(json_pattern, input_str)
    
    if not matches:
        # 无JSON包裹，视为字段缺失类错误
        return 0
    
    # 取第一个匹配到的JSON内容（去除首尾空白字符）
    json_content = matches[0].strip()
    
    # 步骤2：先尝试解析JSON，验证格式合法性
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError:
        # JSON格式错误，需要先检查字段是否存在（即使格式错也能粗略检查）
        # 粗略检查是否包含三个字段的关键词（格式错误时的降级检查）
        has_criterion = 'criterion' in json_content
        has_score = 'score' in json_content
        has_reason = 'reason' in json_content
        
        if has_criterion and has_score and has_reason:
            # 字段完整但JSON格式错误，返回0.5
            return 0.5
        else:
            # 字段缺失，返回0
            return 0
    
    # 步骤3：JSON格式正确，检查字段完整性
    missing_fields = []
    
    # 处理数组情况
    if isinstance(data, list):
        if len(data) == 0:
            return 0
        
        # 检查第一个元素（也可遍历所有元素，根据需求调整）
        item = data[0]
        if not isinstance(item, dict):
            return 0
        
        for field in ['criterion', 'score', 'reason']:
            if field not in item:
                missing_fields.append(field)
    
    # 处理单个对象情况
    elif isinstance(data, dict):
        for field in ['criterion', 'score', 'reason']:
            if field not in data:
                missing_fields.append(field)
    
    # 非数组/对象类型
    else:
        return 0
    
    # 根据字段检查结果返回对应值
    if missing_fields:
        return 0
    else:
        return 1

class Accuracy(ORM):
    def __call__(self, completions, solution, **kwargs) -> List[float]:
        rewards = []
        for content, sol in zip(completions, solution):
            predict = extract_label(content)
            if predict is None:
                accuracy_reward = 0.0
            else:
                accuracy_reward = 1/(1+abs(predict - sol))

            rewards.append(accuracy_reward)
        return rewards

class Format(ORM):
    def __call__(self, completions, **kwargs) -> List[float]:
        """Reward function that checks if the completion has a specific format."""
        # pattern = r'^<think>.*?</think>\n<answer>.*?</answer>(?![\s\S])'
        # matches = [re.match(pattern, content, re.DOTALL | re.MULTILINE) for content in completions]
        rewards = []

        for content in completions:
            format_reward = calculate_Format(content)

            rewards.append(format_reward)
        return rewards

orms['accuracy'] = Accuracy
orms['format'] = Format


# string = "```json[{\"criterion\": \"激励引导与积极反馈\", \"score\": 2, \"reason\": \"缺乏鼓励和支持，语言偏中性，倾向于直接给出正确答案\"}]```"
# print(calculate_Format(string))
# print(extract_label(string))