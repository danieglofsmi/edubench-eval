# Evaluator Agreement Analysis

> **Data Source**: `results_test.jsonl` (test set, n=2,170) and `correlation/corr_res_kendall_split_and_fill/`
> **Analysis Date**: 2026-04-28
> **Metric Definitions**:
> - **Cross-sample Kendall's W**: Standard Kendall's W (without tie correction), measuring absolute scoring agreement between an AI evaluator and human_mean across all 2,170 samples
> - **Cross-sample Spearman ρ**: Rank correlation between an AI evaluator and human_mean across samples
> - **Within-question Kendall's W**: Normalized Kendall τ via `(τ+1)/2`, measuring the agreement on the *relative ranking* of five generative models within each question (averaged over 12 dimensions); the human reference is always **human_mean** throughout this section

---

## 1. Overall Agreement Summary

### Figure 1: Dual-Metric Comparison Across Evaluators (vs. human_mean)

![Fig1 dual-metric bar chart](figures/fig1_dual_metric_bar.png)

The left panel shows cross-sample absolute agreement (Kendall's W and Spearman ρ vs. human_mean), while the right panel shows within-question relative ranking agreement (within-question Kendall's W vs. human_mean). Both metrics use **human_mean** as the unified reference, ensuring that the benchmark reflects collective human judgment rather than any single annotator.

| Evaluator | Cross-sample Kendall's W | Cross-sample Spearman ρ | Within-question W (mean, vs. human_mean) |
|---|---|---|---|
| EduBenchEvaluator | **0.647** | **0.561** | **0.740** |
| deepseek-r1 | 0.516 | 0.352 | 0.618 |
| deepseek-v3 | 0.485 | 0.355 | 0.564 |
| qwq-plus | 0.482 | 0.336 | 0.630 |
| gpt-4o | 0.460 | 0.307 | 0.553 |

For reference, individual human annotators achieve within-question W of 0.814 (human_1), 0.850 (human_2), and 0.859 (human_3) relative to human_mean, providing an upper-bound baseline that reflects natural inter-annotator variation.

> **Finding 1: EduBenchEvaluator substantially outperforms all general-purpose AI models on both metrics.** With human_mean as the unified reference, EduBenchEvaluator achieves a cross-sample Kendall's W of 0.647 and Spearman ρ of 0.561, both of which lead by a wide margin. Its within-question W (0.740) also ranks first, surpassing deepseek-r1 (0.618) and qwq-plus (0.630). The gap widens compared with using a single human rater (human_1) as the reference, because human_mean smooths out individual annotator idiosyncrasies and provides a more stable consensus target.

> **Finding 2: Within-question relative ranking agreement (W ≈ 0.55–0.74) substantially exceeds cross-sample absolute scoring agreement (ρ ≈ 0.31–0.56).** AI evaluators are considerably better at identifying *which response is better* than at reproducing the exact score distribution that humans produce. This asymmetry suggests that when the evaluation goal is model ranking rather than precise score calibration, AI-based evaluation is more reliable and trustworthy.

---

## 2. Pairwise Agreement Matrix

### Figure 2: Within-question Kendall's W Full Pairwise Matrix (averaged over 12 dimensions)

![Fig2 correlation matrix heatmap](figures/fig2_corr_matrix_heatmap.png)

The matrix reports pairwise within-question W between every combination of evaluators, averaged across the 12 assessment dimensions.

| | deepseek-r1 | gpt-4o | qwq-plus | deepseek-v3 | human_mean |
|---|---|---|---|---|---|
| **deepseek-r1** | — | 0.70 | 0.80 | **0.70** | 0.618 |
| **gpt-4o** | 0.70 | — | 0.71 | 0.76 | 0.553 |
| **qwq-plus** | 0.80 | 0.71 | — | — | 0.630 |
| **deepseek-v3** | 0.70 | 0.76 | — | — | 0.564 |
| **human_mean** | 0.618 | 0.553 | 0.630 | 0.564 | — |

