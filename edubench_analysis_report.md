# EduBench 数据分析报告

## 一、分析背景与目标

本文档整合了前置实验记录与当前对 `/Users/liangxinyue/Downloads/edubench/results_merge.jsonl` 的定量分析结果，目标是同时回答两个问题：其一，不同生成模型在 EduBench 教育任务上的能力差异是什么；其二，不同自动评估方法相对人类评审的贴近程度、偏差模式和失效场景分别是什么。文档分为“已有发现”和“后续分析方案”两部分，并补充更深入的量化结果摘要。

## 二、数据概览

当前主分析文件共包含 5536 条记录，覆盖 9 个任务、5 个生成模型、24 个评估维度（含中英文 rubric 表达）。按任务分布为：idea_provision: 863，teaching_material_generation: 770，error_correction: 750，question_generation: 660，automatic_grading: 628，psychological_support: 549，personalized_learning_support: 542，problem_solving: 444，personalized_content_creation: 330。按生成模型分布为：deepseek-r1: 1119，qwen-max: 1110，qwen2.5-7b-instruct: 1108，deepseek-v3: 1100，qwen2.5-14b-instruct: 1099。

数据设计的关键特点是：同一问题会被多个生成模型回答，并在多个任务相关维度上由多位自动评估器与三位人类共同打分，因此非常适合分层比较“生成能力”“评估能力”和“任务/维度难度”。

## 三、已有发现整合

### 3.1 前置实验已有结论

- 前置实验的核心目标是缓解 LLM judge 打分普遍偏高、低分段稀缺以及多场景多维度适配不足的问题。
- 已有实验显示，直接使用人类标注数据训练的 Qwen3-0.6B 分类模型效果最好；只输出分类标签、不显式训练 CoT 的设置优于更复杂的生成式格式。
- 合成低分样本可以提升低分段覆盖，但混合合成数据后模型在统一的人类测试集上的准确率反而下降，说明合成分布与真实人类分布存在明显偏差。
- 按分数段看，低分样本补齐后模型会更挑剔，容易把原本 5 分样本打到 3-4 分，表现为系统性压低高分。
- 在集成方向上，stacking 方案优于单一模型，说明不同微调种子和学习率训练出的基模型之间具有互补性。
- 剪枝和超参搜索能缩小成本与性能差距，但仍未稳定超过最佳的轻量分类模型。

### 3.2 前置实验对当前分析的启示

- 后续分析不能只报告整体准确率，需要同时报告分数段准确率、各 metric 准确率、无效样本率和校准偏差。
- 要将“生成模型能力分析”和“评估模型能力分析”区分开：前者以人类均分为参照，后者以人类一致性为上界。
- 需要专门分析低分合成数据对判别边界的影响，尤其关注 4/5 分和 2/3 分交界处的偏移。

### 3.3 基于 results_merge.jsonl 的新发现

- 以三位人类均分为参考时，整体最强的生成模型是 `deepseek-r1`，而自动评估器中与人类最接近的是 `EduBenchEvaluator`，其整体 MAE 为 0.4453。
- 任务难度与评估难度并不一致，但 `automatic_grading` 与 `problem_solving` 同时表现出“生成更难、评估也更难”的双高难特征。
- 从维度上看，事实准确性和内容相关性类指标得分更高、判别更稳；推理严谨性、高阶思维促进、激励反馈等维度更难，也更容易让自动评估器与人类产生偏差。
- 大多数自动评估器相对于人类存在系统性高估，说明后续实验必须同时报告校准误差，不能只比较相关性或准确率。
- 语言因素不可忽略：不同任务在中英文上存在显著方向不一致的差异，说明“任务 × 语言 × 评估器”之间可能存在交互效应。

## 四、定量分析结果摘要

### 4.1 自动评估器整体表现

