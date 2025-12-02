# -*- encoding:utf-8 -*-
import random
import json
from openai import OpenAI
from tqdm import tqdm
import time
import concurrent.futures
import threading
import itertools
import sys
import os
import re

# GPT
# client = OpenAI(api_key="sk-LWzY4DovAFCgyNdgr1zgLYVvy1Moh3ErL6jwNur5jcs2jqRY", base_url="https://api.chatanywhere.tech/v1")
# BaiLian
# client = OpenAI(api_key="sk-d26f44789140496aa13d4e01def9d5c4", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
#  sk-fbc6bcfdb0ba4e3abe159906f0d3f798
# client = OpenAI(api_key="sk-2403a97b97e8498bb1b4e9accf1fa7c7", base_url="https://api.deepseek.com")
# 'gpt-4o'
# client = OpenAI(api_key="sk-LWzY4DovAFCgyNdgr1zgLYVvy1Moh3ErL6jwNur5jcs2jqRY", base_url="https://api.chatanywhere.tech/v1")

# client = OpenAI(api_key="sk-d26f44789140496aa13d4e01def9d5c4", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

# # BaiLian
# client = OpenAI(api_key="sk-bc238a1af6f44edd83b427a10bcdd3a5", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

# # deepseek
# ds_key = "sk-2403a97b97e8498bb1b4e9accf1fa7c7"
# client = OpenAI(api_key=ds_key, base_url="https://api.deepseek.com")

# paracloud
ds_key = "sk-2403a97b97e8498bb1b4e9accf1fa7c7"
client = OpenAI(api_key=ds_key, base_url="https://llmapi.paratera.com")

# # chatanywhere
# client = OpenAI(api_key="sk-VXzRQMF8cdJL1TONR2YQhDvNnm8yronUjGtgZXeGX7SCjwUH", base_url="https://api.chatanywhere.tech/v1")

# # openrouter
# client = OpenAI(base_url="https://openrouter.ai/api/v1",api_key="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",)

write_lock = threading.Lock()



template_prompt = """我将向你提供一个任务的题目以及一个评分标准，根据评分标准生成分数分别为1-3分的3个回复，不要中英文混杂，以json的形式返回。

# 评分任务：{principle}
# 题目：{question}
# 评分标准：{rules}

请你根据评分标准生成分数为1-3分的回复，以json的形式返回，下面提供一个参考示例。

# 参考示例:
## 评分任务：{example_principle}
## 示例题目：{example_question}
## 示例输出：{example}

JSON_FORMAT = ```json
{{
  "generated_responses": [
    {{
      "score": 1,
      "response": "",
      "reason": ""
    }},
    {{
      "score": 2,
      "response": "",
      "reason": ""
    }},
    {{
      "score": 3,
      "response": "",
      "reason": ""
    }}
  ]
}}
```"""