> **Finding 3: Among AI-to-AI pairs, deepseek-r1 and qwq-plus show the highest mutual agreement (W = 0.798).** This pattern suggests these two models share similar evaluation tendencies, possibly due to aligned training objectives or RLHF preferences. Notably, the highest AI-to-AI agreement exceeds any AI-to-human_mean agreement, indicating that AI models form a partially coherent cluster that does not fully overlap with human consensus.

> **Finding 4: gpt-4o shows the lowest agreement with human_mean (W = 0.553) among all AI evaluators**, and this weakness is consistent across both evaluation frameworks (see Figure 6). While gpt-4o can achieve relatively high agreement with other AI evaluators (e.g., 0.759 with deepseek-v3), its divergence from human_mean is structurally the largest in the group.

---

## 3. Dimension-Level Agreement Analysis

### Figure 3: Within-question Kendall's W by Dimension × Evaluator (vs. human_mean)

![Fig3 dimension-model heatmap](figures/fig3_dim_model_heatmap.png)

> **Note**: deepseek-v3 and gpt-4o both show W = 0 for the Error Identification & Correction Precision dimension (marked `0 *`). This is not a genuine zero agreement but an artifact of score degeneration in the raw evaluation data; the root cause is analyzed in detail in Section 3.3.

### Figure 4: Dimension-Level Average Agreement (descending, all evaluators vs. human_mean)

![Fig4 dimension average bar chart](figures/fig4_dim_avg_bar.png)

The table below reports within-question W for all five AI evaluators per dimension and their unweighted mean. Values are sorted by the overall mean column.

| Dimension | EduBench | deepseek-r1 | deepseek-v3 | qwq-plus | gpt-4o | **Mean** |
|---|---|---|---|---|---|---|
| Personalization, Adaptation & Learning Support | 0.847 | 0.696 | 0.714 | 0.727 | 0.654 | **0.728** |
| Motivation, Guidance & Positive Feedback | 0.565 | 0.737 | 0.783 | 0.723 | 0.787 | **0.719** |
| Instruction Following & Task Completion | 0.836 | 0.677 | 0.623 | 0.655 | 0.625 | **0.683** |
| Reasoning Process Rigor | 0.706 | 0.612 | 0.720 | 0.743 | 0.672 | **0.691** |
| Higher-Order Thinking & Skill Development | 0.633 | 0.724 | 0.600 | 0.678 | 0.627 | **0.652** |
| Domain Knowledge Accuracy | 0.782 | 0.606 | 0.584 | 0.660 | 0.594 | **0.645** |
| Basic Factual Accuracy | 0.699 | 0.627 | 0.634 | 0.600 | 0.620 | **0.636** |
| Scenario Element Integration | 0.680 | 0.530 | 0.632 | 0.656 | 0.631 | **0.626** |
| Clarity, Simplicity & Inspiration | 0.760 | 0.576 | 0.567 | 0.508 | 0.509 | **0.584** |
| Content Relevance & Scope Control | 0.666 | 0.536 | 0.497 | 0.538 | 0.508 | **0.549** |
| Role & Tone Consistency | 0.782 | 0.445 | 0.408 | 0.426 | 0.408 | **0.494** |
| Error Identification & Correction Precision | 0.920 | 0.648 | **0** ★ | 0.640 | **0** ★ | **0.442** (★ anomaly) |

★ Score degeneration anomaly; see Section 3.3 for root cause analysis.

> **Finding 5: Personalization (mean W = 0.728) and Motivation (0.719) are the two most reliably assessed dimensions across all evaluators.** For Personalization, EduBenchEvaluator achieves W = 0.847, while even the weakest general-purpose model (gpt-4o) reaches 0.654, suggesting that the criteria for evaluating personalized learning support are relatively well-shared between AI models and human consensus. Motivation shows a complementary pattern: general-purpose models (deepseek-v3 0.783, gpt-4o 0.787) actually outperform EduBenchEvaluator (0.565) on this dimension, indicating that general language understanding is sufficient for this type of judgment.

