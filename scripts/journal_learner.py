"""
期刊学习和摘要润色模块

功能：
1. 学习期刊的 aim and scope
2. 分析最近发表的文献
3. 给出摘要润色建议
4. 基于模板生成仅供参考的 cover letter 文本
"""
from __future__ import annotations

import re
import asyncio
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright


class JournalLearner:
    """期刊学习器"""
    
    def __init__(self):
        self.timeout = 60000
    
    async def learn_journal(self, journal_name: str) -> Dict:
        """
        学习期刊信息
        
        Args:
            journal_name: 期刊名称
        
        Returns:
            Dict: 期刊信息
        """
        print(f"\n正在学习期刊: {journal_name}")
        
        # 1. 搜索期刊官网
        journal_url = await self._find_journal_website(journal_name)
        
        # 2. 获取 aim and scope
        aim_scope = await self._get_aim_scope(journal_url)
        
        # 3. 获取最近发表的文章
        recent_articles = await self._get_recent_articles(journal_url)
        
        # 4. 分析文章风格
        style_analysis = self._analyze_style(recent_articles)
        
        return {
            'name': journal_name,
            'url': journal_url,
            'aim_scope': aim_scope,
            'recent_articles': recent_articles,
            'style_analysis': style_analysis,
        }
    
    async def _find_journal_website(self, journal_name: str) -> str:
        """查找期刊官网"""
        # 使用 Google 搜索
        search_query = f"{journal_name} official website"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # 访问 Google 搜索
                await page.goto(f'https://www.google.com/search?q={search_query}', 
                              wait_until='domcontentloaded', timeout=self.timeout)
                await page.wait_for_timeout(3000)
                
                # 提取第一个结果的链接
                links = await page.query_selector_all('a[href*="http"]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and ('springer' in href or 'elsevier' in href or 'wiley' in href or 
                                'nature' in href or 'agu' in href or 'copernicus' in href):
                        return href
                
                return ""
            
            except Exception as e:
                print(f"查找期刊官网失败: {e}")
                return ""
            
            finally:
                await browser.close()
    
    async def _get_aim_scope(self, journal_url: str) -> str:
        """获取期刊的 aim and scope"""
        if not journal_url:
            return ""
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                await page.goto(journal_url, wait_until='domcontentloaded', timeout=self.timeout)
                await page.wait_for_timeout(3000)
                
                # 查找 aim and scope 相关内容
                text = await page.inner_text('body')
                
                # 尝试提取 aim and scope
                aim_scope = self._extract_aim_scope(text)
                
                return aim_scope
            
            except Exception as e:
                print(f"获取 aim and scope 失败: {e}")
                return ""
            
            finally:
                await browser.close()
    
    def _extract_aim_scope(self, text: str) -> str:
        """从页面文本中提取 aim and scope"""
        # 查找 aim and scope 相关段落
        patterns = [
            r'(?:aims?\s*(?:and|&)\s*scope|about\s+(?:this\s+)?journal|journal\s+description|mission)[:\s]*(.*?)(?:(?:key\s*words|topics|scope\s+notes|submit|publish|contact)|\n\n|\Z)',
            r'(?:we\s+publish|this\s+journal|the\s+journal\s+publishes)[:\s]*(.*?)(?:(?:key\s*words|topics|scope\s+notes|submit|publish|contact)|\n\n|\Z)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:2000]
        
        return ""
    
    async def _get_recent_articles(self, journal_url: str) -> List[Dict]:
        """获取最近发表的文章"""
        if not journal_url:
            return []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                await page.goto(journal_url, wait_until='domcontentloaded', timeout=self.timeout)
                await page.wait_for_timeout(3000)
                
                # 查找文章列表
                articles = await self._extract_articles(page)
                
                return articles[:5]  # 只返回前 5 篇
            
            except Exception as e:
                print(f"获取最近文章失败: {e}")
                return []
            
            finally:
                await browser.close()
    
    async def _extract_articles(self, page) -> List[Dict]:
        """从页面提取文章信息"""
        articles = []
        
        try:
            # 查找文章标题元素
            title_elements = await page.query_selector_all('h3 a, h2 a, [class*="title"] a, [class*="article"] a')
            
            for elem in title_elements[:10]:
                title = await elem.inner_text()
                href = await elem.get_attribute('href')
                
                if title and len(title) > 20:
                    articles.append({
                        'title': title.strip(),
                        'url': href or '',
                    })
        
        except Exception as e:
            print(f"提取文章失败: {e}")
        
        return articles
    
    def _analyze_style(self, articles: List[Dict]) -> Dict:
        """分析文章风格"""
        if not articles:
            return {
                'typical_length': 'unknown',
                'common_structure': 'unknown',
                'writing_style': 'unknown',
            }
        
        # 分析标题风格
        titles = [a['title'] for a in articles]
        
        # 标题长度统计
        avg_length = sum(len(t) for t in titles) / len(titles) if titles else 0
        
        # 常见词汇
        common_words = []
        for title in titles:
            words = title.lower().split()
            common_words.extend(words)
        
        # 统计词频
        word_freq = {}
        for word in common_words:
            if len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 排序
        sorted_words = sorted(word_freq.items(), key=lambda x: -x[1])
        
        return {
            'typical_title_length': f"{avg_length:.0f} 字符",
            'common_title_words': [w for w, _ in sorted_words[:10]],
            'article_count': len(articles),
        }


def suggest_abstract_revision(
    original_abstract: str,
    journal_info: Dict,
    title: str = "",
) -> str:
    """
    根据期刊信息给出摘要润色建议
    
    Args:
        original_abstract: 原始摘要
        journal_info: 期刊信息
        title: 论文标题
    
    Returns:
        str: 润色建议
    """
    suggestions = []
    
    # 1. 长度建议
    word_count = len(original_abstract.split())
    if word_count < 150:
        suggestions.append("- 摘要偏短（当前约 {} 词），建议扩展到 150-250 词，增加研究方法和结果的详细描述".format(word_count))
    elif word_count > 300:
        suggestions.append("- 摘要偏长（当前约 {} 词），建议精简到 150-250 词，突出核心发现".format(word_count))
    else:
        suggestions.append("- 摘要长度合适（当前约 {} 词）".format(word_count))
    
    # 2. 结构建议
    has_background = any(w in original_abstract.lower() for w in ['background', 'introduction', 'context', 'motivation'])
    has_methods = any(w in original_abstract.lower() for w in ['method', 'approach', 'data', 'analysis', 'observation'])
    has_results = any(w in original_abstract.lower() for w in ['result', 'finding', 'show', 'reveal', 'indicate'])
    has_conclusion = any(w in original_abstract.lower() for w in ['conclusion', 'implication', 'suggest', 'highlight'])
    
    if not has_background:
        suggestions.append("- 建议在开头明确研究背景和动机")
    if not has_methods:
        suggestions.append("- 建议简要说明研究方法或数据来源")
    if not has_results:
        suggestions.append("- 建议突出核心研究结果")
    if not has_conclusion:
        suggestions.append("- 建议在结尾总结研究意义或启示")
    
    # 3. 期刊风格建议
    aim_scope = journal_info.get('aim_scope', '')
    if aim_scope:
        # 分析期刊关注的主题
        focus_areas = []
        keywords = ['climate', 'environment', 'ecology', 'hydrology', 'geology', 
                   'remote sensing', 'GIS', 'sustainability', 'hazard', 'risk']
        for keyword in keywords:
            if keyword in aim_scope.lower():
                focus_areas.append(keyword)
        
        if focus_areas:
            suggestions.append("- 该期刊关注以下主题：{}，建议在摘要中强调与这些主题的关联".format(', '.join(focus_areas)))
    
    # 4. 常见标题词汇建议
    style_analysis = journal_info.get('style_analysis', {})
    common_words = style_analysis.get('common_title_words', [])
    if common_words:
        suggestions.append("- 该期刊近期文章标题常用词汇：{}，可以考虑在标题或摘要中使用类似术语".format(', '.join(common_words[:5])))
    
    # 5. 写作风格建议
    suggestions.append("- 建议使用简洁、直接的学术语言，避免过度修饰")
    suggestions.append("- 建议突出研究的创新点和实际意义")
    suggestions.append("- 建议使用具体的数据或定量描述，而非笼统的定性描述")
    
    # 生成建议报告
    report = []
    report.append("# 摘要润色建议")
    report.append("")
    report.append(f"**目标期刊**: {journal_info.get('name', '未知')}")
    report.append("")
    
    if journal_info.get('aim_scope'):
        report.append("## 期刊 Aim & Scope")
        report.append("")
        report.append(journal_info['aim_scope'][:500] + "...")
        report.append("")
    
    report.append("## 润色建议")
    report.append("")
    for suggestion in suggestions:
        report.append(suggestion)
    report.append("")
    
    report.append("## 注意事项")
    report.append("")
    report.append("- 以上建议基于期刊公开信息和近期发表文章的分析")
    report.append("- 具体投稿时请参考期刊的 Author Guidelines")
    report.append("- 建议阅读 2-3 篇该期刊近期发表的相似主题文章，学习其写作风格")
    
    return "\n".join(report)


def generate_reference_cover_letter(
    title: str,
    abstract: str,
    journal_info: Dict,
) -> str:
    """
    Generate a reference-only cover letter from title, abstract, and target-journal signals.

    The output intentionally includes a strong disclaimer because the tool only sees
    title/abstract-level evidence and cannot verify authorship, originality, prior
    submission status, ethical approvals, conflicts of interest, or factual claims.
    """
    journal_name = journal_info.get('name', 'the target journal')
    title = (title or '[Manuscript Title]').strip()
    abstract = (abstract or '').strip()
    background = _infer_background_significance_paragraph(title, abstract)
    main_work = _infer_main_work_and_novelty_paragraph(abstract)
    editorial_hook = _infer_editorial_hook(title, abstract, journal_info)
    alignment = _infer_journal_alignment(journal_info)

    lines = [
        "# Cover Letter 参考稿（仅供参考）",
        "",
        "> 重要声明：以下 cover letter 仅供参考，只基于你提供的标题、摘要和公开期刊信息生成；我不对内容是否合理和真实负责。",
        "> 我无法核验作者贡献、伦理审批、利益冲突、原创性、是否一稿多投、数据可用性或任何投稿声明。正式投稿前必须由作者逐句核实和修改。",
        "> 模板说明：正文仅替换模板方括号内容；不生成 Word 文件。",
        "",
        "Dear Editor,",
        "",
        f"We are pleased to submit our manuscript, “{title},” for consideration in {journal_name}.",
        "",
        background,
        "",
        main_work,
        "",
        editorial_hook + " " + alignment,
        "",
        "Please verify before use: We confirm that this manuscript is original, has not been published elsewhere, and is not under consideration by any other journal. We further confirm that all authors have approved the manuscript and agree with its submission to this journal.",
        "",
        "Thank you for considering our manuscript. We would be grateful for the opportunity to have it reviewed for publication in your journal, and we look forward to your response.",
        "",
        "Sincerely,",
        "",
        "XXXXX",
    ]
    return "\n".join(lines)


def _infer_background_significance_paragraph(title: str, abstract: str) -> str:
    sentences = _split_sentences(abstract)
    title_signal = _title_signal_phrase(title)
    if sentences:
        return (
            f"The manuscript addresses {title_signal}, a topic with clear relevance for the field. "
            f"The abstract frames the underlying problem as follows: {_trim_sentence(sentences[0])} "
            "This opening issue gives the submission an editor-facing rationale beyond a narrow case description."
        )
    return (
        f"The manuscript addresses {title_signal}, a topic that may be relevant to the journal’s readership. "
        "The authors should strengthen this paragraph with the verified research gap, broader significance, and why the study is timely."
    )


def _infer_main_work_and_novelty_paragraph(abstract: str) -> str:
    sentences = _split_sentences(abstract)
    method_keywords = (
        'method', 'approach', 'data', 'dataset', 'model', 'analysis', 'experiment',
        'observation', 'remote sensing', 'survey', 'monitoring', 'simulation'
    )
    result_keywords = (
        'result', 'finding', 'show', 'reveal', 'indicate', 'demonstrate',
        'highlight', 'suggest', 'found', 'identified', 'observed'
    )
    method_sentence = ""
    result_sentence = ""
    for sentence in sentences:
        lowered = sentence.lower()
        if not method_sentence and any(keyword in lowered for keyword in method_keywords):
            method_sentence = _trim_sentence(sentence)
        if not result_sentence and any(keyword in lowered for keyword in result_keywords):
            result_sentence = _trim_sentence(sentence)
        if method_sentence and result_sentence:
            break

    if not method_sentence and len(sentences) >= 2:
        method_sentence = _trim_sentence(sentences[1])
    if not result_sentence and sentences:
        result_sentence = _trim_sentence(sentences[-1])

    if method_sentence and result_sentence and method_sentence != result_sentence:
        return (
            f"To address this problem, the study appears to use the following evidence base or analytical strategy: {method_sentence} "
            f"The main result or contribution highlighted in the abstract is: {result_sentence} "
            "For an editor, this paragraph should make the paper’s concrete advance immediately visible."
        )
    if method_sentence:
        return (
            f"To address this problem, the study appears to present the following core work: {method_sentence} "
            "The authors should refine this paragraph by adding the most concrete verified result and the specific advance over prior work."
        )
    return (
        "To address this problem, the manuscript should summarize the core work, evidence base, and most concrete finding in one compact paragraph. "
        "Because only the title and abstract are available here, the authors should replace this sentence with verified methodological and result details from the manuscript."
    )


def _infer_editorial_hook(title: str, abstract: str, journal_info: Dict) -> str:
    hook_parts = []
    novelty_sentence = _find_novelty_or_implication_sentence(abstract)
    if novelty_sentence:
        hook_parts.append(
            "The main reason this submission may merit external review is that the abstract points to a specific contribution: "
            + _trim_sentence(novelty_sentence)
        )
    else:
        hook_parts.append(
            "The main reason this submission may merit external review is its potential to connect a recognizable research problem with evidence that could be useful to the journal’s readers."
        )

    scope_terms = _extract_focus_terms(str(journal_info.get('aim_scope', '') or ''))
    if scope_terms:
        hook_parts.append(
            "This framing should help the editor see a direct readership fit around "
            + ", ".join(scope_terms[:4])
            + "."
        )
    else:
        title_terms = _content_terms(title)[:4]
        if title_terms:
            hook_parts.append(
                "The title itself signals a readership fit around "
                + ", ".join(title_terms)
                + "."
            )

    return " ".join(hook_parts)


def _find_novelty_or_implication_sentence(abstract: str) -> str:
    sentences = _split_sentences(abstract)
    novelty_keywords = (
        'novel', 'first', 'new', 'reveal', 'demonstrate', 'show', 'finding',
        'indicate', 'highlight', 'significant', 'advance', 'improve',
        'unprecedented', 'mechanism', 'implication', 'important', 'key',
        'substantial', 'robust', 'risk', 'management', 'policy'
    )
    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in novelty_keywords):
            return sentence
    return ""


