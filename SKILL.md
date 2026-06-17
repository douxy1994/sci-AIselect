---
name: sci-aiselect
description: Use when a user wants SCI, SCIE, ESCI, SSCI, or journal submission help, including paper-to-journal recommendations from a title, abstract, keywords, manuscript text, or research direction, and direct journal lookup for metrics such as IF, CAS partition, SCI type, review speed, OA/APC, h-index, and data-source notes.
---

# sci-aiselect

sci-aiselect is a journal lookup and paper-to-journal selection assistant. It combines multiple publisher Journal Finders with AI-powered matching to provide comprehensive journal recommendations.

## Features

### 1. File Extraction
Extract title, abstract, and keywords from Word (.docx) or PDF files.

### 2. Multi-Source Journal Finder
Search journals from 5 publishers simultaneously:
- Elsevier, Wiley, Taylor & Francis, Springer, Web of Science

### 3. LetPub Expanded Search
Beyond the 5 Journal Finders, search LetPub for additional candidates:
- Covers ALL publishers (AGU, Copernicus, MDPI, IEEE, Frontiers, NSR, etc.)
- Includes ESCI journals with good JCR partition
- Not limited to SCIE-only
- Provides review-speed and APC clues that must be normalized before ranking

### 3.1 Review Cycle and APC Controls
- **Review cycle is optional as a ranking factor**: enable it only when the user explicitly says they want fast review, short review cycle, quick acceptance, or fast publication.
- **APC is always reported**: for every recommended journal, show APC amount, source, and RMB estimate when exchange-rate conversion succeeds.
- **Data-source order for review cycle**: journal official page or publisher data first; LetPub review-speed text second; if neither exists, mark as `未获取` rather than guessing.
- **Data-source order for APC**: journal official/APC page first; DOAJ second; OpenAlex third.
- **Currency conversion**: convert non-CNY APC to RMB using a live exchange-rate source; include the rate date when available.
- **WOS On Hold hard rule**: any journal marked `On Hold` by Web of Science / Clarivate is excluded from the candidate pool and must not appear as `推荐`, `备选`, `谨慎`, or `不推荐`.

### 4. Top-Tier Cross-Disciplinary Pool
For papers with strong innovation signals, always consider:
- **National Science Review** (IF~20, Chinese Academy of Sciences, broad scope)
- **Nature** / **Science** (IF~60, breakthrough discoveries)
- **PNAS** (IF~10, broad scope, PNAS Nexus for newer papers)
- **Nature Communications** (IF~16, broad scope)
- These journals are NEVER returned by Journal Finders or LetPub category searches, but they DO publish high-quality earth/climate/environmental science

### 5. Journal Learning and Abstract Revision
Learn about a target journal and get abstract revision suggestions.

### 5.1 Reference Cover Letter
When the user selects a target journal, output a text-only reference cover letter after the abstract suggestions. Use `/Volumes/DouXY/download/cover letter template.docx` only as the structural template; only these bracketed parts are adaptive:
- `[Title]` → manuscript title
- `[Journal]` → target journal name
- `[Introduce the research background and significant]` → infer background and significance from title/abstract
- `[Introduce the main work and novelty of this research ]` → infer main work and novelty from title/abstract
- `[Emphasize the alignment ...]` → combine target-journal scope/preferences with the manuscript’s likely fit, then include standard originality/no simultaneous submission/all-author-approval statements as text that the author must verify

The draft must:
- Start with a Chinese disclaimer that it is for reference only and that the assistant is not responsible for whether the content is reasonable or true.
- Make the editor-facing case for why the manuscript may deserve external review.
- Tie journal fit to the target journal’s scope, readers, or recent-title signals rather than generic flattery.
- Mark originality, no-simultaneous-submission, and all-author-approval statements as declarations the author must verify.
- Output direct text, not a `.docx`, unless the user explicitly asks for a Word document.

Style rules:
- Use concise, confident, editor-facing language.
- Lead with significance and contribution, not flattery.
- Tie claims to wording from the title/abstract and journal scope.
- Avoid unsupported hype such as `groundbreaking`, `paradigm-shifting`, `highly cited`, or `guaranteed impact` unless the user provides evidence.
- Keep all unverified declarations clearly marked for author verification.

### 6. Flexible Re-matching
If user is not satisfied, re-run AI matching without Journal Finder constraints.

## Workflow Design

### Innovation Assessment: What IS and IS NOT Innovation

**核心原则：创新不是"做了什么分析"，而是"改变了什么认知"。**

#### ✅ 真正的创新信号
1. **机制发现** — 揭示了之前未被充分认识的因果关系
   - 例："frozen lateral moraine containing dead ice" → 冻土退化是冰碛坍塌的根本原因
   - 例："sediment erosion 20× exceeds moraine collapse volume" → 侵蚀量远超预期