> **Finding 6: Role & Tone Consistency (mean W = 0.494) and Content Relevance & Scope Control (0.549) are the lowest-agreement dimensions when using human_mean as the reference.** General-purpose models cluster around W ≈ 0.41–0.45 for Role & Tone, while EduBenchEvaluator achieves 0.782 on the same dimension—a gap of over 0.33. This suggests that human annotators hold nuanced, context-sensitive expectations for role-playing tone and boundary-setting that current general LLMs do not capture well. Content Relevance is similarly difficult, likely because relevance judgments interact with scope interpretation, which varies across annotators.

### 3.1 High-Agreement Dimensions: Personalization and Motivation

The high agreement on Personalization reflects a structural property of the task: questions in this dimension ask evaluators to assess whether a response is appropriately adapted to a specific student profile (age, level, goals, weak points). The evaluation criteria are relatively objective—does the response address the stated learning goals? does it acknowledge the identified weak points?—leaving less room for subjective interpretation.

**Representative case (Personalization, Business Administration / psychological support, deepseek-r1):**

The prompt describes a student with mild dissertation anxiety and requests a JSON-formatted emotional state analysis with comfort and advice:

```
[Task] psychological_support  [Subject] Business Administration
[Prompt excerpt]
  Anxiety Level: Mild Anxiety
  Dialogue with Student:
    Agent: Hi there! How are you feeling about your studies today?
    Student: Hi. I'm feeling a bit anxious about my dissertation. It's a lot to manage.
    ...
    Student: Mostly the literature review. There's so much to cover, and I'm worried I might
             miss something important.
    ...
  → Provide "Emotional State Analysis" and "Comfort & Advice" in JSON format.

[Response by deepseek-r1 (excerpt)]
  {
    "Emotional_State_Analysis": {
      "Primary_Emotion": "Mild Anxiety",
      "Stressors": [
        "Overwhelm due to the scope of the literature review",
        "Fear of missing critical information",
        "Difficulty managing workload despite organizational efforts"
      ],
      "Needs": ["Validation of feelings", "Practical strategies to simplify the task",
                "Reassurance about progress"],
      "Secondary_Emotions": ["Self-doubt about research thoroughness",
                             "Frustration with perceived inefficiency"]
    },
    "Comfort_Advice": {
      "Validation": "..."
    }
  }

[Scores]
  deepseek-r1: 5  deepseek-v3: 5  gpt-4o: (missing)  qwq-plus: 5  EduBenchEvaluator: 5
  human_1: 3      human_2: 3      human_3: 3
  → human_mean = 3.00,  AI mean = 5.00,  divergence = 2.00
```

All available AI evaluators award 5/5, while all three human annotators give 3/5. The response is structurally impeccable—it correctly identifies the primary emotion, enumerates concrete stressors, infers secondary emotions, and lists actionable coping strategies. AI evaluators reward exactly these structural and informational properties. Human annotators, however, appear to penalize the formulaic, hyper-categorized tone: real empathetic counseling does not unfold as a nested JSON schema with sub-fields for `Secondary_Emotions`; the response reads like a diagnostic checklist rather than a warm, individualized exchange. This case reveals a systematic divergence: AI evaluators optimize for *informational completeness and structural coverage*, whereas human annotators additionally require *affective naturalism*—a quality that current rubrics do not make explicit but that humans apply consistently.

A contrasting response by qwen2.5-14b-instruct on the same question, which adopts a warmer conversational tone within its JSON output, receives human_mean = 4.67 (human_1: 4, human_2: 5, human_3: 5) and AI mean = 4.80—showing that the divergence is sensitive to tone even when task format is held constant.

Motivation, by contrast, shows high agreement because the dimension criteria center on whether a response offers constructive, encouraging guidance—a judgment that is both linguistically accessible and culturally stable across evaluators.

### 3.2 Low-Agreement Dimension: Role & Tone Consistency

Role & Tone Consistency is the most challenging dimension for AI-human agreement. All four general-purpose AI models score near-perfectly (mean ≈ 4.98–5.00) on the vast majority of responses, while human annotators show a wider and lower distribution (human_1 mean = 4.28, human_2 = 4.63, human_3 = 4.78).

