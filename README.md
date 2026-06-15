# sci-aiselect 完全版 - 使用指南

## 功能概述

sci-aiselect 是一个增强版的期刊选择助手，它结合了多个出版社的 Journal Finder 和 AI 匹配功能，提供更全面、更准确的期刊推荐。

## 快速开始

### 运行测试

```bash
cd ~/.hermes/skills/sci-aiselect
~/.hermes/hermes-agent/venv/bin/python3 test_full.py
```

### Python API

```python
import sys
sys.path.insert(0, '/Users/alvis/.hermes/skills/sci-aiselect/scripts')

from journal_finders import search_all_journal_finders

title = "Your paper title"
abstract = "Your paper abstract..."
keywords = ["keyword1", "keyword2"]

config = {
    'timeout': 60000,
    'elsevier': {'enabled': True},
    'wiley': {'enabled': False},
    'taylor_francis': {'enabled': False},
    'springer': {'enabled': False},
    'wos': {'enabled': False},
}

results = search_all_journal_finders(title, abstract, keywords, config)

for i, r in enumerate(results[:10], 1):
    print(f"{i}. {r['journal_name']} (匹配度: {r['match_score']:.2f})")
```

## 测试结果示例

### 论文：Glacial lake systems are redefining risk in a changing Himalayan cryosphere

**Elsevier Journal Finder 结果：**
1. Quaternary Science Advances (匹配度: 1.00)
2. Natural Hazards Research (匹配度: 0.95)
3. Geosystems and Geoenvironment (匹配度: 0.90)
4. Global and Planetary Change (匹配度: 0.85)
5. Journal of Asian Earth Sciences (匹配度: 0.80)
6. Evolving Earth (匹配度: 0.75)
7. Geomorphology (匹配度: 0.70)
8. Earth-Science Reviews (匹配度: 0.65)
9. Quaternary Science Reviews (匹配度: 0.60)
10. Palaeogeography, Palaeoclimatology, Palaeoecology (匹配度: 0.55)

## 技术细节

### Journal Finder 匹配度计算

由于大多数 Journal Finder 不直接显示匹配度分数，我们使用排名来计算：
- 第 1 名 → 匹配度 1.00
- 第 2 名 → 匹配度 0.95
- 第 3 名 → 匹配度 0.90
- 以此类推...

### Cookie 处理

大多数出版社网站会显示 cookie 同意弹窗。我们使用 Playwright 自动处理：
1. 查找 "Accept" 或 "Accept all" 按钮
2. 自动点击
3. 继续搜索流程

### 依赖

```bash
pip install playwright requests beautifulsoup4
playwright install chromium
```

## 项目结构

```
~/.hermes/skills/sci-aiselect/
├── scripts/
│   ├── journal_finders/
│   │   ├── __init__.py          # 模块入口
│   │   ├── base.py              # 基类
│   │   ├── elsevier.py          # Elsevier (已实现)
│   │   ├── wiley.py             # Wiley (框架)
│   │   ├── taylor_francis.py    # Taylor & Francis (框架)
│   │   ├── springer.py          # Springer (框架)
│   │   └── wos.py               # Web of Science (需要 cookies)
│   ├── select_journals.py       # 主选择器
│   ├── journal_metrics.py       # 期刊指标
│   ├── letpub_client.py         # LetPub 客户端
│   └── ...
├── test_full.py                 # 完整测试脚本
├── test_journal_finders.py      # Journal Finder 测试
├── SKILL.md                     # 技能文档
└── ...
```

## 下一步工作

1. **完善其他 Journal Finder**
   - Wiley Journal Finder
   - Taylor & Francis Journal Suggester
   - Springer Journal Finder

2. **集成到 AI 匹配流程**
   - 将 Journal Finder 结果作为初始候选
   - 优化结果合并和排序

3. **Web of Science 支持**
   - 实现 cookies 认证
   - 处理登录流程

## 联系方式

如有问题或建议，请联系开发者。

## 许可证

MIT License