def _infer_journal_alignment(journal_info: Dict) -> str:
    journal_name = journal_info.get('name', 'the target journal')
    aim_scope = str(journal_info.get('aim_scope', '') or '')
    focus_terms = _extract_focus_terms(aim_scope)
    style_analysis = journal_info.get('style_analysis', {}) or {}
    common_words = style_analysis.get('common_title_words', [])[:5]

    if focus_terms:
        return (
            f"We therefore believe the manuscript is potentially well aligned with {journal_name}: the journal’s stated scope emphasizes "
            f"{', '.join(focus_terms)}, and the manuscript’s topic and implications appear relevant to those readers. "
            "This combination of topical fit, identifiable contribution, and potential broader interest is why the paper may be suitable for peer review."
        )
    if common_words:
        return (
            f"We therefore believe the manuscript is potentially suitable for {journal_name}. Recent article-title signals from the journal include "
            f"{', '.join(common_words)}, which may overlap with the manuscript’s subject area and intended readership. "
            "This likely readership connection is the central reason for requesting editorial consideration."
        )
    return (
        f"We therefore believe the manuscript may be of interest to readers of {journal_name}, subject to the authors’ verification of fit with the journal’s aims, scope, and author guidelines. "
        "The authors should sharpen this paragraph by naming the journal-specific audience and the most compelling reason the editor should send the paper for external review."
    )


