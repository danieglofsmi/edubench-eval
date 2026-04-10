# 小模型 / 决策树用于文本分类与打分评价任务：论文整理

> 整理时间：2026-04-10
> 覆盖论文：5 篇（不含综述）

---

## 1. Representation-as-a-Judge with Small Language Models via Semantic Capacity Asymmetry

**论文信息**
- arXiv: [2601.22588](https://arxiv.org/abs/2601.22588)
- 发表：ICLR 2026
- 作者：Zhuochun Li, Yong Zhang, Ming Li 等（Ping An Technology / University of Pittsburgh / UMD）
- 代码：https://github.com/zhuochunli/Representation-as-a-judge

### 训练任务

用小语言模型（SLM）的**内部隐层表示**来预测文本质量的多维评分，替代大模型（LLM-as-a-Judge）的生成式评判。评估维度包括：语义一致性（Semantic Consistency）、逻辑性（Logicality）、信息量（Informativeness）、流畅性（Fluency）、事实性（Factuality），每个维度打 1–5 分。任务形式为多分类（5 类）和二分类（高/低质量）。

### 数据形式

1. **响应数据集构建**：用中等规模模型（Llama-3-8B-Instruct）对推理基准（GSM8K、MATH、GPQA）的问题生成回答，构成 (问题, 回答) 对。
2. **标注数据集构建**：用强大 LLM（DeepSeek-V3）对每个 (问题, 回答) 对按 5 个维度打分（1–5），得到 probing 数据集 $D_\text{prob}$。
3. **数据平衡**：对每个维度按最少类别数量下采样，保证各分数等级样本均衡（每个分数等级通常不超过 100 条）。

### 模型训练方法

框架名为 **INSPECTOR**，分三步：

1. **LLM 标注**：用强 LLM 对 (问题, 回答) 对按各维度打分，生成标注数据。
2. **小模型 Probing**：将评估 prompt 输入冻结的小模型（Qwen3-0.6B / 1.7B、Llama-3.2-1B / 3.1-8B），提取各层隐状态，计算 mean/last/min/max/concat 等多种池化特征，并附加注意力熵统计量，再用 PCA 降维至 50 维。
3. **分类器训练**：在提取的特征上训练轻量分类器（逻辑回归、随机森林、小 MLP、线性 SVM），通过分层交叉验证选出最优层-池化-分类器组合，最终组合多层特征构建最终 probing 分类器。

整个过程中小模型参数**完全冻结**，只训练分类器头。

### 实验结论

- **Probing 远优于 Prompt**：在 GSM8K、MATH、GPQA 上，probing 方法的加权平均 F1 比直接 prompt 小模型高出 20% 以上。
- **二分类可靠性高**：二分类（高/低质量）F1 达 80–90%，可作为可靠的数据过滤器；多分类 F1 约 50–60%（受限于小模型与大模型的能力差距）。
- **模型大小非决定因素**：Qwen3-1.7B 在某些任务上优于 Llama-3.1-8B，说明更大的小模型不一定更好。
- **数据过滤有效**：用 probing 分类器过滤 SFT 训练数据，下游模型性能与用 DeepSeek-V3 过滤相当，均显著优于随机过滤。
- **最优配置**：mean pooling + 逻辑回归分类器表现最稳定。

### 数据示例

**输入**（评估 prompt，送入冻结的小模型）：

```
[Question]
If a train travels at 60 mph for 2.5 hours, how far does it travel?

[Response]
To find the distance, I multiply speed by time: 60 × 2.5 = 150 miles.
Therefore, the train travels 150 miles.
```

**中间产物**（从小模型第 16 层提取 mean pooling 隐状态，PCA 降至 50 维）：

```
[0.032, -0.118, 0.274, 0.051, -0.203, ..., 0.089]  # shape: (50,)
```

**输出**（逻辑回归分类器对各维度的预测分数）：

```json
{
  "Semantic Consistency": 5,
  "Logicality": 5,
  "Informativeness": 4,
  "Fluency": 5,
  "Factuality": 5,
  "binary_label": "high"
}
```

---

## 2. QuRating: Selecting High-Quality Data for Training Language Models

**论文信息**
- arXiv: [2402.09739](https://arxiv.org/abs/2402.09739)
- 发表：ICML 2024
- 作者：Alexander Wettig, Aatmik Gupta, Saumya Malik, Danqi Chen（Princeton NLP）
- 代码 & 数据：https://github.com/princeton-nlp/QuRating

### 训练任务

训练一个 **QuRater 模型**，从文本对的成对偏好判断中学习标量质量评分，用于大规模预训练语料的质量打分与数据筛选。评估四个质量维度：写作风格（Writing Style）、事实与趣闻（Facts & Trivia）、教育价值（Educational Value）、所需专业知识（Required Expertise）。

### 数据形式

1. **成对判断数据**：从 SlimPajama 语料中采样 50 万篇文档，构成 25 万对文本对（每对截取至多 512 个 token），用 GPT-3.5-turbo-0613 对每个质量维度进行成对比较，正反顺序各问一次以消除位置偏差，得到置信度 $p_{B \succ A} \in [0,1]$。
2. **训练集构成**：20 万对跨领域随机采样 + 每个专业领域（Wikipedia、Book、StackExchange、Github、ArXiv）各 1 万对，共 25 万对。
3. **标注语料**：用训练好的 QuRater 对 260B token 的 SlimPajama 子集（QuRatedPajama）打分，每篇文档按 4 个维度各得一个标量分。

### 模型训练方法

- **基础模型**：Sheared-Llama-1.3B（参数量 13 亿）。
- **训练目标**：Bradley-Terry 模型，用二元交叉熵损失拟合成对偏好概率：
  $$\mathcal{L}_\theta = \mathbb{E}[-p_{B \succ A} \log \sigma(s_\theta(t_B) - s_\theta(t_A)) - (1-p_{B \succ A}) \log \sigma(s_\theta(t_A) - s_\theta(t_B))]$$
- **多任务设置**：为 4 个质量维度设置独立的回归头，一次前向传播输出 4 个分数。
- **数据选择**：用温度采样 $p(d_i) \propto \exp(s_i / \tau)$ 从 260B token 中采样 30B token 训练 1.3B 参数的语言模型，$\tau=2.0$ 时效果最佳（平衡质量与多样性）。

### 实验结论

- **温度采样优于 top-k 选择**：直接选最高分文档（top-k）反而比均匀采样差，因为多样性损失过大；$\tau=2.0$ 的温度采样效果最好。
- **教育价值维度最有效**：按教育价值采样的模型在 10 个 ICL 任务上平均提升 1.8%（vs. 均匀采样）；事实与趣闻维度提升 1.3%。
- **写作风格降低困惑度但不提升下游任务**：按写作风格选出的数据困惑度最低，但 ICL 性能提升不显著。
- **课程学习有效**：按所需专业知识从低到高排序训练（课程学习），比随机顺序训练性能更好。
- **QuRater 准确率高**：在保留判断集上准确率超过 93%。

### 数据示例

**输入**（GPT-3.5 成对比较 prompt，用于生成训练标注）：

```
Text A:
The mitochondria is the powerhouse of the cell. It produces ATP through
oxidative phosphorylation, converting nutrients into usable energy...

Text B:
lol so i was like whatever and then she said omg no way and i was like
yeah way and we just laughed about it for like an hour haha

Which text has higher Educational Value? Respond with A or B and a
confidence score between 0.5 and 1.0.
```

**标注结果**（GPT-3.5 输出，转换为训练信号）：

```
A, confidence: 0.97
→ p(A ≻ B) = 0.97
```

**模型输入**（QuRater，截取至 512 tokens 的文档文本）：

```
The mitochondria is the powerhouse of the cell. It produces ATP through
oxidative phosphorylation, converting nutrients into usable energy...
```

**模型输出**（4 个维度的标量评分，由独立回归头输出）：

```json
{
  "writing_style": 3.82,
  "facts_and_trivia": 4.51,
  "educational_value": 4.73,
  "required_expertise": 2.14
}
```

---

## 3. The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale（FineWeb-Edu 分类器部分）

**论文信息**
- arXiv: [2406.17557](https://arxiv.org/abs/2406.17557)
- 发表：NeurIPS 2024 Datasets & Benchmarks Track
- 作者：Guilherme Penedo, Hynek Kydlíček 等（Hugging Face）
- 数据集：https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu

### 训练任务

训练一个**教育质量分类器**，对网页文本按教育价值打 0–5 分（整数），用于从 15T token 的 FineWeb 数据集中筛选出高质量教育内容（FineWeb-Edu，1.3T token）。

### 数据形式

1. **LLM 标注**：用 Llama-3-70B-Instruct 对从 FineWeb 中采样的 46 万条文档进行教育质量评分（0–5 分），采用加法量表（additive scale）——模型逐条评估各子标准后累加得分，而非直接给出固定分类。Prompt 要求模型聚焦于小学和初中水平的知识，避免偏向 arXiv 等高度技术性内容。
2. **训练集/验证集划分**：41 万条用于训练，5 万条用于验证。

### 模型训练方法

- **嵌入模型**：Snowflake-arctic-embed-m（编码器模型，参数量约 110M）。
- **分类器结构**：在冻结的嵌入模型之上训练一个**线性回归头**（Linear Regression），输出连续分数后四舍五入为 0–5 的整数。
- **训练设置**：学习率 3e-4，训练 20 个 epoch，选验证集 F1 最高的 checkpoint。
- **过滤阈值**：选择分数 ≥ 3 的文档纳入 FineWeb-Edu，该阈值在知识/推理密集型基准与其他基准之间取得最佳平衡，验证集 F1 达 82%。
- **推理规模**：对 15T token 的 FineWeb 全量打分，消耗约 6,000 H100 GPU 小时。

### 实验结论

- **FineWeb-Edu 大幅优于其他开放数据集**：在 MMLU、ARC、OpenBookQA 等知识/推理密集型基准上，FineWeb-Edu 训练的模型显著优于所有其他开放网络数据集。
- **MMLU 提升显著**：相比 FineWeb，MMLU 分数从 33% 提升至 37%（相对提升约 12%）；ARC 从 46% 提升至 57%（相对提升约 24%）。
- **数据效率极高**：FineWeb-Edu 仅需约 38B token 即可在 MMLU 上达到 33.6% 的准确率，而次优数据集 Matrix 需要约 300B token 才能达到相同水平（约 8× 数据效率提升）。
- **线性分类器足够有效**：简单的线性回归头在冻结嵌入上即可达到 82% 的 F1，证明轻量分类器对此类打分任务的有效性。

### 数据示例

**输入**（网页文本，送入冻结的 Snowflake-arctic-embed-m 编码器）：

```
Photosynthesis is the process by which green plants convert sunlight into
food. Using chlorophyll in their leaves, plants absorb carbon dioxide from
the air and water from the soil. With energy from sunlight, they produce
glucose and release oxygen as a byproduct. This process is fundamental to
life on Earth, as it forms the base of most food chains.
```

**中间产物**（编码器输出的文本嵌入向量，维度 768）：

```
[0.041, 0.183, -0.072, ..., 0.215]  # shape: (768,)
```

**输出**（线性回归头输出连续值，四舍五入为整数分）：

```
连续输出: 3.74  →  最终评分: 4（教育价值高，纳入 FineWeb-Edu）
```

---

## 4. propella-1: Multi-Property Document Annotation for LLM Data Curation at Scale

**论文信息**
- arXiv: [2602.12414](https://arxiv.org/abs/2602.12414)
- 发表：2025（预印本）
- 作者：Maximilian Idahl, Benedikt Droste, Björn Plüster, Jan Philipp Harries（ellamind / Leibniz University Hannover）
- 模型 & 数据：Hugging Face Hub（CC-BY-4.0 许可）

### 训练任务

训练一系列小型多语言 LLM，对文本文档在 **18 个属性**上进行结构化分类标注，输出 JSON 格式的多维度注释。18 个属性分为 6 大类：

| 类别 | 属性（示例） |
|------|-------------|
| 核心内容 | 内容完整性、内容比例、内容长度 |
| 分类 | 一句话描述、内容类型（18 类）、行业领域（37 类）、技术内容类型（7 类） |
| 质量与价值 | 内容质量、信息密度、教育价值、推理深度 |
| 受众与目的 | 受众层次、商业偏向、时效性 |
| 安全 | 内容安全、PII 存在性 |
| 地理 | 地区相关性、国家相关性 |

### 数据形式

1. **标注数据生成**：用多个前沿 LLM（含 Gemini 系列等）按完整标注 rubric（约 8,000 词）对多样化文档进行标注，生成训练数据。
2. **语言覆盖**：57 种语言，约 35% 英语，其余涵盖欧洲语言、阿拉伯语、中文、日语、韩语、泰语等。
3. **文档来源**：网络爬取、PDF、精选数据集，覆盖代码、数学内容、对话等多种内容类型。
4. **评估集**：3,000 篇文档，以 Gemini-3-Pro（高推理模式）的标注作为参考标签。

### 模型训练方法

- **基础架构**：Qwen-3 解码器架构，三个规模：0.6B、1.7B、4B 参数。选择解码器模型的原因：(1) 原生支持长文档（最长 64K context）；(2) 一次前向传播输出所有 18 个属性的 JSON；(3) 通过微调内化详细标注指南。
- **训练设置**：fp8 混合精度，4× H100 GPU，每个模型变体训练仅需数小时；上下文长度 64K；输出格式为无空格的紧凑 JSON，减少输出 token 数。
- **推理 Prompt**：使用约 800 token 的紧凑系统 prompt（列出所有属性及枚举值），远短于训练时使用的完整 rubric（约 14K token）。
- **推理基础设施**：SGLang + llguidance 结构化输出后端，强制 JSON schema 合规，4B fp8 模型在单张 H100 上处理速度约 27 文档/秒（约 10.3 GPU 小时/百万文档）。

### 实验结论

- **4B 模型超越更大的通用模型**：propella-1-4b 整体得分 0.779，超过 Gemini-3-Flash 及所有开源基线（尽管参数量远小于后者）。
- **0.6B 模型也表现强劲**：0.6B 模型整体得分 0.729，证明小型专用模型可接近大型通用模型的标注质量。
- **fp8 推理无损**：fp8 精度推理与 bf16 相比标注质量差异可忽略不计。
- **多维度分析揭示单一分数无法捕捉的差异**：以德语数据为例，FinePDFs 中"优秀质量"内容占比 21.4%，而 FineWeb-2 仅 2.4%；FinePDFs 中含分析推理的内容约为 FineWeb-2 的 12 倍。
- **大规模标注验证**：在 3,936 张 A100 GPU 上，约 3.5 小时内完成 FineWeb-2 中约 5 亿篇文档的标注。

### 数据示例

**输入**（系统 prompt 约 800 tokens，此处仅展示文档部分）：

```
<document>
Python is a high-level, interpreted programming language known for its
clear syntax and readability. It supports multiple programming paradigms,
including procedural, object-oriented, and functional programming.
Python's extensive standard library and active community make it one of
the most popular languages for data science, web development, and
automation tasks.
</document>
```

**输出**（propella-1-4b 生成的紧凑 JSON，18 个属性一次输出）：

```json
{
  "completeness":"complete",
  "content_ratio":"high",
  "length":"medium",
  "one_liner":"Introduction to Python programming language and its use cases",
  "content_type":"educational",
  "domain":"technology",
  "technical_content_type":"tutorial",
  "quality":"good",
  "information_density":"high",
  "educational_value":"high",
  "reasoning_depth":"low",
  "audience":"general",
  "commercial_bias":"none",
  "timeliness":"evergreen",
  "safety":"safe",
  "pii":"none",
  "geographic_relevance":"global",
  "country_relevance":"none"
}
```

---

## 5. RDBE: Reasoning Distillation-Based Evaluation Enhances Automatic Essay Scoring

**论文信息**
- arXiv: [2407.13781](https://arxiv.org/abs/2407.13781)
- 发表：2024（预印本）
- 作者：Ali Ghiasvand Mohammadkhani（Shahid Soltani High School, Iran）
- 代码：https://github.com/AliGhiasvand86/RDBE

### 训练任务

自动作文评分（Automated Essay Scoring, AES）：给定作文题目、作文正文和评分 rubric，输出该 rubric 下的评分（从 [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0] 中选取），同时生成可解释的评分理由。评分维度包括：内容（Content）、组织（Organization）、语言（Language）及总分（Total）。

### 数据形式

1. **基础数据集**：DREsSNew 数据集，共 1,980 条有效数据点，每条包含作文题目、作文正文、三个维度的人工评分。按 60%/20%/20% 划分训练/验证/测试集。
2. **合成推理数据生成**：用 Llama-3-70B（通过 Groq API 调用，temperature=0）对每条训练数据的每个评分维度生成推理解释，系统 prompt 要求模型分析作文在该 rubric 下的优缺点并给出解释。
3. **最终训练数据格式**：输入为 `[Scoring Rubric] + [Subject] + [Essay]`，输出为 `{LLM 生成的推理解释} --> {分数}`，即先推理后给分。

### 模型训练方法

- **骨干模型**：LongT5-Base（约 2.2 亿参数），采用 transient-global attention，支持更长输入序列，来自 HuggingFace transformers 库。
- **训练目标**：序列到序列生成，用交叉熵损失（cross-entropy loss）训练模型先生成推理文本再输出分数。
- **训练设置**：AdamW 优化器，batch size=8，训练 15 个 epoch。
- **核心思路**：推理蒸馏（Reasoning Distillation）——用大模型（Llama-3-70B）生成的推理链作为监督信号，训练小模型（LongT5-Base）模仿推理过程，从而提升打分能力和可解释性。

### 实验结论

- **RDBE 达到数据集 SOTA**：在 DREsSNew 测试集上，RDBE 在所有评分维度均优于两个基线：
  - Content QWK：0.606（vs. ArTS 0.516，vs. Llama-3-70B zero-shot 0.167）
  - Organization QWK：0.629（vs. ArTS 0.508，vs. Llama-3-70B 0.108）
  - Language QWK：0.638（vs. ArTS 0.535，vs. Llama-3-70B 0.090）
  - Total QWK：0.730（vs. ArTS 0.559，vs. Llama-3-70B 0.119）
- **小模型大幅超越大模型 zero-shot**：LongT5-Base（2.2 亿参数）在所有维度上均远超 Llama-3-70B 的零样本表现，后者参数量是前者的约 318 倍。
- **推理蒸馏提升可解释性**：模型不仅输出分数，还能生成对应的评分理由，具有实际教育应用价值。
- **局限性**：受预算限制，合成数据由 Llama-3-70B 而非 GPT-4 生成，数据质量有提升空间。

### 数据示例

**输入**（拼接 Scoring Rubric + Subject + Essay，送入 LongT5-Base）：

```
[Scoring Rubric]
Content (1-5): Does the essay address the prompt with relevant ideas and
supporting details? 1=off-topic, 5=fully developed with strong evidence.

[Subject]
Describe a challenge you have overcome and what you learned from it.

[Essay]
Last year, I struggled with public speaking. Every time I had to present
in class, my hands would shake and my mind would go blank. I decided to
join the school debate club to face my fear directly. At first, I lost
every round, but I kept practicing. By the end of the semester, I won
second place in the regional competition. I learned that growth requires
discomfort, and that consistent effort matters more than natural talent.
```

**输出**（LongT5-Base 先生成推理链，再输出分数）：

```
The essay directly addresses the prompt by describing a specific challenge
(public speaking anxiety) with concrete details (debate club, regional
competition). The narrative arc is clear and the lesson learned is
explicitly stated and well-supported by the described experience. The
writer demonstrates personal growth with measurable evidence. However,
the supporting details could be further elaborated with more specific
examples of practice methods.
--> Content: 4.0
```

---

## 6. When XGBoost Outperforms GPT-4 on Text Classification: A Case Study

**论文信息**
- 发表：ACL/NAACL 2024 Workshop（TrustNLP 2024），页码 51–60
- 作者：Matyas Bohacek, Michal Bravansky
- 代码：https://github.com/maty-bohacek/xgboost-vs-gpt4

### 训练任务

新闻可信度分类（News Trustworthiness Classification）：对新闻文章进行二分类或多分类，判断其可信度等级。对比传统机器学习流水线（XGBoost + TF-IDF 特征）与大模型流水线（GPT-4、LLaMA 2）在该任务上的性能、训练成本和部署需求。

### 数据形式

使用新闻可信度标注数据集，包含新闻文章文本及对应的可信度标签。传统流水线使用 TF-IDF 特征向量化文本；LLM 流水线使用零样本或少样本 prompt 直接分类。

### 模型训练方法

- **传统流水线（XGBoost）**：TF-IDF 特征提取 → XGBoost 梯度提升决策树分类器，需要标注训练数据进行有监督训练。
- **LLM 流水线（GPT-4 / LLaMA 2）**：零样本或少样本 prompt，无需训练数据，直接调用 API 或本地推理。
- 对比维度：分类性能、训练数据需求、参数量、部署成本。

### 实验结论

- **XGBoost 流水线在性能上优于 GPT-4 和 LLaMA 2**：在新闻可信度分类任务上，传统 TF-IDF + XGBoost 流水线的分类准确率超过两个 LLM 流水线。
- **参数量差距悬殊**：XGBoost 模型参数量比 GPT-4 小数个数量级，但性能更优。
- **任务特异性是关键**：当任务有充足的标注训练数据时，针对特定任务训练的传统分类器可以超越通用大模型的零/少样本能力。
- **部署成本优势明显**：传统流水线无需 GPU 推理，部署成本极低，适合资源受限场景。
- **结论的适用范围**：该结论针对特定任务（新闻可信度分类）和特定数据规模，不代表传统方法在所有文本分类任务上均优于 LLM。

### 数据示例

**输入**（新闻文章文本，经 TF-IDF 向量化后送入 XGBoost）：

```
Scientists at MIT have developed a new battery technology that could
charge electric vehicles in under five minutes. The breakthrough uses
a novel anode material that dramatically increases ion transfer speed.
The research, published in Nature Energy, was funded by the Department
of Energy and has been independently replicated by two other labs.
```

**TF-IDF 特征**（稀疏向量，词汇表大小约 50,000，此处仅展示非零项示例）：

```
{"scientists": 0.31, "MIT": 0.48, "published": 0.27,
 "Nature Energy": 0.52, "independently replicated": 0.61,
 "Department of Energy": 0.44, ...}
```

**输出**（XGBoost 分类器预测可信度等级）：

```
预测类别: trustworthy（可信）
置信概率: {"trustworthy": 0.83, "uncertain": 0.12, "untrustworthy": 0.05}
```

---

## 横向对比

| 论文 | 模型类型 | 打分/分类任务 | 训练数据来源 | 核心方法 |
|------|---------|-------------|------------|---------|
| Representation-as-a-Judge | 小 LLM（0.6B–8B）+ 线性分类器 | 推理质量多维评分（1–5 分） | 大 LLM（DeepSeek-V3）标注 | Probing 隐层表示 |
| QuRating | 小 LLM（1.3B）回归头 | 文本质量标量评分（4 维度） | GPT-3.5 成对偏好判断 | Bradley-Terry 模型 + 温度采样 |
| FineWeb-Edu | 线性回归头（冻结编码器） | 教育价值评分（0–5 分） | Llama-3-70B 标注 | 线性回归 + 阈值过滤 |
| propella-1 | 小 LLM（0.6B–4B）生成 JSON | 18 维度结构化分类标注 | 多个前沿 LLM 标注 | 指令微调 + 结构化输出 |
| RDBE | 小 LLM（LongT5-Base，220M） | 作文评分（1–5 分，多维度） | Llama-3-70B 生成推理链 | 推理蒸馏 + seq2seq 微调 |
| XGBoost vs GPT-4 | XGBoost + TF-IDF | 新闻可信度分类 | 人工标注 | 梯度提升决策树 |