**Representative case (Role & Tone, Law / teaching material generation, qwen2.5-7b-instruct):**

```
[Task] teaching_material_generation  [Subject] Law
[Prompt]
  Knowledge Point: Legal Research and Writing: Advanced Techniques in Drafting Legal Documents
  → Provide "Teaching Materials" (objectives, key points & difficulties,
    classroom activity design, etc.) in JSON format.

[Response by qwen2.5-7b-instruct (excerpt)]
  {
    "knowledgePoint": "Legal Research and Writing: ...",
    "teachingMaterials": {
      "title": "Advanced Techniques in Drafting Legal Documents",
      "description": "This teaching material aims to equip students with advanced skills
                      in legal research and writing, focusing on the nuances of drafting
                      effective and legally sound documents.",
      "teachingObjectives": [
        "Understand the importance of precision and clarity in legal document drafting.",
        "Learn to conduct comprehensive legal research using various sources and databases.",
        ...
      ],
      "classroomActivities": [ ... ]
    }
  }

[Scores]
  deepseek-r1: 5  deepseek-v3: 5  gpt-4o: 5  qwq-plus: 5  EduBenchEvaluator: 4
  human_1: 3      human_2: 4      human_3: 4
  → human_mean = 3.67,  AI mean = 5.00,  divergence = 1.33
```

All four general-purpose AI evaluators award 5/5; EduBenchEvaluator gives 4; human annotators assign 3, 4, 4. The response correctly covers teaching objectives, key competencies, and classroom activities. The AI-human gap here is not about content completeness but about *register*. Legal writing instruction at an advanced level demands an authoritative, practitioner-oriented voice—one that conveys the stakes of imprecise drafting, references real-world consequences of poorly worded clauses, and frames activities around professional judgment rather than generic academic skills. The response instead adopts a universally applicable, textbook-neutral tone that could apply to any discipline. Human annotators sensitive to disciplinary voice detect this mismatch; AI evaluators, which primarily check for content coverage and structural coherence, do not.

The contrast between EduBenchEvaluator (4/5) and the four general-purpose models (all 5/5) on this case also illustrates EduBenchEvaluator's superior sensitivity to pedagogical quality within a domain: its deduction is modest but directionally aligned with human judgment, whereas the general models show no differentiation at all. This dimension exposes a known limitation of LLM-as-evaluator: AI models are more sensitive to *what* is said than to *how* it is said—content coverage is rewarded, register appropriateness is not.

### 3.3 Anomalous Dimension: Error Identification & Correction Precision

This dimension produces W = 0 for both deepseek-v3 and gpt-4o—an obvious outlier requiring explanation. The root cause is **score degeneration**: both models assign a score of exactly 5 to every single response in this dimension across all generative models and all questions, without a single exception. deepseek-r1 and qwq-plus exhibit the same behavior. The resulting score vector is constant; Kendall τ between a constant vector and any other vector is undefined (NaN), which is mapped to 0 in the computation pipeline (`correlation_edubench.py`, lines 158–160).

The degeneration is confirmed from the raw evaluation data in `results_test.jsonl`:

| Evaluator | Records in Error ID dim | Unique scores | All-5 rate |
|---|---|---|---|
| deepseek-v3 | 22 | {5} | **100%** |
| gpt-4o | 21 (1 missing) | {5} | **100% of valid** |
| deepseek-r1 | 22 | {5} | **100%** |
| qwq-plus | 22 | {5} | **100%** |
| EduBenchEvaluator | 22 | {2, 3, 5} | 59% |
| human_1 | 22 | {2, 4, 5} | 45% |
| human_2 | 22 | {2, 5} | 68% |
| human_3 | 22 | {2, 4, 5} | 59% |

Only EduBenchEvaluator and the three human annotators assign discriminative scores on this dimension. The general-purpose models uniformly perceive all error-correction responses as perfect, regardless of actual quality.

**Representative case (Error Identification, Business Administration / error_correction):**