def _extract_focus_terms(text: str) -> List[str]:
    focus_terms = []
    keywords = [
        'climate', 'environment', 'ecology', 'hydrology', 'geology',
        'remote sensing', 'GIS', 'sustainability', 'hazard', 'risk',
        'water', 'earth', 'management', 'policy', 'model'
    ]
    lowered = text.lower()
    for keyword in keywords:
        if keyword in lowered and keyword not in focus_terms:
            focus_terms.append(keyword)
    return focus_terms[:5]


def _split_sentences(text: str) -> List[str]:
    text = re.sub(r'\s+', ' ', text or '').strip()
    if not text:
        return []
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [part.strip() for part in parts if len(part.strip()) >= 20]


def _title_signal_phrase(title: str) -> str:
    terms = _content_terms(title)
    if terms:
        return "the problem of " + ", ".join(terms[:5])
    return "the research problem described by the manuscript title"


def _content_terms(text: str) -> List[str]:
    stopwords = {
        'the', 'and', 'for', 'with', 'using', 'from', 'into', 'onto', 'that',
        'this', 'these', 'those', 'study', 'analysis', 'based', 'across',
        'between', 'under', 'over', 'through', 'towards', 'toward', 'a', 'an',
        'of', 'in', 'on', 'to', 'by', 'is', 'are', 'be'
    }
    words = re.findall(r'[A-Za-z][A-Za-z-]{3,}', text or '')
    seen = set()
    terms = []
    for word in words:
        lowered = word.lower().strip('-')
        if lowered in stopwords or lowered in seen:
            continue
        seen.add(lowered)
        terms.append(lowered)
    return terms


def _trim_sentence(sentence: str, limit: int = 420) -> str:
    sentence = re.sub(r'\s+', ' ', sentence or '').strip()
    if len(sentence) <= limit:
        return sentence
    return sentence[:limit].rsplit(' ', 1)[0] + "..."


# 便捷函数
async def learn_and_suggest(
    journal_name: str,
    abstract: str,
    title: str = "",
) -> str:
    """
    学习期刊并给出摘要润色建议
    
    Args:
        journal_name: 期刊名称
        abstract: 原始摘要
        title: 论文标题
    
    Returns:
        str: 润色建议报告
    """
    learner = JournalLearner()
    journal_info = await learner.learn_journal(journal_name)
    return "\n\n".join([
        suggest_abstract_revision(abstract, journal_info, title),
        generate_reference_cover_letter(title, abstract, journal_info),
    ])