| evaluator | n | mean_score | std_score | mae_to_human_mean | signed_bias_vs_human_mean | exact_match_rate |
| --- | --- | --- | --- | --- | --- | --- |
| EduBenchEvaluator | 5536 | 4.6033 | 0.6297 | 0.4453 | 0.2872 | 0.7056 |
| deepseek-r1 | 5536 | 4.5795 | 0.7950 | 0.6046 | 0.2633 | 0.5695 |
| deepseek-v3 | 5528 | 4.6664 | 0.7607 | 0.6236 | 0.3495 | 0.5803 |
| gpt-4o | 5397 | 4.7569 | 0.5295 | 0.5884 | 0.4313 | 0.5709 |
| qwq-plus | 5446 | 4.6614 | 0.7297 | 0.6049 | 0.3391 | 0.5859 |

### 4.2 生成模型整体表现（以人类均分为准）

| model | n | human_mean_score | human_score_std | high_score_rate_human_mean_ge_4_5 |
| --- | --- | --- | --- | --- |
| deepseek-r1 | 1119 | 4.6408 | 0.7128 | 0.8284 |
| deepseek-v3 | 1100 | 4.2688 | 0.7781 | 0.4664 |
| qwen-max | 1110 | 4.3946 | 0.7102 | 0.5649 |
| qwen2.5-14b-instruct | 1099 | 4.1313 | 0.7438 | 0.3667 |
| qwen2.5-7b-instruct | 1108 | 4.1402 | 0.8300 | 0.4125 |

### 4.3 任务层发现

从任务维度看，`automatic_grading` 和 `problem_solving` 的人类均分最低，同时也是自动评估误差最高的两个任务。这说明一旦任务同时要求正确性判断、推理检查、结构化输出以及反馈质量，自动 judge 的稳定性会明显下降。

### 4.4 维度层发现

在 metric 层面，推理、高阶思维和激励反馈相关指标最难评，且对自动评估器的区分度最大；基础事实准确性、内容相关性、角色口吻一致性等指标更稳定。

### 4.5 同系偏袒与校准现象

在同系偏袒分析中，我们重点检查了 `deepseek-r1` judge 是否对 `deepseek-r1` 生成回答更宽松，以及 `deepseek-v3` judge 是否对 `deepseek-v3` 回答更宽松。该分析以“相对人类均分的 signed bias”作为核心指标。如果 own-model 组 bias 明显高于 other-model 组，则可视为存在潜在偏袒。

同时，我们按照人类均分分箱计算 calibration curve，比较每个自动评估器在低分、中分和高分段的平均预测分与人类均分之间的差值。这个分析能直接回答“自动评估器到底是高估所有样本，还是只高估高分段/低分段”。

## 五、后续分析方案

### 5.1 指标定义

后续实验建议固定使用以下指标体系。对于生成模型能力，以三位人类均分作为主参考，报告总体均分、按任务均分、按 metric 均分、分数段分布、高分率以及 question-level 难度。对于自动评估器能力，至少报告 MAE、signed bias、exact match rate、按任务/按维度 MAE、分数段 calibration gap，以及与人类内部一致性的相对差距。对于训练实验，则额外报告 accuracy、macro-F1、各分数段准确率、无效输出率和格式错误率。

### 5.2 图表设计

建议图表包括：生成模型总体表现条形图；任务 × 生成模型热力图；任务 × 自动评估器 MAE 热力图；metric × 自动评估器 MAE 热力图；自动评估器 calibration 曲线；分数段混淆矩阵；中英文对比条形图；同系偏袒对比图；最难问题与最易问题样本展示表；以及前置训练实验中的分数段准确率折线图。

### 5.3 论文写法建议

论文叙述上建议先明确区分“answer model evaluation”和“judge model evaluation”。第一部分介绍数据集任务设计与 rubric 特征，强调这是多任务、多维度、多语言教育场景。第二部分报告生成模型表现，指出哪些任务最能区分模型水平。第三部分报告评估器表现，重点强调小型专用分类模型在该数据上的一致性优势，以及自动评估器普遍存在高估倾向。第四部分回扣前置实验，说明低分数据增强虽然改善类别覆盖，但会改变判别边界并带来高分压低问题。第五部分讨论限制，包括人类均分并非绝对真值、当前分析尚未进行显著性检验、语言与学科因素可能存在交互。