2. **认知改变** — 改变了领域对某类问题的理解框架
   - 例："paradigm shifts in GLOF risk management"
   - 例："wider relevance given rapid climate warming worldwide"

3. **首次方法应用** — 第一次用某种方法解决了之前无法解决的问题
   - 例："first detection of GLOF precursors 3 years in advance using optical pixel offset tracking"
   - 注意：必须是"第一次用"，不是"用了"

4. **反直觉发现** — 发现了与预期不符的结果
   - 例："in stark contrast, no discernible deformation anomalies were detected around the ice dam"

5. **显著的定量发现** — 通过数据展现的创新（不是声明，是发现本身）
   - 例："5-fold increase in annual landslide volumes" → 倍数级变化
   - 例："comparable to that of alpine glaciation" → 可比重要自然过程
   - 例："migrating upslope in the wake of retreating glaciers" → 空间迁移趋势
   - 注意：这类创新**不会用"novel"等词**，而是通过数据和对比展现

#### ❌ 不是创新（但经常被误判为创新）
1. **用了某种方法** — "using r.avaflow model"、"integrates satellite observations" → 不是创新
2. **涉及某个主题** — "compound hazard interactions"、"transboundary settings" → 不是创新
3. **描述某种现象** — "accelerated growth"、"spatially variable" → 不是创新
4. **自称为新** — "novel framework for GLOF hazard assessment"（但实际只是标准敏感性分析）→ 不一定是创新
5. **覆盖了某个区域** — "Indian Himalayan Region"、"36 glacial lakes" → 不是创新

#### 如何区分
| 问题 | 是创新 | 不是创新 |
|------|--------|---------|
| 揭示了新的物理机制？ | ✅ 冻土退化导致冰碛坍塌 | ❌ 用模型重建了溃决过程 |
| 改变了领域认知？ | ✅ GLOF 风险管理需要范式转变 | ❌ 提供了区域风险管理的参考 |
| 第一次做某件事？ | ✅ 首次提前3年检测到前兆 | ❌ 用卫星影像分析了冰湖变化 |
| 发现了反直觉的结果？ | ✅ 冰坝前无变形信号 vs 冰碛有 | ❌ 冰湖面积扩大了15% |

### Three-Layer Signal Architecture

期刊推荐基于三层信号，按可靠性排序：

#### Layer 1: Journal Finder 初判（首要，定级别）
- 5 个出版社的 Journal Finder 各自独立评估论文，给出排序
- **目的：判断论文的级别**（breakthrough / high / solid），而非提供最终候选期刊
- 如果所有出版社都把区域/专业期刊排第一 → 论文级别为 solid
- 如果多个出版社把高影响力期刊排第一 → 论文级别为 high
- **关键：初判完成后，最终选刊不限于这 5 个出版社**

#### Layer 2: 扩展选刊（核心，全覆盖）
初判确定论文级别后，从以下来源扩展候选池：
- **LetPub 搜索**：覆盖所有出版社（AGU、Copernicus、MDPI、IEEE、Frontiers 等），不限 SCIE
- **跨学科顶级期刊池**：NSR、Nature、Science、PNAS 等（永远不会出现在 Journal Finder 中）
- **期刊分布校准**：通过文献检索看类似主题的论文都发在什么期刊上

#### Layer 3: 创新性微调（辅助，可靠性低）
- 用正则模式检测摘要中的创新信号
- 仅用于极端情况的微调，不能推翻 Layer 1 的级别判断

### Agent 执行流程

```
Step 1: Journal Finder 初筛（5 个出版社并行）
        → 得到每个出版社的推荐排序

Step 2: 从排序推断论文档次
        → 多数 #1 是 Nature 级 → breakthrough
        → 多数 #1 是高影响力 → high
        → 多数 #1 是区域/专业 → solid
        → 分歧大 → 需要 Layer 2 验证

Step 3: 创新点提取 + 文献检索（当需要验证时）
        a) 从摘要提取"可能的创新点"关键词
        b) 用关键词搜索文献（web_search 或 scansci_pdf_search）
        c) 分析检索结果：
           - 创新性：类似文献多不多？
           - 期刊分布：类似文献发在什么期刊上？
        d) 根据结果调整推荐

Step 4: 最终推荐
        → 综合三层信号，给出 10 个期刊推荐
        → 每个推荐标注信号来源和置信度
        → 默认展示 APC 和审稿周期信息
        → 仅在用户要求快审/尽快接收见刊时，把审稿周期纳入排序权重
```

### Review Cycle Weighting Rules

审稿周期不是默认排序维度。只有出现以下意图时才启用：
- 中文：`审稿周期短`、`审稿快`、`快审`、`尽快接收`、`尽快见刊`、`快速发表`
- English: `fast review`, `short review cycle`, `rapid decision`, `quick acceptance`, `fast publication`

