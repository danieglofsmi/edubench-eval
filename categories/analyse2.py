import json



def merge_design(in_path, out_path):
    with open(in_path,'r',encoding='utf-8')as f:
        data = json.load(f)

    new_data = {}
    for key, value in data.items():
        new_data[key] = {}
        k12_level = {}
        higher_education = {}

        for level, subjects in value.items():
            level = level.replace("'","")
            if level in ["小学", "初中", "高中", "Elementary School","Middle School","High School"]:
                for subject, count in subjects.items():
                    if subject in k12_level:
                        k12_level[subject] += count
                    else:
                        k12_level[subject] = count
            elif level in ["大学", "硕士", "博士","Undergraduate","Master","PhD"]:
                for subject, count in subjects.items():
                    if subject in higher_education:
                        higher_education[subject] += count
                    else:
                        higher_education[subject] = count

        # 将合并后的数据存入新的数据结构
        new_data[key]["k12 level"] = k12_level
        new_data[key]["higher education"] = higher_education

        # 添加合计
        for level in ["k12 level", "higher education"]:
            total = 0
            for subject in new_data[key][level].items():
                total += subject[-1]
                new_data[key][level]["总合计"] = total

    # 将新的数据结构写入新的JSON文件
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=4)



def reorganize():
    # 加载原始JSON数据
    with open('EduBench/category_no_design.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

        # 创建一个新的字典来存储转换后的数据
        new_data = {}

        # 遍历原始数据并重新组织结构
        for key, value in data.items():
            new_data[key] = {}
            for subject, levels in value.items():
                for level, questions in levels.items():
                    if level not in new_data[key]:
                        new_data[key][level] = {}
                    new_data[key][level][subject] = questions

        # 将新的数据结构写入新的JSON文件
        with open('EduBench/category_reorganized.json', 'w', encoding='utf-8') as file:
            json.dump(new_data, file, ensure_ascii=False, indent=4)

def merge(in_path,out_path):
    with open(in_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # 创建一个新的字典来存储合并后的数据
    new_data = {}

    # 遍历每个文件
    for file_name, content in data.items():
        new_data[file_name] = {
            "'k12 level": {},
            "'higher education": {}
        }
        
        # 遍历每个学段
        for level, subjects in content.items():
            # 合并小学、初中、高中到k12 level
            level = level.replace("'","")
            if level in ["小学", "初中", "高中","Elementary School","Middle School","High School"]:
                target_level = "'k12 level"
            # 合并大学、硕士、博士到higher education
            elif level in ["大学", "硕士", "博士","Undergraduate","Master","PhD"]:
                target_level = "'higher education"
            else:
                continue  # 跳过其他未知的级别
            
            # 遍历每个学科
            for subject, questions in subjects.items():
                if subject not in new_data[file_name][target_level]:
                    new_data[file_name][target_level][subject] = {}
                
                # 合并问题类型
                try:
                    for question_type, count in questions.items():
                        if question_type not in new_data[file_name][target_level][subject]:
                            new_data[file_name][target_level][subject][question_type] = 0
                        new_data[file_name][target_level][subject][question_type] += count
                except:
                    print(subject, questions)

        # 添加合计
        for level in ["'k12 level", "'higher education"]:
            for subject, questions in new_data[file_name][level].items():
                total = sum(questions.values())
                new_data[file_name][level][subject]["合计"] = total

        # 添加每个级别的总合计
        for level in ["'k12 level", "'higher education"]:
            total_sum = 0
            for subject, questions in new_data[file_name][level].items():
                total_sum += questions["合计"]
            new_data[file_name][level]["总合计"] = total_sum

    # 将新的数据结构写入新的JSON文件
    with open(out_path, 'w', encoding='utf-8') as file:
        json.dump(new_data, file, ensure_ascii=False, indent=4)



# reorganize()
merge_design('EduBench/category.json','EduBench/category_merge_1.json')
# merge('EduBench/category_reorganized.json','EduBench/category_merge_2.json')

# with open('EduBench/category_merge_2.json', 'r', encoding='utf-8') as file:
#     data = json.load(file)
#     files = list(data.keys())
#     for file_name in files:
#         for level in ["'k12 level", "'higher education"]:
#             print(f"{file_name}, {level}", data[file_name][level]["总合计"])