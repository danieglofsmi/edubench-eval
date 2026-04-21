# EduBench 数据分析报告

## ai的回答
结合数据本身可以先得到一个比较清晰的分析框架：这份数据其实天然适合分成三条主线来做，分别是“生成模型能力差异”“评估模型能力差异”“任务与维度特性差异”，而后续你关心的“不同评估方法的差异”可以作为第四条主线展开。

建立一个分层分析框架。
第一层是样本结构层，也就是先搞清楚任务、题目、维度、语言、模型、评估器各自的分布是否平衡。
第二层是生成质量层，把三位人类评审的均值当成当前最稳妥的近似参照，用它来比较不同“answer model”的水平差异。
第三层是自动评估能力层，把每个自动评估器相对于人类均值的偏差、绝对误差、分档一致率作为核心指标，观察谁更接近人。
第四层是任务机制层，分析哪些任务和哪些维度更容易让生成模型拉开差距，哪些更容易让自动评估器“看不准”。
如果后面要做论文级别结果，我建议再加入第五层，即“层次化建模”，例如以 task、metric、language、generator model 为固定效应，以 question 为随机效应，做 mixed-effects 或至少做分组 bootstrap，这样结论会更稳。

这份数据的整体结构比较完整。总共有 5536 条记录，包含 9 个任务，分别是 automatic_grading、error_correction、idea_provision、personalized_content_creation、personalized_learning_support、problem_solving、psychological_support、question_generation、teaching_material_generation。生成模型一共 5 个，分别是 deepseek-r1、deepseek-v3、qwen-max、qwen2.5-14b-instruct、qwen2.5-7b-instruct。评估器里除了三位人类，还有 EduBenchEvaluator、deepseek-r1、deepseek-v3、gpt-4o、qwq-plus 四类 LLM judge 和一个小模型 judge。总体看，数据规模不算巨量，但已经足够做比较系统的误差分析。

从任务分布看，数据并不是完全均衡的。idea_provision 最多，有 863 条，teaching_material_generation 770 条，error_correction 750 条，而 personalized_content_creation 只有 330 条。也就是说，如果你后面要比较“任务难度”，不能只看总体平均，最好报告每个任务下的样本量和置信区间，否则大任务会压过小任务。任务内部大致对应 21 到 23 个唯一题目，每个题目再被多个模型回答，并在多个维度上打分，这个设计很适合做“同题跨模型比较”。

从评估维度看，不同任务的 metric 组合不同。比如 problem_solving 更集中在 Instruction Following、Content Relevance、Basic Factual Accuracy、Reasoning Process Rigor 这类通用能力；psychological_support 则多出 Role & Tone Consistency、Motivation, Guidance & Positive Feedback、Personalization；personalized_content_creation 只覆盖 3 类核心维度；teaching_material_generation 和 question_generation 会更强调 Domain Knowledge Accuracy、Clarity、Higher-Order Thinking。这说明后面一定要避免一个常见误区：不能把不同任务上的不同 metric 简单拼成一个“统一总分”，因为它们测量的能力空间并不一样，更合适的是做 task-specific 和 metric-specific 分析，再根据论文附录定义做能力簇归并。

如果先把三位人类评分均值当成当前的“生成质量参考”，生成模型之间已经有比较明显的水平差异。整体人类均分从高到低大致是：deepseek-r1 4.6408，qwen-max 4.3946，deepseek-v3 4.2688，qwen2.5-7b-instruct 4.1402，qwen2.5-14b-instruct 4.1313。这里一个挺有意思的现象是，qwen2.5-7b-instruct 整体略高于 qwen2.5-14b-instruct，这说明这个数据集上的教育任务表现并不完全按“参数量更大就更强”的简单规律走，可能和指令风格、对中文教育场景的适配、输出稳定性有关。deepseek-r1 的领先幅度也比较明显，不是勉强领先，而是跨多个任务都能保持优势。

按任务拆开看，这种差异更明显。deepseek-r1 在 personalized_content_creation 上人类均分 4.9545，几乎接近封顶；在 personalized_learning_support 和 psychological_support 也都非常高，都是 4.85 左右，说明它在“贴近学生画像、给建议、维持支持性语气”这类任务上很强。qwen-max 在 problem_solving 上反而最好，达到 4.2197，高于 deepseek-r1 的 4.0265，这提示不同模型的强项可能分化：有的擅长“教育陪伴/个性化输出”，有的更擅长“结构化解题”。而 automatic_grading 和 problem_solving 是整体最难的两类任务，人类均值分别只有 4.0998 和 4.0578。这很重要，因为这两类任务都更强调“标准答案、推理严谨性、评分标准映射”，容错空间更小，所以更容易暴露模型上限。