### 5.4 实验顺序建议

实验顺序建议如下：先完成描述性统计与主结果复现；随后做任务层和 metric 层拆解；再进行同系偏袒分析与校准分析；然后回到训练实验，比较人类数据、混合数据、均匀采样数据在不同分数段的收益与副作用；最后做模型集成、剪枝与超参搜索的补充实验。若论文篇幅允许，再加入 bootstrap 置信区间和显著性检验。

## 六、重点样本观察

最难问题多集中在 automatic grading、error correction 和高教育阶段的问题求解任务；最容易问题多出现在心理支持、简单判断型自动评分以及结构清晰的个性化支持任务中。这说明任务名称之外，题目内部仍有显著难度梯度，后续适合引入基于 question 的难度标签。

### 6.1 最难问题样本（按人类均分排序）

| rank | task | avg_human_mean | n | question_preview |
| --- | --- | --- | --- | --- |
| 1 | error_correction | 2.2571 | 35 | Question: Which of the following is a primary role of a marketing manager in an organization? Original Answer: Managing the financial accounts of the organization. You are providing error-correction services for the student's response. Base |
| 2 | automatic_grading | 3.2143 | 28 | 问题：在神经生理学中，动作电位的过程中不包括以下哪一个步骤？ A) 去极化 B) 再极化 C) 超极化 D) 钙离子流入细胞 学生的答案：C) 超极化 请根据问题和学生答案给出"评分":"评分细节":"个性化反馈":,以json格式返回 |
| 3 | problem_solving | 3.2167 | 20 | Subject:History Education Level:PhD Question:Which of the following historians is best known for pioneering the Annales School of historical writing, which emphasized long-term social history?  A) Marc Bloch  B) E. H. Carr  C) Leopold von R |
| 4 | problem_solving | 3.4667 | 20 | Subject:Mathematics Education Level:PhD Question:In the context of complex analysis, consider the function f(z) = z^2 + 1. Which of the following statements is true regarding its singularities? A) f(z) has no singularities. B) f(z) has a re |
| 5 | automatic_grading | 3.5222 | 30 | 问题：选择以下具有微分同胚性质的函数类别：（可多选） A. 二次多项式函数 B. 余弦函数 C. 指数函数 D. 常数函数 E. 三次多项式函数 学生的答案：['C', 'E'] 请根据问题和学生答案给出"评分":"评分细节":"个性化反馈":,以json格式返回 |
| 6 | idea_provision | 3.5917 | 40 | Question: Explain how Porter's Five Forces framework can be used to analyze the competitive environment of an industry.  Please provide reasoning based on this question. Do not provide the answer directly.. "Reasoning Provided":, return in  |
| 7 | automatic_grading | 3.6212 | 22 | 问题：解释为什么基因编辑技术可以用于提高作物抗病能力，并举例说明一个成功的应用案例。 学生的答案：基因编辑技术通过精确修改作物的基因组，可以提高抗病能力。CRISPR-Cas9是一种常用的基因编辑工具，通过识别和切割特定的DNA序列，使科研人员能够插入、删除或替换疾病相关的基因，从而增强植物的免疫反应。一个成功的应用案例是基因编辑改善水稻对稻瘟病的抵抗力，这是一种由真菌引起的毁灭性疾病。科学家利用CRISPR-Cas9编辑OsSWEET13基因，从而阻止病原体破坏水稻细胞的糖 |
| 8 | problem_solving | 3.6833 | 20 | 学科:法学 学制级别:博士 问题：在国际法中，以下哪一个原则主要用于解决国家之间的领土争端？ A. 不干涉内政原则 B. 自决原则 C. 先占原则 D. 互惠原则 .请根据问题生成对应的答案。"答案":,以json格式返回 |
| 9 | problem_solving | 3.7167 | 20 | 学科:地理 学制级别:初中 问题：以下哪些国家位于非洲？ A. 埃及 B. 巴西 C. 尼日利亚 D. 日本 E. 南非 .请根据问题生成对应的答案。"答案":,以json格式返回 |
| 10 | automatic_grading | 3.7333 | 30 | Question: Explain the significance of the Mid-Autumn Festival in Chinese culture. Student's Answer: The Mid-Autumn Festival is an important holiday in China. It is also called the Moon Festival and is celebrated on the 15th day of the 8th m |

