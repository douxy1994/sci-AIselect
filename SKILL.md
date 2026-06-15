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

### 3. AI-Powered Matching
Use AI to analyze paper topics and match with journals, using Journal Finder results as weight reference.

### 4. Journal Learning and Abstract Revision
Learn about a target journal and get abstract revision suggestions.

### 5. Flexible Re-matching
If user is not satisfied, re-run AI matching without Journal Finder constraints.

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
- **If yes**: Learn about the journal and provide abstract revision suggestions
- **If no**: Re-run AI matching without Journal Finder constraints

### Step 6: Journal Learning (If User Selects a Journal)
1. Find journal official website
2. Extract aim and scope
3. Analyze recent articles
4. Provide abstract revision suggestions

### Step 7: Abstract Revision Suggestions
Based on journal analysis:
- Length suggestions
- Structure suggestions
- Style suggestions
- Focus area suggestions

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
- Source: which Journal Finder found it

## Common Mistakes

- Do not treat method terms (ML, DL, GIS) as primary journal field
- Do not recommend journals only because IF is high
- Do not give only elite journals without quality assessment
- Always preserve a realistic submission gradient

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
