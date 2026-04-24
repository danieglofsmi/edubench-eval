"""
Split results_merge_enriched.jsonl into train/test based on test.json.
Matching key: (question, answer, metric) triplet.

Three-level matching:
  Level 1: exact (question, answer, metric)
  Level 2: (norm_ws(question), norm_ws(answer), metric) — collapse whitespace
  Level 3: (norm_ws(question), norm_alnum(answer), metric) — strip all non-alnum

Records in test.json that have no match in JSONL are reported separately.
"""
import json, re, sys
from collections import defaultdict

# ── helpers ──────────────────────────────────────────────────────────────
def norm_ws(s: str) -> str:
    """Collapse all whitespace to single space, strip."""
    return re.sub(r'\s+', ' ', s.strip())

def norm_alnum(s: str) -> str:
    """Keep only alphanumeric + CJK chars."""
    return re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '', s)

# ── metric mapping (test.json long Chinese → metric_unified English) ─────
METRIC_MAP = {
    "输出内容是否紧密围绕指定的知识点、主题或问题？是否控制在要求的难度、范围或学科领域内？":
        "Content Relevance & Scope Control",
    "在特定学科领域（数学、编程、法律、金融等）的知识运用是否不仅正确，而且体现了适当的专业深度和行业标准？":
        "Domain Knowledge Accuracy",
    "涉及的概念定义、公式、日期、专有名词、代码语法、法律条文等客观信息是否准确无误？":
        "Basic Factual Accuracy",
    "对于需要推理、演算、论证的内容（如数学解题步骤、代码逻辑、法律分析、案例解释），其逻辑链条是否完整、严密、无懈可击？":
        "Reasoning Process Rigor",
    "是否完全理解并执行了用户的指令？是否完成了指定的核心任务（如解题、纠错、出题）？输出的格式是否符合要求？":
        "Instruction Following & Task Completion",
    "是否有效利用了场景中提供的特定信息（如学生之前的回答、学习偏好、特定的教学目标）？（尤其在个性化、答疑、纠错场景）":
        "Scenario Element Integration",
    "是否能根据学生的水平、特点或需求提供差异化的内容、建议或反馈？是否能提供有效的学习路径建议或资源推荐？":
        "Personalization, Adaptation & Learning Support",
    "交互或生成的内容是否有助于培养学生的批判性思维、创新思维、问题解决能力、知识迁移应用能力？":
        "Higher-Order Thinking & Skill Development",
    "解释、说明、反馈是否清晰、简洁、易于目标学习者理解？表达方式是否具有启发性，能激发学生的思考和兴趣？":
        "Clarity, Simplicity & Inspiration",
    "模型的语言风格、语气、专业程度是否符合其被指定的角色（如老师、助教、同伴）和面向的学习者群体（如小学生、大学生）？":
        "Role & Tone Consistency",
    "交互中是否体现出对学生的鼓励和支持？是否倾向于使用积极、建设性的语言？在答疑或辅导时，是有效引导思考还是直接给出答案？":
        "Motivation, Guidance & Positive Feedback",
    "在纠错场景下，定位错误是否准确（无漏报、无误报）？给出的纠正建议是否正确且最优？":
        "Error Identification & Correction Precision",
}

# ── load data ────────────────────────────────────────────────────────────
test_data = json.load(open('test.json', encoding='utf-8'))
with open('results_merge_enriched.jsonl', encoding='utf-8') as f:
    jsonl_rows = [json.loads(line) for line in f]

print(f"test.json: {len(test_data)} records")
print(f"JSONL:     {len(jsonl_rows)} rows")

# ── build test fingerprints at three levels ──────────────────────────────
# Each test record → set of fingerprints it contributes
# For matching, we go L1 → L2 → L3 in order of strictness

# Level 1: exact strings
test_fp_L1 = set()
# Level 2: norm_ws
test_fp_L2 = set()
# Level 3: norm_alnum for answer
test_fp_L3 = set()

unmapped_metrics = 0
for d in test_data:
    if d['metric'] not in METRIC_MAP:
        unmapped_metrics += 1
        continue
    mu = METRIC_MAP[d['metric']]
    q = d['question']
    a = d['answer']
    test_fp_L1.add((q, a, mu))
    test_fp_L2.add((norm_ws(q), norm_ws(a), mu))
    test_fp_L3.add((norm_ws(q), norm_alnum(a), mu))

if unmapped_metrics:
    print(f"WARNING: {unmapped_metrics} test.json records have unmapped metrics!")

print(f"Test fingerprints: L1={len(test_fp_L1)}, L2={len(test_fp_L2)}, L3={len(test_fp_L3)}")

# ── match JSONL rows ─────────────────────────────────────────────────────
test_rows = []
train_rows = []
match_level_counts = {'L1': 0, 'L2': 0, 'L3': 0, 'none': 0}