启用后：
1. 先查期刊官网或出版商页面，记录 `time to first decision`、`review time`、`submission to acceptance`、`acceptance to publication`。
2. 官网未获取时，用 LetPub 的 `平均审稿速度`，区分 `期刊官网数据`、`来源Elsevier官网`、`网友分享经验`。
3. 将周期折算为天数：天=原值，周×7，月×30。
4. 排序加权：≤45天明显加分，46-75天加分，76-120天小幅加分，121-180天不加不扣，181-270天扣分，>270天重扣；未知周期小扣分。
5. 报告必须显示依据：如 `整体约45天（官网）` 或 `整体约8.3个月（LetPub网友）`。

### APC Reporting Rules

每个推荐期刊必须显示 APC：
1. 优先查期刊官网/APC 页面或出版商页面；能获取官方金额时标记为官网来源。
2. 官网未获取时查 DOAJ；DOAJ `has_apc=false` 时显示 `无APC（DOAJ）`。
3. DOAJ 未获取时用 OpenAlex `apc_prices` / `apc_usd`；OpenAlex 的 APC 通常来自 DOAJ，报告中标注来源。
4. 非人民币金额必须用实时汇率折算 RMB，并显示汇率日期；汇率失败时显示原币金额和 `人民币汇率未获取`。
5. 不要因为 APC 高低自动改变推荐梯度，除非用户明确说有预算限制；默认只报告 APC，作为用户决策信息。

### WOS On Hold Exclusion

`On Hold` 是硬排除条件：
1. Web of Science / Clarivate / Master Journal List 页面出现 `On Hold`、`收录暂停`、`暂停收录`，立即从候选池删除。
2. LetPub、官网、Journal Finder、缓存或原始数据中出现等价 on-hold 字段，也删除。
3. 删除后不再降级展示；不要把 on-hold 期刊放进 `谨慎` 或 `不推荐` 列表。
4. 如果用户指定的目标期刊处于 on-hold，只能说明原因并建议替代期刊。

### Submission Band Logic
| Paper Tier | Max Band | Meaning |
|---|---|---|
| breakthrough | 冲刺 | No cap — top journals are appropriate |
| high | 冲刺 | No cap — quality justards ambition |
| solid_high | 稳妥 | Conservative — don't overshoot |
| solid | 稳妥 | Conservative — match journal to solid work |

**Scope NEVER affects submission band.** A regional study with strong innovation gets "冲刺" if it deserves it.

## Quick Start

### Option 1: Interactive Mode (Recommended)
```bash
cd ~/.hermes/skills/sci-aiselect
~/.hermes/hermes-agent/venv/bin/python3 interactive.py
```

### Option 2: From File
```bash
cd ~/.hermes/skills/sci-aiselect
~/.hermes/hermes-agent/venv/bin/python3 << 'EOF'
import sys
sys.path.insert(0, 'scripts')
from full_workflow import extract_and_select
print(extract_and_select("path/to/paper.pdf"))
EOF
```

### Option 3: Manual Input
```bash
cd ~/.hermes/skills/sci-aiselect
~/.hermes/hermes-agent/venv/bin/python3 << 'EOF'
import sys
sys.path.insert(0, 'scripts')
from full_workflow import quick_select

title = "Your paper title"
abstract = "Your paper abstract..."
keywords = ["keyword1", "keyword2"]

print(quick_select(title, abstract, keywords))
EOF
```

Fast-review mode:
```bash
cd ~/.hermes/skills/sci-aiselect
~/.hermes/hermes-agent/venv/bin/python3 << 'EOF'
import sys
sys.path.insert(0, 'scripts')
from full_workflow import quick_select

print(quick_select(
    "Your paper title",
    "Your paper abstract...",
    ["keyword1", "keyword2"],
    review_preference=True,
))
EOF
```

### Option 4: Journal Learning
```bash
cd ~/.hermes/skills/sci-aiselect
~/.hermes/hermes-agent/venv/bin/python3 << 'EOF'
import sys
sys.path.insert(0, 'scripts')
import asyncio
from journal_learner import learn_and_suggest

result = asyncio.run(learn_and_suggest(
    "Journal of Hydrology",
    "Your abstract here...",
    "Your title here"
))
print(result)
EOF
```

## Workflow

### Step 1: File Extraction (Optional)
If user provides a file, extract title, abstract, and keywords.

### Step 2: Journal Finder Initial Screening
Search journals from 5 publishers simultaneously.

### Step 3: AI-Powered Selection
Use AI to:
1. Infer paper profile (topics, methods, categories)
2. Search LetPub for candidate journals
3. Aggregate metrics from LetPub and OpenAlex
4. Score and rank candidates (using Journal Finder results as weight reference)
5. Assign submission bands (冲刺/稳妥/保底)