### 6.2 最易问题样本（按人类均分排序）

| rank | task | avg_human_mean | n | question_preview |
| --- | --- | --- | --- | --- |
| 1 | problem_solving | 4.9333 | 20 | Subject:Theoretical Economics Education Level:Undergraduate Question:What is the Nash Equilibrium in a game theory context, and how can it be identified in a simple two-player game? . Please generate the corresponding answer based on the qu |
| 2 | psychological_support | 4.9067 | 25 | Anxiety Level: Moderate Anxiety Dialogue with Student: ["Student: Hi, I'm feeling quite overwhelmed with my PhD in Automation.", "Agent: I'm sorry to hear that. Can you tell me more about what's causing you to feel overwhelmed?", "Student:  |
| 3 | psychological_support | 4.8933 | 25 | Anxiety Level: Mild Anxiety Dialogue with Student: ["Agent: Hi there! How's your day going?", "Student: It's okay, I guess. I'm just feeling a little worried about my Chemistry homework.", "Agent: I'm sorry to hear that. What is it about th |
| 4 | psychological_support | 4.8800 | 25 | Anxiety Level: Mild Anxiety Dialogue with Student: Agent: Hi there! How's your Chinese study going today? Student: Hi... It's going okay, I guess. Agent: Just okay? Is there something that's bothering you? Student: Well, I'm feeling a bit a |
| 5 | psychological_support | 4.8533 | 25 | Anxiety Level: Mild Anxiety Dialogue with Student: [{'Agent': 'Hi there! How are you feeling today?'}, {'Student': "Hey, I'm feeling a bit anxious, honestly. There's just so much to keep up with in my Clinical Medicine program."}, {'Agent': |
| 6 | automatic_grading | 4.8333 | 30 | Question: True or False: The sum of the interior angles of a triangle is 180 degrees. Student's Answer: True Please provide "Score", "Scoring Details", and "Personalized Feedback" based on the question and student's answer, in JSON format. |
| 7 | idea_provision | 4.8241 | 36 | Question: Which of the following principles is central to the concept of New Public Management (NPM)?  Please provide reasoning based on this question. Do not provide the answer directly.. "Reasoning Provided":, return in JSON format |
| 8 | personalized_learning_support | 4.8133 | 25 | Student Profile: Student Profile: {'Name': 'Alex Johnson', 'Age': 20, 'Year': 'Sophomore', 'Interests': ['Behavioral Economics', 'Game Theory', 'Microeconomics'], 'Strengths': ['Analytical thinking', 'Mathematical modeling'], 'Areas for Imp |
| 9 | idea_provision | 4.7917 | 40 | 问题：以下哪句话使用了正确的时态来描述过去的习惯行为？ A) I am reading books every night when I was a child. B) I used to read books every night when I was a child. C) I have read books every night when I was a child. D) I was read books every night when I was a chil |
| 10 | personalized_content_creation | 4.7556 | 15 | {'Name': 'Alex Johnson', 'Age': 19, 'Current Education Level': 'Undergraduate, Year 1', 'Current Skill Level': 'Introductory Physics', 'Learning Goals': 'To gain a comprehensive understanding of classical mechanics and prepare for advanced  |

## 七、产物说明

本次分析同步输出了多份 CSV 表格与一个 Python 脚本。脚本路径为 `/Users/liangxinyue/Downloads/edubench/edubench_deep_analysis.py`，结果目录为 `/Users/liangxinyue/Downloads/edubench/analysis_outputs/`。其中包括 evaluator_summary、task_evaluator_table、metric_evaluator_table、task_model_table、evaluator_generator_affinity、calibration_curve、language_task_table 等文件，可直接用于后续论文制图或进一步统计。