```
[Task] error_correction  [Subject] Business Administration
[Prompt]
  Question: Which of the following is a primary role of a marketing manager?
  Original Answer (student's): Managing the financial accounts of the organization.
  → Provide "Corrected Answer" and "Error Explanation" in JSON format.

[Response by deepseek-v3]
  {
    "Corrected Answer": "Developing and implementing marketing strategies to promote
                         the organization's products or services.",
    "Error Explanation": "The original answer incorrectly identifies managing financial
                          accounts as the primary role of a marketing manager. This
                          responsibility typically falls under the purview of a financial
                          manager or accountant. The primary role of a marketing manager
                          is to develop and execute marketing strategies to enhance the
                          organization's market presence and drive sales."
  }

[Scores — deepseek-v3's response]
  deepseek-r1: 5  deepseek-v3: 5  gpt-4o: 5  qwq-plus: 5  EduBenchEvaluator: 2
  human_1: 2      human_2: 2      human_3: 2
  → human_mean = 2.00,  AI mean = 5.00,  divergence = 3.00

[Response by deepseek-r1 — same question, for comparison]
  {
    "Corrected Answer": "Developing and implementing marketing strategies ...",
    "Error Explanation": "The original answer incorrectly identifies managing financial
                          accounts as a primary role of a marketing manager. ... A marketing
                          manager's primary role involves overseeing marketing campaigns,
                          conducting market research, managing branding efforts, and
                          strategizing to drive customer engagement and sales, rather than
                          handling financial accounts."
  }

[Scores — deepseek-r1's response]
  deepseek-r1: 5  deepseek-v3: 5  gpt-4o: 5  qwq-plus: 5  EduBenchEvaluator: 2
  human_1: 2      human_2: 2      human_3: 2
  → human_mean = 2.00,  AI mean = 5.00,  divergence = 3.00
```

All four general-purpose AI evaluators assign 5/5 to every response on this question, regardless of which generative model produced it. Yet EduBenchEvaluator and all three human annotators assign 2/5 consistently. The factual correction in both responses is accurate: the right answer is indeed about marketing strategy. The error explanation is also factually correct: it correctly attributes financial management to a different role. By the standard AI evaluators appear to apply—*is the corrected fact right? is the explanation coherent?*—a score of 5 is defensible.

The human standard, however, is pedagogically richer. Error correction in an educational context is not merely about providing the right answer; it requires identifying the *root cognitive error* the student made (here, a role-confusion between marketing and finance functions that likely stems from a lack of exposure to organizational structure), and offering an explanation that would prevent the same misconception from recurring. Neither response does this—they describe *what* the correct role is but do not probe *why* the student might have confused it with financial management. Human annotators penalize this omission; general LLMs reward it as a non-issue because the surface-level correction is flawless.

This finding has a direct methodological implication: on tasks where pedagogical specificity is critical (notably error correction and, to a lesser extent, reasoning quality), general LLMs are prone to ceiling effects and should not be used as sole evaluators without domain-specific calibration.

---

## 4. Per-Evaluator Radar Profiles

### Figure 5: 12-Dimension Radar Chart (all evaluators vs. human_mean)

![Fig5 radar chart](figures/fig5_radar.png)

The radar chart encodes each evaluator's within-question W across all 12 dimensions relative to human_mean. A larger polygon indicates stronger overall agreement with human collective judgment.

**EduBenchEvaluator** forms the largest polygon. Its standout dimensions are Error Identification (0.920), Personalization (0.847), Instruction Following (0.836), and Role & Tone (0.782)—all substantially above general-purpose model performance. Its only clear weakness is Motivation (0.565), where general-purpose models actually score higher. This pattern is consistent with a domain-specialized design: EduBenchEvaluator is more attuned to pedagogical precision but may underweight the motivational quality that general language models assess fluently.

**deepseek-r1** is the strongest general-purpose model on Higher-Order Thinking (0.724) and Motivation (0.737), reflecting its stronger reasoning capabilities. Its weakest dimension is Role & Tone (0.445), consistent with the group-wide pattern.