如果从 metric 难度角度看，最难的确实不是事实性，而是推理和高阶能力。按人类均分排序，最低的是 推理过程严谨性 3.6794、Higher-Order Thinking & Skill Development 3.7531、Reasoning Process Rigor 3.8774，后面还有 Motivation, Guidance & Positive Feedback、个性化适应与学习支持 等主观性更强的维度。相反，Basic Factual Accuracy、Content Relevance & Scope Control、Instruction Following & Task Completion 这些维度均分更高。这个现象很符合直觉：大模型在“答对、答上、别跑题”上已经不错，但在“推理是否严谨”“是否真正促进高阶思维”“反馈是否既鼓励又有效”这类教育特有标准上，区分会更明显，也更容易出现评估分歧。

你尤其关心评估能力差异，这部分我觉得是这份数据最值得深挖的地方。若用“与人类均值的平均绝对误差 MAE”作为一个简单但有效的指标，那么整体上 EduBenchEvaluator 反而是最接近人类的，MAE 只有 0.4453，明显好于几位大模型评估器：gpt-4o 为 0.5884，deepseek-r1 为 0.6046，qwq-plus 为 0.6049，deepseek-v3 为 0.6236。若看“与四舍五入后的人类均值完全一致”的比例，EduBenchEvaluator 达到 70.56%，而其余自动评估器都在 57% 到 59% 左右。这是一个很强的信号：这个 0.6B 的分类模型虽然小，但在这个封闭标签空间、已定义 rubric 的教育评估场景下，非常可能学到了比通用 LLM judge 更稳定的判别边界。

不过这里不能直接得出“小模型比大模型评估更强”的绝对结论，因为它有可能利用了任务分布、标签模式、 rubric 表述风格等数据特征。更准确的表述应该是：在这份 EduBench 数据对应的打分任务上，EduBenchEvaluator 与人类评分更一致，且一致性优势非常明显。这意味着后续很值得重点分析它为什么更强，是因为更少的“泛化式解释”、更强的标签校准，还是因为它和数据定义之间存在更紧的分布匹配。

人类内部一致性也挺高。三位人类相对于人类均值的平均偏差分别只有 0.2678、0.2349、0.2330，而且没有样本出现“最大分差达到 2 分以上”的情况，2481 条样本三位人类完全一致。这说明你的数据的人类标注噪声并不高，自动评估器和人类之间 0.45 到 0.62 的 MAE 不是因为“人类自己也很乱”，而是真有稳定差距。这个结论对后续做评估器比较非常关键，因为它给“以人类为参照”的做法提供了更强的正当性。

从评估偏差看，几乎所有自动评估器都有“打分偏高”的倾向。相对于人类均值的平均偏差分别是：EduBenchEvaluator +0.2872，deepseek-r1 +0.2633，deepseek-v3 +0.3495，gpt-4o +0.4313，qwq-plus +0.3391。其中 gpt-4o 偏高最明显。这说明如果只看自动评估器的绝对分值，容易得出过于乐观的模型能力判断。也就是说，后面如果要比较评估方法，除了 MAE 和一致率，最好再加一个“calibration / systematic bias”维度，也就是评估器是否存在整体高估或低估。

更有意思的是，这种偏差不是各任务一致的，而是任务相关。比如在 automatic_grading 上，EduBenchEvaluator 的偏差高达 +0.7521，明显高估；而 deepseek-v3 在这个任务上甚至出现 -0.2473，表现为略低估。这提示自动评分任务可能是一个“评估器最不稳定”的区域。结合 MAE 结果也能验证：automatic_grading 上的评估误差确实非常高，EduBenchEvaluator 0.8063，gpt-4o 0.7910，deepseek-v3 甚至到 1.1828。这个任务之所以特殊，很可能是因为它混合了“答案正确性判断”“评分细则展开”“反馈质量”，既要求 judge 看懂答案对错，又要求理解评分规范，难度比单纯评价开放回答高很多。

另一个特别难评的是 problem_solving。这里 EduBenchEvaluator 的 MAE 是 0.6096，已经不低，而其余 LLM judges 都接近或超过 0.9，qwq-plus 达到 1.0098。说明只要题目涉及解题、推理、学科知识链条，自动评估器就更容易和人类分开。相对来说，psychological_support、personalized_content_creation、teaching_material_generation 这些任务上 EduBenchEvaluator 表现非常稳，MAE 分别只有 0.3097、0.3000、0.3597。这说明小模型评估器的优势很可能来自它对“结构化、风格化、rubric 明确”的教育沟通任务拟合得更好，但在需要判断深层推理质量时仍有明显困难。

如果再细到 metric 层面，这个判断更清楚。对 EduBenchEvaluator 来说，最难评的维度是 Higher-Order Thinking & Skill Development，MAE 1.0093；其次是 Motivation, Guidance & Positive Feedback 0.9836，以及 Reasoning Process Rigor 0.9371。换句话说，这个小模型虽然总体最像人，但一旦进入“教育启发性”“鼓励是否到位”“推理链是否严谨”这种高主观性或高深层推断维度，误差会迅速上升。其余大模型 judges 在 Reasoning Process Rigor 上甚至更差，普遍在 1.0 左右。这个结果很值得你后续写成一个重点发现：当前自动评估方法最脆弱的地方，不是简单的事实对错，而是教育场景中特有的过程性、高阶性、支持性指标。