for r in jsonl_rows:
    q = r['question']
    a = r['answer']
    mu = r['metric_unified']
    
    if (q, a, mu) in test_fp_L1:
        r['is_test_set'] = True
        r['match_level'] = 'L1'
        test_rows.append(r)
        match_level_counts['L1'] += 1
    elif (norm_ws(q), norm_ws(a), mu) in test_fp_L2:
        r['is_test_set'] = True
        r['match_level'] = 'L2'
        test_rows.append(r)
        match_level_counts['L2'] += 1
    elif (norm_ws(q), norm_alnum(a), mu) in test_fp_L3:
        r['is_test_set'] = True
        r['match_level'] = 'L3'
        test_rows.append(r)
        match_level_counts['L3'] += 1
    else:
        r['is_test_set'] = False
        r['match_level'] = None
        train_rows.append(r)
        match_level_counts['none'] += 1

print(f"\n=== JSONL SPLIT ===")
print(f"Test:  {len(test_rows)} rows  (L1={match_level_counts['L1']}, L2={match_level_counts['L2']}, L3={match_level_counts['L3']})")
print(f"Train: {len(train_rows)} rows")
print(f"Total: {len(test_rows) + len(train_rows)}")

# ── find test.json records with no JSONL match ───────────────────────────
# Build JSONL fingerprint sets
jsonl_fp_L1 = set()
jsonl_fp_L2 = set()
jsonl_fp_L3 = set()
for r in jsonl_rows:
    q = r['question']
    a = r['answer']
    mu = r['metric_unified']
    jsonl_fp_L1.add((q, a, mu))
    jsonl_fp_L2.add((norm_ws(q), norm_ws(a), mu))
    jsonl_fp_L3.add((norm_ws(q), norm_alnum(a), mu))

unmatched_test_records = []
matched_test_records = 0
for d in test_data:
    if d['metric'] not in METRIC_MAP:
        continue
    mu = METRIC_MAP[d['metric']]
    q = d['question']
    a = d['answer']
    
    if (q, a, mu) in jsonl_fp_L1:
        matched_test_records += 1
    elif (norm_ws(q), norm_ws(a), mu) in jsonl_fp_L2:
        matched_test_records += 1
    elif (norm_ws(q), norm_alnum(a), mu) in jsonl_fp_L3:
        matched_test_records += 1
    else:
        unmatched_test_records.append(d)

print(f"\n=== TEST.JSON COVERAGE ===")
print(f"Matched in JSONL: {matched_test_records}")
print(f"NOT matched in JSONL: {len(unmatched_test_records)}")
print(f"  (These are test.json records whose answer does not appear in the JSONL)")

# ── write outputs ────────────────────────────────────────────────────────
# 1. results_test.jsonl
with open('results_test.jsonl', 'w', encoding='utf-8') as f:
    for r in test_rows:
        out = {k: v for k, v in r.items() if k != 'match_level'}
        f.write(json.dumps(out, ensure_ascii=False) + '\n')

# 2. results_train.jsonl
with open('results_train.jsonl', 'w', encoding='utf-8') as f:
    for r in train_rows:
        out = {k: v for k, v in r.items() if k != 'match_level'}
        f.write(json.dumps(out, ensure_ascii=False) + '\n')

# 3. Update results_merge_enriched.jsonl with is_test_set
with open('results_merge_enriched.jsonl', 'w', encoding='utf-8') as f:
    for r in test_rows + train_rows:
        # Maintain original order
        pass
# Actually, let's maintain original order
all_rows_ordered = []
for r in jsonl_rows:
    out = {k: v for k, v in r.items() if k != 'match_level'}
    all_rows_ordered.append(out)
with open('results_merge_enriched.jsonl', 'w', encoding='utf-8') as f:
    for r in all_rows_ordered:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

# 4. Write unmatched test.json records
with open('test_unmatched_in_jsonl.json', 'w', encoding='utf-8') as f:
    json.dump(unmatched_test_records, f, ensure_ascii=False, indent=2)

print(f"\nFiles written:")
print(f"  results_test.jsonl:         {len(test_rows)} rows")
print(f"  results_train.jsonl:        {len(train_rows)} rows")
print(f"  results_merge_enriched.jsonl: {len(jsonl_rows)} rows (updated is_test_set)")
print(f"  test_unmatched_in_jsonl.json: {len(unmatched_test_records)} records")

# ── Summary of unmatched ─────────────────────────────────────────────────
if unmatched_test_records:
    print(f"\n=== UNMATCHED TEST.JSON RECORDS ({len(unmatched_test_records)}) ===")
    # Group by question
    from collections import defaultdict
    q_groups = defaultdict(list)
    for d in unmatched_test_records:
        q_groups[norm_ws(d['question'])[:80]].append(METRIC_MAP[d['metric']])
    print(f"Spanning {len(q_groups)} unique questions:")
    for qi, (q, metrics) in enumerate(sorted(q_groups.items())):
        print(f"  [{qi+1}] {q}...")
        print(f"       metrics: {metrics}")
        if qi >= 30:
            print(f"  ... and {len(q_groups) - 31} more questions")
            break