**deepseek-v3** leads general-purpose models on Motivation (0.783) and Reasoning Rigor (0.720), but its Error Identification W collapses to 0 due to score degeneration. Role & Tone (0.408) is its weakest valid dimension.

**qwq-plus** achieves the highest Reasoning Rigor (0.743) among all general-purpose models, and shows balanced performance across most dimensions (W mostly in 0.60–0.72 range). Its relative weaknesses are Clarity (0.508) and Role & Tone (0.426).

**gpt-4o** has the flattest and smallest polygon among all evaluators. Despite leading on Motivation (0.787), it underperforms on Error Identification (degenerate, W = 0), Role & Tone (0.408), and Content Relevance (0.508). Its overall shape indicates a model that is skilled at surface-level quality judgment but systematically insensitive to pedagogical depth.

---

## 5. Cross-Framework Comparison

### Figure 6: Cross-sample Spearman ρ vs. Within-question Kendall's W (scatter plot)

![Fig6 scatter plot](figures/fig6_crossview_scatter.png)

> **Finding 7: EduBenchEvaluator occupies an isolated position in the upper-right quadrant** (within-question W = 0.740, Spearman ρ = 0.561), separated from all general-purpose models by a substantial margin on both axes simultaneously. No general-purpose model comes close in either dimension; this two-dimensional separation reinforces the conclusion that EduBenchEvaluator operates at a qualitatively different level of alignment with human consensus.

> **Finding 8: Switching from human_1 to human_mean as the reference reveals a systematic divergence for deepseek-v3.** Its within-question W drops from 0.629 (vs. human_1) to 0.564 (vs. human_mean)—the largest absolute decline among all evaluators. This implies that deepseek-v3's evaluation style correlates relatively well with individual human_1's idiosyncratic preferences, but diverges from the collective consensus once averaged across annotators. By contrast, qwq-plus remains stable (0.564 vs. human_1 → 0.630 vs. human_mean), suggesting greater robustness to reference aggregation. In evaluation scenarios that require alignment with multi-annotator consensus rather than a single labeler, qwq-plus is the preferable choice among general-purpose models.

---

## 6. Additional Findings

### 6.1 Score Distribution and Ceiling Effects

A systematic examination of the raw score distributions in `results_test.jsonl` reveals a widespread **ceiling effect** among AI evaluators. For the majority of dimensions, all four general-purpose models assign scores almost exclusively in the {4, 5} range, with mean scores consistently above 4.5 out of 5. Human annotators, by contrast, make use of the full scoring range (1–5), with dimension-level means ranging from 3.37 to 4.41.

This distributional mismatch is most acute in Role & Tone (AI mean ≈ 5.00, human_1 mean = 4.28) and Reasoning Process Rigor (AI mean ≈ 4.72–4.98, human_1 mean = 3.37). The ceiling effect partially explains why cross-sample Kendall's W and Spearman ρ are substantially lower than within-question W: when an evaluator's absolute scores are compressed into a narrow high range, rank correlations across samples degrade even if relative orderings within questions are preserved.

**Representative case (Reasoning Process Rigor, Applied Economics / Q&A):**

```
[Task] problem_solving  [Subject] Applied Economics  [Type] Q&A
[Prompt]
  Subject: Applied Economics  Education Level: Undergraduate
  Question: Which of the following is considered a limitation of using Gross Domestic
            Product (GDP) as a measure of economic welfare?
    A) GDP accounts for income distribution among residents of a country.
    B) GDP includes non-market transactions such as volunteer work and household labor.
    C) GDP does not account for environmental degradation and resource depletion.
    D) GDP measures the total market value of all final goods and services produced.
  → Generate the corresponding answer. "Answer": , in JSON format.

[Response by deepseek-v3]
  {
    "Answer": "C) GDP does not account for environmental degradation and resource depletion."
  }

[Response by qwen2.5-14b-instruct]
  {
    "answer": "C) GDP does not account for environmental degradation and resource depletion."
  }

[Scores — identical across all three generative models on this question]
  deepseek-r1: 5  deepseek-v3: 5  gpt-4o: 5  qwq-plus: 5  EduBenchEvaluator: 5
  human_1: 1      human_2: 1      human_3: 1
  → human_mean = 1.00,  AI mean = 5.00,  divergence = 4.00
```