另外还有一个很值得深挖的现象：中英文样本之间存在明显差异，而且这种差异是任务相关、模型相关、评估器相关的。按人类均分看，psychological_support 英文样本 4.7127，而中文只有 4.1046，差距非常大；personalized_learning_support 也是英文 4.4727，高于中文 4.0449；但 idea_provision 和 question_generation 则是中文更高。说明语言因素不是统一方向的，它和任务模版、学科表达习惯、评分标准文本语言可能有交互。按生成模型看，deepseek-r1 中文反而高于英文，qwen2.5-14b-instruct 与 qwen2.5-7b-instruct 都是英文明显高于中文。按自动评估器看，EduBenchEvaluator 对中文样本 MAE 只有 0.3745，明显优于英文 0.5154；但 gpt-4o 则相反，英文 0.5573 好于中文 0.6201。这个现象非常适合继续分析，因为它可能揭示不同评估器的语言适配偏向。

我还粗略找了最难和最容易的问题样本。最难样本集中在 error_correction、automatic_grading、problem_solving，尤其是一些高教育阶段、需要精准判断或者生成评分细节的题目，比如博士级历史、数学、法学问题，以及要求按 JSON 返回评分细节的自动评分任务。最容易的样本则集中在 psychological_support、部分简单 automatic_grading 判断题、以及个别结构明确的 personalized_learning_support。这说明“任务名”本身还不够，题目内部还存在明显难度梯度，后续最好在 question 层建一个难度指标，而不是只停留在 task 层。

所以如果你问我接下来怎么系统规划，我会建议这样推进。第一阶段先做“描述性分析成图”，包括任务-维度映射图、各生成模型总体分布图、各任务上的模型箱线图、各评估器相对人类的 MAE 热力图、语言差异对比图。这一阶段目标是把基本现象稳定下来。第二阶段做“能力拆解”，把 metric 按论文附录 E 分成更高层的能力簇，比如指令遵循、事实与知识、推理、高阶思维、个性化支持、情绪与语气一致性，再比较生成模型与评估模型在这些簇上的表现。第三阶段做“评估器分析”，重点看 calibration、高估/低估倾向、不同任务上的失效模式、和人类分歧样本上的行为。第四阶段做“难度分析”，在 question 层根据人类均分、人类方差、模型分歧度、任务类型、学科、语言、教育阶段等构建难度标签。第五阶段才是“评估方法差异”，例如比较 pointwise 打分、平均人类分、majority vote、归一化分数、按任务校准后的分数，看看最终模型排序是否稳定。

如果重点聚焦“模型的评估能力和水平差异”，我建议优先做以下几个问题。第一，EduBenchEvaluator 为什么整体最像人？你可以分任务、分 metric、分语言、分高低分段分别算它的误差，看看它是不是在高分样本特别稳、低分样本却不行，或者在中文特别强。第二，大模型 judge 为什么普遍高估？可以看它们在不同分数段上的 calibration curve，比如人类均值为 3、4、5 时，judge 平均打多少。第三，judge 是否对“自己同系模型”的回答更宽容。比如 deepseek-r1 作为评估器，是否对 deepseek-r1 生成答案的打分偏高。这可以做 evaluator-generator interaction analysis。第四，评估器和人类分歧最大的样本，集中在哪些任务与维度，它们的回答特征是什么，比如格式漂亮但实质浅、语气好但内容不够、推理像样但关键步错。

如果重点聚焦“任务特性”，我建议看三个层次。一个是任务难度，也就是哪个 task 平均分低、分布散、模型区分度高。当前看 problem_solving 和 automatic_grading 最难。第二个是任务的“评估难度”，也就是 judge 的 MAE 高不高。当前看仍然是 automatic_grading、problem_solving 最难评。第三个是任务的“能力画像”，比如 psychological_support 更看重支持性与口吻，teaching_material_generation 更看重知识准确与表达清晰，personalized_learning_support 更看重个性化与场景融合。这个画像做出来后，后续解释模型强弱就会更自然，不会只停留在“谁均分高”。

我把当前最值得写进初步结论的现象整理成几句更凝练的话。第一，这个数据集上的生成模型水平并不均质，deepseek-r1 整体领先明显，qwen-max 次之，而两个 qwen instruct 模型整体偏弱，但在部分解题或事实性维度上并不差。第二，教育任务中最难的不是事实正确性，而是推理严谨性、高阶思维促进、个性化支持和鼓励反馈。第三，EduBenchEvaluator 这个 0.6B 小模型在整体上比多个大模型评估器更接近人类评分，说明专门训练的小评估器在窄任务定义下可能比通用 judge 更稳定。第四，所有自动评估器都有不同程度的高估倾向，尤其是 gpt-4o。第五，自动评分和问题求解是当前最难评的任务，说明“带标准答案/带推理要求”的教育评估仍是自动 judge 的薄弱环节。第六，中英文差异显著，而且会随任务和模型改变方向，不能把语言因素忽略掉。

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
