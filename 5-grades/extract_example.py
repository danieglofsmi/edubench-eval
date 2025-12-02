import json
import re

file = "5-grades/example.jsonl"
with open(file, 'r', encoding='utf-8') as f:
    lines = [json.loads(line) for line in f]
    for line in lines:
        json_pattern = re.search(r'```json\s*([\{$$].*?[$$\}])\s*```', line['response'], re.DOTALL)
        if json_pattern:
            text = json_pattern.group(1)
        else:
            print("Format Error: ",line['response'])
            continue
            # print(text)
        try:
            # 解析为Python对象
            data = json.loads(text)
            print(data)
            for item in data['generated_responses']:
                example = {}
                if 'score' in item and 'reason' in item and 'response' in item:
                    example['score'] = item['score']
                    example['reason'] = item['reason']
                    example['model'] = 'DeepSeek-V3.2-Exp'
                    example['response'] = item['response']
                    example['eval'] = 'DeepSeek-V3.2-Exp'

                print(example)
        except:
            print("无法解析以下内容为JSON：")
            print(text)
            # raise  # 忽略无法解析的块