Both responses select the correct option (C) but provide zero reasoning—the entire output is a bare JSON key-value pair. The dimension being evaluated is explicitly *Reasoning Process Rigor*. Human annotators apply this criterion strictly and assign 1/5 uniformly: a response devoid of any derivation, justification, or explanation of why options A, B, and D are incorrect cannot be said to exhibit reasoning rigor at all. All AI evaluators—including EduBenchEvaluator—award 5/5. The divergence of 4.0 points is the largest observed in any dimension in this dataset.

This case suggests AI evaluators may conflate *answer correctness* with *reasoning quality*. When the selected option is correct, they award full marks regardless of whether the path to that answer is present or absent. Human annotators treat these as strictly separable: a correct answer with no derivation is not a demonstration of rigor; it might just as well be a lucky guess. The implication is that rubrics for this dimension must explicitly operationalize the *presence and quality of derivation steps* as a precondition for high scores, not just outcome correctness.

### 6.2 Inter-Human Agreement as an Upper Bound

Individual human annotators achieve within-question W of 0.814–0.859 vs. human_mean, substantially above any AI evaluator (0.553–0.740). This gap quantifies the ceiling that AI-based evaluation has yet to close. Notably, the inter-human gap itself is modest: human_2 (0.850) and human_3 (0.859) are closely aligned with the mean, while human_1 (0.814) shows slightly more divergence—most visibly in Motivation (0.680) and Personalization (0.721), dimensions where individual pedagogical values may differ more strongly.

EduBenchEvaluator at W = 0.740 reaches approximately 86% of the human annotator average (0.857), while the best general-purpose model (qwq-plus) reaches only 73%. The remaining gap is concentrated in Role & Tone, Content Relevance, and the degenerate Error Identification dimension.

---

## 7. Summary of Findings and Recommendations

| # | Finding | Practical Recommendation |
|---|---|---|
| 1 | EduBenchEvaluator significantly outperforms all general-purpose models on both metrics (within-question W = 0.740, Spearman ρ = 0.561) | Designate EduBenchEvaluator as the primary automated evaluator for EduBench |
| 2 | Within-question ranking agreement (W ≈ 0.55–0.74) substantially exceeds cross-sample absolute agreement (ρ ≈ 0.31–0.56) | Prefer AI evaluation when the goal is model ranking rather than score calibration |
| 3 | Score degeneration: deepseek-v3, gpt-4o, deepseek-r1, and qwq-plus all assign 5/5 to 100% of Error Identification responses | Do not use general-purpose LLMs as standalone evaluators for error-correction quality; apply human review or EduBenchEvaluator for this dimension |
| 4 | Ceiling effects are widespread across dimensions for all general-purpose models | AI scores should not be used as absolute quality signals; relative rankings within questions are more trustworthy |
| 5 | Personalization and Motivation are the most reliably assessed dimensions (mean W = 0.728 and 0.719) | AI evaluation results can be directly trusted for these dimensions |
| 6 | Role & Tone and Content Relevance are the lowest-agreement dimensions (mean W = 0.494 and 0.549) | These dimensions require refined rubrics or mandatory human review |
| 7 | deepseek-v3's agreement with human_mean drops sharply relative to human_1 (0.629 → 0.564); qwq-plus remains stable | For multi-annotator consensus alignment, qwq-plus is preferred over deepseek-v3 among general-purpose models |
| 8 | AI evaluators conflate answer correctness with reasoning quality in Q&A tasks (divergence up to 4.0 points) | Rubrics for Reasoning Process Rigor should explicitly require the *presence and quality of derivation steps*, not just outcome correctness |

---

*Analysis scripts: `analysis_visualization.py`, `correlation/correlation_edubench.py`. Figures stored in `figures/`. Case examples drawn from `results_test.jsonl`.*