### Step 4: Present 10 Recommendations
Show top 10 journals with recommendation tier, submission band, metrics, and source.

### Step 5: User Decision
Ask user if they have a preferred journal:
- **If yes**: Learn about the journal, provide abstract revision suggestions, and output a reference-only cover letter
- **If no**: Re-run AI matching without Journal Finder constraints

### Step 6: Journal Learning (If User Selects a Journal)
1. Find journal official website
2. Extract aim and scope
3. Analyze recent articles
4. Provide abstract revision suggestions
5. Generate a text-only reference cover letter from the template’s bracketed instructions

### Step 7: Abstract Revision Suggestions
Based on journal analysis:
- Length suggestions
- Structure suggestions
- Style suggestions
- Focus area suggestions

### Step 8: Reference Cover Letter
After abstract revision suggestions, output `Cover Letter 参考稿（仅供参考）`:
1. Start with a prominent disclaimer in Chinese: the cover letter is for reference only; it is generated only from title, abstract, and public journal information; the assistant is not responsible for whether the content is reasonable or true.
2. Follow the template order exactly: `Dear Editor` → submission sentence → background/significance paragraph → main work/novelty paragraph → journal alignment plus required declaration paragraph → `Sincerely` → `XXXXX`.
3. Make the editorial hook explicit: name the reason the manuscript may merit external review.
4. Emphasize likely reader interest and journal fit using aim/scope and recent-title signals.
5. Do not invent author names, manuscript number, funding, ethics approval, conflicts of interest, data availability, or reviewer suggestions.
6. For originality, no simultaneous submission, and all-author approval statements, include them only as text that the author must verify before use.
7. Do not output a `.docx` unless the user explicitly asks for a Word document.

## Configuration

### Journal Finder Configuration
```python
config = {
    'timeout': 90000,
    'retry_count': 1,
    'elsevier': {'enabled': True},
    'wiley': {'enabled': True},
    'taylor_francis': {'enabled': True},
    'springer': {'enabled': True},
    'wos': {'enabled': True},
}
```

## Required Output

For each recommendation, include:
- Tier: `推荐`, `备选`, `谨慎`, or `不推荐`
- Submission band: `冲刺`, `稳妥`, `保底`, or `谨慎`
- Metrics: IF, partition, SCI type, h-index
- APC: original currency, RMB estimate, data source, and rate date when available
- Review cycle: first decision / review / acceptance / publication timing when available
- Source: which Journal Finder found it

## Common Mistakes

- Do not treat method terms (ML, DL, GIS) as primary journal field
- Do not recommend journals only because IF is high
- Do not give only elite journals without quality assessment
- Always preserve a realistic submission gradient
- **Do not penalize ESCI journals unconditionally** — ESCI + JCR Q1/Q2 is a good journal; only penalize ESCI without good partition data
- **Do not limit candidates to 5 Journal Finder publishers** — use LetPub to expand coverage to all publishers (AGU, Copernicus, MDPI, IEEE, Frontiers, etc.)
- **Do not let IF ranking override topic fit** — aim & scope matching should be able to compensate for IF differences
- **"novel framework" in abstract does not equal innovation** — check if the framework is actually novel or just a standard sensitivity analysis with a new name
- **Do not rank by review speed unless the user asks for speed** — review cycle is an optional preference, not a default quality metric
- **Do not include WOS On Hold journals anywhere in recommendations** — hard exclude them before scoring
- **Do not hide APC** — every recommendation must show APC status, even when APC is unknown
- **Do not invent APC or review-cycle data** — mark `未获取` when official/DOAJ/OpenAlex/LetPub data is unavailable
- **Do not treat cover letter content as verified** — it is reference text only; do not add author names, ethics, funding, conflicts, data availability, reviewer suggestions, manuscript IDs, or other facts absent from title/abstract
- **Do not write a generic cover letter** — state why the manuscript may deserve external review and tie journal fit to scope, readers, and topic overlap rather than flattery

## Pitfalls

- Journal Finder uses Playwright, which requires Chromium browser
- First run may take longer due to browser installation
- Some websites may block automated access (e.g., Wiley)
- LetPub requests have 0.5s delay to avoid blocking
- OpenAlex API may timeout occasionally

## Verification

Run the tests:
```bash
cd ~/.hermes/skills/sci-aiselect

# Full workflow test
~/.hermes/hermes-agent/venv/bin/python3 << 'EOF'
import sys
sys.path.insert(0, 'scripts')
from full_workflow import quick_select
print(quick_select(
    "Glacial lake systems are redefining risk in a changing Himalayan cryosphere",
    "Glacial lakes are expanding rapidly across the Himalaya...",
    ["glacial lakes", "GLOF", "Himalaya"]
))
EOF
```

## Dependencies

```bash
pip install playwright requests beautifulsoup4 pymupdf python-docx
playwright install chromium
```