def send_request(prompt, model): 
    """发送请求到 OpenAI API 并返回结果（线程安全）"""
    try:
        if not 'qwq' in model and not 'r1' in model:
            response = client.chat.completions.create(
                model=model,    #'deepseek-chat'
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=1.3,
                max_completion_tokens=8192
            )
            return response.choices[0].message.content if response.choices else None
        else:
            reasoning_content = ""  # 定义完整思考过程
            answer_content = ""     # 定义完整回复
            is_answering = False   # 判断是否结束思考过程并开始回复

            # 创建聊天完成请求
            completion = client.chat.completions.create(
                model=model,  # 此处以 qwq-32b 为例，可按需更换模型名称
                messages=[
                    # {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
            )

            for chunk in completion:
                # 如果chunk.choices为空，则打印usage
                if not chunk.choices:
                    print("\nUsage:")
                    print(chunk.usage)
                else:
                    delta = chunk.choices[0].delta
                    # 打印思考过程
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                        reasoning_content += delta.reasoning_content
                    else:
                        # 开始回复
                        if delta.content != "" and is_answering is False:
                            is_answering = True
                        # 打印回复过程
                        answer_content += delta.content
            return answer_content
    except Exception as e:
        print(f"{model} API 请求失败: {e}")
        return None


def read_jsonl(jsonl_file):
    data = []
    with open(jsonl_file, "r", encoding="utf-8") as file:
        for line in file:
            record = json.loads(line)  # 解析每一行
            data.append(record)
    return data

def read_json(json_file):
    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data

def extract_json_from_response(response):
    json_pattern = re.search(r'```json\s*([\{$$].*?[$$\}])\s*```', response, re.DOTALL)
    if json_pattern:
        text = json_pattern.group(1)
    else:
        print("Format Error: ",response)
        # print(text)
    try:
        # 解析为Python对象
        data = json.loads(text)
        examples = []
        for item in data['generated_responses']:
            example = {}
            if 'score' in item and 'reason' in item and 'response' in item:
                example['score'] = item['score']
                example['reason'] = item['reason']
                example['model'] = 'DeepSeek-V3.2-Exp'
                example['response'] = item['response']
                example['eval'] = 'DeepSeek-V3.2-Exp'
                examples.append(example)

        return(examples)
    except:
        print("无法解析以下内容为JSON：")
        print(text)


def process_point_item(data, idx, output_file, model):
    max_retries = 5
    for _ in range(max_retries):
        try:  
            prompt = template_prompt.format(principle=data['principle'],rules=data['rules'],question=data['question'],example=data['example'],example_principle=data['example']['principle'],example_question=data['example']['question'])  
            print(prompt)
            return
            response = send_request(prompt,model)
            # print(response)
    
            if response is not None:
                examples = extract_json_from_response(response)
                print("examples:",examples)

                for example in examples:
                    meta = {}
                    meta['principle'] = data['principle']
                    meta['score'] = example['score']
                    meta['reason'] = example['reason']
                    meta['model'] = example['model']
                    meta['question'] = data['question']
                    meta['response'] = example['response']
                    meta['eval'] = example['eval']

                    with write_lock:
                        with open(output_file, 'a', encoding='utf-8') as f:
                            f.write(json.dumps(meta, ensure_ascii=False) + '\n')
                break
            else:
                time.sleep(10)
        except Exception as e:
            print(f"process_point_item Error: {e}")



def batch_process(data_list, output_file,model):
    """批量处理JSON数据（多线程版本）"""
    # 创建线程池（根据API限流调整workers数量）
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for idx, item in enumerate(data_list):
            futures.append(executor.submit(process_point_item, item, idx, output_file,model))

        # 使用进度条监控处理进度
        with tqdm(total=len(futures), desc="处理进度") as pbar:
            for future in concurrent.futures.as_completed(futures):
                pbar.update(1)

def generate(output_file,model):
    
    existed = set() # 当程序崩溃时,使数据能够断点续传,避免重复生成

    if not os.path.exists(output_file):  
        with open(output_file, 'w') as f:  
            f.write("")  
        print(f"{output_file} 不存在，已创建该文件。")  

    else:
        with open(output_file, 'r', encoding='utf-8') as f:
            if not f.readline().strip() == '':
                for line in f:
                    item = json.loads(line)
                    if item["response"] != "":
                        existed.add(item['question'])
            print(f"existed:{len(existed)}")

    metrics = read_json("5-grades/5_metrics_zh.json")
    question_set = read_json("5-grades/5_50_metric_v3_questions_zh.json")
    case_set = read_json("5-grades/1-shot_cases_zh.json")

    data_list = []
    for metric in question_set.keys():
        questions = question_set[metric][:2]
        for question in questions:
            if not question in existed:
                d = {
                    "principle": metric,
                    "rules": metrics[metric]['rules'],
                    "question": question,
                    # "example": case_set[metric]
                    "example": case_set["指令遵循与任务完成"]
                }
                data_list.append(d)

    print("data list: ",len(data_list))
    print(question_set.keys())

    batch_process(data_list, output_file,model)



# model = "deepseek-chat"
model = "DeepSeek-V3.2-Exp"
print(model)

output_file = '5-grades/example.jsonl'
generate(output_file,model)

# print(send_request(template_prompt,model))
# case_set = read_json("5-grades/1-shot_cases_zh.json")
# print()