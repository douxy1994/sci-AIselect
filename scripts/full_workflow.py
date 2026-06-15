"""
sci-aiselect 完整工作流

功能：
1. 从 Word/PDF 提取标题和摘要
2. Journal Finder 初筛（5个出版社）
3. AI 匹配（结合 Journal Finder 结果作为权重参考）
4. 提供 10 个综合选择
5. 意向期刊学习和摘要润色
6. 不满意时重新匹配
"""
from __future__ import annotations

import sys
import os
import re
from typing import Dict, List, Optional, Tuple

# 添加 scripts 目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from journal_finders import search_all_journal_finders
from journal_metrics import get_journal_metrics, format_metrics_line
from letpub_client import advanced_search


# ============================================================
# 文件提取功能
# ============================================================

def extract_from_file(file_path: str) -> Tuple[str, str, List[str]]:
    """
    从 Word 或 PDF 文件中提取标题、摘要和关键词
    
    Args:
        file_path: 文件路径
    
    Returns:
        Tuple[str, str, List[str]]: (标题, 摘要, 关键词)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return _extract_from_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        return _extract_from_word(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def _extract_from_pdf(file_path: str) -> Tuple[str, str, List[str]]:
    """从 PDF 文件提取"""
    try:
        import fitz  # pymupdf
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return _parse_paper_text(text)
    except ImportError:
        raise ImportError("需要安装 pymupdf: pip install pymupdf")


def _extract_from_word(file_path: str) -> Tuple[str, str, List[str]]:
    """从 Word 文件提取"""
    try:
        from docx import Document
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return _parse_paper_text(text)
    except ImportError:
        raise ImportError("需要安装 python-docx: pip install python-docx")


def _parse_paper_text(text: str) -> Tuple[str, str, List[str]]:
    """
    从论文文本中解析标题、摘要和关键词
    
    Args:
        text: 论文全文
    
    Returns:
        Tuple[str, str, List[str]]: (标题, 摘要, 关键词)
    """
    lines = text.strip().split('\n')
    
    title = ""
    abstract = ""
    keywords = []
    
    # 提取标题（通常是第一个非空行）
    for line in lines:
        line = line.strip()
        if line and len(line) > 10:
            title = line
            break
    
    # 提取摘要
    abstract_start = -1
    abstract_end = -1
    
    for i, line in enumerate(lines):
        line_lower = line.strip().lower()
        if 'abstract' in line_lower and len(line_lower) < 20:
            abstract_start = i + 1
        elif abstract_start > 0:
            if any(keyword in line_lower for keyword in ['keywords', 'key words', 'introduction', '1.', '1 ']):
                abstract_end = i
                break
    
    if abstract_start > 0:
        if abstract_end < 0:
            abstract_end = min(abstract_start + 30, len(lines))
        abstract = " ".join(lines[abstract_start:abstract_end]).strip()
    
    # 提取关键词
    for i, line in enumerate(lines):
        line_lower = line.strip().lower()
        if 'keywords' in line_lower or 'key words' in line_lower:
            # 提取关键词行
            keyword_text = line
            if ':' in keyword_text:
                keyword_text = keyword_text.split(':', 1)[1]
            elif '：' in keyword_text:
                keyword_text = keyword_text.split('：', 1)[1]
            
            # 分割关键词
            for sep in [',', ';', '，', '；', '·']:
                if sep in keyword_text:
                    keywords = [kw.strip() for kw in keyword_text.split(sep) if kw.strip()]
                    break
            
            if not keywords:
                keywords = [keyword_text.strip()]
            
            break
    
    return title, abstract, keywords


# ============================================================
# 论文特征推断
# ============================================================

def infer_paper_profile(text: str, max_categories: int = 4) -> Dict:
    """推断论文特征"""
    TERM_RULES = [
        {"label": "groundwater", "aliases": ["地下水", "groundwater", "aquifer"], "categories": [("环境科学与生态学", "水资源")], "weight": 4},
        {"label": "hydrology", "aliases": ["水文", "hydrology", "hydrological", "watershed", "catchment", "basin"], "categories": [("环境科学与生态学", "水资源")], "weight": 3},
        {"label": "glacial", "aliases": ["冰川", "glacial", "glacier", "ice"], "categories": [("地球科学", "自然地理学")], "weight": 4},
        {"label": "lake", "aliases": ["湖", "lake", "lacustrine"], "categories": [("环境科学与生态学", "水资源")], "weight": 3},
        {"label": "hazard", "aliases": ["灾害", "hazard", "risk", "disaster"], "categories": [("环境科学与生态学", "环境科学")], "weight": 3},
        {"label": "remote sensing", "aliases": ["遥感", "remote sensing", "satellite"], "categories": [("地球科学", "遥感")], "weight": 4},
        {"label": "climate change", "aliases": ["气候变化", "climate change", "global warming"], "categories": [("地球科学", "气象与大气科学")], "weight": 3},
        {"label": "himalaya", "aliases": ["喜马拉雅", "himalaya", "himalayan"], "categories": [("地球科学", "自然地理学")], "weight": 4},
        {"label": "geology", "aliases": ["地质", "geology", "geological"], "categories": [("地球科学", "地质学")], "weight": 3},
        {"label": "ecology", "aliases": ["生态", "ecology", "ecosystem"], "categories": [("环境科学与生态学", "生态学")], "weight": 3},
        {"label": "ocean", "aliases": ["海洋", "ocean", "marine"], "categories": [("地球科学", "海洋学")], "weight": 3},
        {"label": "atmosphere", "aliases": ["大气", "atmosphere", "atmospheric"], "categories": [("地球科学", "气象与大气科学")], "weight": 3},
        {"label": "water quality", "aliases": ["水质", "water quality", "pollution"], "categories": [("环境科学与生态学", "水资源")], "weight": 3},
        {"label": "sediment", "aliases": ["沉积", "sediment", "sedimentary"], "categories": [("地球科学", "地质学")], "weight": 3},
        {"label": "GIS", "aliases": ["GIS", "geographic information", "spatial analysis"], "categories": [("地球科学", "遥感")], "weight": 3},
    ]
    
    normalized = re.sub(r'\s+', ' ', (text or '').lower())
    category_scores = {}
    matched_terms = []
    
    for rule in TERM_RULES:
        hits = [alias for alias in rule["aliases"] if alias.lower() in normalized]
        if hits:
            matched_terms.append(rule["label"])
            for category in rule["categories"]:
                category_scores[category] = category_scores.get(category, 0) + rule["weight"]
    
    if not category_scores:
        category_scores[("综合性期刊", "")] = 1
    
    ranked_categories = sorted(category_scores.items(), key=lambda item: -item[1])
    categories = [
        {"category1": cat1, "category2": cat2, "score": score}
        for (cat1, cat2), score in ranked_categories[:max_categories]
    ]
    
    return {
        "categories": categories,
        "matched_terms": matched_terms,
        "methods": [],
        "input_length": len(text or ""),
    }


# ============================================================
# 期刊指标获取和排序
# ============================================================

def get_journal_metrics_safe(name: str) -> Dict:
    """安全获取期刊指标"""
    try:
        metrics = get_journal_metrics(name)
        return metrics
    except Exception as e:
        return {
            'name': name,
            '_sources': [],
            '_source_errors': {'all': str(e)},
        }


def rank_metric_records(profile: Dict, records: List[Dict], finder_results: List[Dict] = None) -> List[Dict]:
    """
    评分和排序期刊记录
    
    Args:
        profile: 论文特征
        records: 期刊指标记录
        finder_results: Journal Finder 结果（用于权重参考）
    """
    # 创建 Journal Finder 结果的查找表
    finder_lookup = {}
    if finder_results:
        for r in finder_results:
            name_lower = r['journal_name'].lower()
            finder_lookup[name_lower] = r
    
    ranked = []
    
    for record in records:
        entry = dict(record)
        name = entry.get('name', '')
        name_lower = name.lower()
        
        # 计算 fit_score
        fit_score = 0
        
        # 1. 基于 Journal Finder 结果的权重
        if name_lower in finder_lookup:
            finder_score = finder_lookup[name_lower].get('match_score', 0)
            fit_score += finder_score * 30  # 最高 30 分
        
        # 2. 基于主题匹配
        matched_terms = profile.get('matched_terms', [])
        field = str(entry.get('field', '')).lower()
        for term in matched_terms:
            if term.lower() in field:
                fit_score += 5
        
        # 3. 基于分类匹配
        for category in profile.get('categories', []):
            cat1 = category.get('category1', '').lower()
            cat2 = category.get('category2', '').lower()
            if cat1 in field or cat2 in field:
                fit_score += 10
        
        # 计算 quality_score
        quality_score = 0
        impact_factor = float(entry.get('impact_factor', 0) or 0)
        partition = str(entry.get('partition', ''))
        
        if '1区' in partition:
            quality_score += 18
        elif '2区' in partition:
            quality_score += 13
        elif '3区' in partition:
            quality_score += 7
        elif '4区' in partition:
            quality_score += 3
        
        if impact_factor >= 20:
            quality_score += 15
        elif impact_factor >= 10:
            quality_score += 12
        elif impact_factor >= 5:
            quality_score += 9
        elif impact_factor >= 3:
            quality_score += 5
        elif impact_factor > 0:
            quality_score += 2
        
        h_index = float(entry.get('h_index', 0) or 0)
        if h_index >= 200:
            quality_score += 8
        elif h_index >= 100:
            quality_score += 5
        elif h_index >= 50:
            quality_score += 3
        
        # 计算 risk_penalty
        risk_penalty = 0
        if entry.get('warning'):
            risk_penalty += 60
        
        sci = str(entry.get('sci_type', '')).upper()
        if 'ESCI' in sci:
            risk_penalty += 10
        elif not sci and 'letpub' in entry.get('_sources', []):
            risk_penalty += 30
        
        # 总分
        total_score = fit_score + quality_score - risk_penalty
        
        entry['fit_score'] = fit_score
        entry['quality_score'] = quality_score
        entry['risk_penalty'] = risk_penalty
        entry['score'] = total_score
        entry['metrics_line'] = format_metrics_line(entry)
        
        # 来源信息
        sources = []
        if name_lower in finder_lookup:
            sources.append(f"journal_finder: {finder_lookup[name_lower].get('source', '')}")
        if entry.get('_sources'):
            sources.extend(entry['_sources'])
        entry['data_sources'] = sources
        
        # 确定 tier
        if entry.get('warning'):
            entry['tier'] = '不推荐'
        elif total_score >= 50 and fit_score >= 15:
            entry['tier'] = '推荐'
        elif total_score >= 35 and fit_score >= 10:
            entry['tier'] = '备选'
        elif total_score >= 20:
            entry['tier'] = '谨慎'
        else:
            entry['tier'] = '不推荐'
        
        ranked.append(entry)
    
    # 排序
    tier_order = {"推荐": 0, "备选": 1, "谨慎": 2, "不推荐": 3}
    ranked.sort(key=lambda item: (tier_order.get(item["tier"], 9), -item["score"]))
    
    return ranked


def assign_submission_bands(ranked: List[Dict]) -> List[Dict]:
    """分配投稿梯度"""
    for item in ranked:
        if item.get("tier") in ("不推荐", "谨慎"):
            item["submission_band"] = "谨慎"
        elif item.get("warning"):
            item["submission_band"] = "谨慎"
        else:
            partition = str(item.get("partition", ""))
            impact = float(item.get("impact_factor", 0) or 0)
            
            if "1区" in partition or impact >= 10:
                item["submission_band"] = "冲刺"
            elif "2区" in partition or impact >= 5:
                item["submission_band"] = "稳妥"
            else:
                item["submission_band"] = "保底"
    
    return ranked


# ============================================================
# 格式化输出
# ============================================================

def format_selection_matrix(profile: Dict, ranked: List[Dict]) -> str:
    """格式化决策表"""
    lines = [
        "## 快速决策表",
        "",
        "| 期刊 | 建议 | 梯度 | IF | 分区 | 收录 |",
        "|---|---|---|---:|---|---|",
    ]
    
    for item in ranked:
        name = str(item.get('name', '-')).replace('|', '/').replace('\n', ' ')
        if len(name) > 40:
            name = name[:37] + "..."
        tier = item.get('tier', '')
        band = item.get('submission_band', '待定')
        impact = item.get('impact_factor') or '-'
        partition = item.get('partition') or '-'
        sci = item.get('sci_type') or '-'
        
        lines.append(f"| {name} | {tier} | {band} | {impact} | {partition} | {sci} |")
    
    return "\n".join(lines)


def format_full_report(
    bundle: Dict,
    title: str = "",
    show_finder_results: bool = True,
) -> str:
    """生成完整的报告"""
    lines = []
    
    # 标题
    if title:
        lines.append(f"# sci-aiselect 选刊建议：{title}")
    else:
        lines.append("# sci-aiselect 选刊建议")
    lines.append("")
    
    # Journal Finder 结果
    if show_finder_results and bundle.get('finder_results'):
        lines.append("## Journal Finder 初筛结果")
        lines.append("")
        
        by_source = {}
        for r in bundle['finder_results']:
            source = r['source']
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(r)
        
        for source, journals in by_source.items():
            lines.append(f"### {source}")
            for i, j in enumerate(journals[:10], 1):
                lines.append(f"{i}. {j['journal_name']} (匹配度: {j['match_score']:.2f})")
            lines.append("")
    
    # AI 匹配结果
    lines.append("## AI 智能匹配结果")
    lines.append("")
    
    profile = bundle.get('profile', {})
    category_text = "；".join(
        f"{c['category1']}/{c['category2'] or '综合'}" for c in profile.get("categories", [])
    )
    if category_text:
        lines.append(f"**识别方向**：{category_text}")
    
    terms = "、".join(profile.get("matched_terms", [])[:8])
    if terms:
        lines.append(f"**命中主题**：{terms}")
    
    lines.append("")
    
    # 决策表
    lines.append(format_selection_matrix(profile, bundle['results']))
    lines.append("")
    
    # 详细推荐
    tier_icons = {"推荐": "推荐", "备选": "备选", "谨慎": "谨慎", "不推荐": "不推荐"}
    for idx, item in enumerate(bundle['results'], 1):
        band = item.get("submission_band", "待定")
        lines.append(f"## {idx}. {item.get('name', '未知期刊')}｜{band}｜{tier_icons.get(item['tier'], item['tier'])}")
        lines.append(f"**指标**：{item.get('metrics_line') or format_metrics_line(item)}")
        
        # 来源信息
        source_info = []
        if item.get('data_sources'):
            source_info.append(f"来源: {', '.join(item['data_sources'])}")
        if source_info:
            lines.append(f"**来源**：{'；'.join(source_info)}")
        
        lines.append("")
    
    return "\n".join(lines).strip()


# ============================================================
# 主工作流
# ============================================================

def select_journals_with_finder(
    title: str,
    abstract: str,
    keywords: List[str] = None,
    use_journal_finders: bool = True,
    finder_config: Dict = None,
    impact_low: str = "3",
    max_candidates: int = 10,
) -> Dict:
    """
    完整的期刊选择流程
    
    Args:
        title: 论文标题
        abstract: 论文摘要
        keywords: 关键词列表
        use_journal_finders: 是否使用 Journal Finder 初筛
        finder_config: Journal Finder 配置
        impact_low: 最低影响因子
        max_candidates: 最大候选数量
    
    Returns:
        Dict: 包含 profile, results, finder_results
    """
    # 构建论文文本
    paper_text = title + "\n" + abstract
    if keywords:
        paper_text += "\n关键词：" + ", ".join(keywords)
    
    # 步骤 1: Journal Finder 初筛
    finder_results = []
    if use_journal_finders:
        print("\n" + "="*70)
        print("步骤 1: Journal Finder 初筛")
        print("="*70)
        
        default_config = {
            'timeout': 90000,
            'retry_count': 1,
            'elsevier': {'enabled': True},
            'wiley': {'enabled': True},
            'taylor_francis': {'enabled': True},
            'springer': {'enabled': True},
            'wos': {'enabled': True},
        }
        
        if finder_config:
            default_config.update(finder_config)
        
        finder_results = search_all_journal_finders(title, abstract, keywords, default_config)
        
        print(f"\nJournal Finder 共找到 {len(finder_results)} 个期刊")
        
        # 按来源分组显示
        by_source = {}
        for r in finder_results:
            source = r['source']
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(r)
        
        for source, journals in by_source.items():
            print(f"\n{source}: {len(journals)} 个期刊")
            for j in journals[:5]:
                print(f"  - {j['journal_name']} (匹配度: {j['match_score']:.2f})")
    
    # 步骤 2: AI 智能匹配
    print("\n" + "="*70)
    print("步骤 2: AI 智能匹配")
    print("="*70)
    
    # 推断论文特征
    profile = infer_paper_profile(paper_text)
    
    print("\n论文特征:")
    category_text = ", ".join([c["category1"] + "/" + c["category2"] for c in profile['categories']])
    print("  识别方向: " + category_text)
    print("  命中主题: " + ", ".join(profile['matched_terms']))
    
    # 获取 Journal Finder 期刊的指标
    print("\n正在获取期刊指标...")
    metric_records = []
    
    # 收集所有候选期刊名称
    candidate_names = set()
    
    # 1. Journal Finder 结果
    for finder_result in finder_results:
        candidate_names.add(finder_result['journal_name'])
    
    # 2. 基于 LetPub 搜索的候选
    print("正在搜索 LetPub 候选期刊...")
    for category in profile['categories'][:3]:
        try:
            results = advanced_search(
                searchcategory1=category.get('category1', ''),
                searchcategory2=category.get('category2', ''),
                searchimpactlow=impact_low,
                searchscitype='SCIE',
                searchsort='impactor',
            )
            for journal in results.get('journals', [])[:5]:
                name = journal.get('name', '')
                if name:
                    candidate_names.add(name)
        except Exception as e:
            print(f"  LetPub 搜索失败: {e}")
    
    # 获取所有候选期刊的指标
    print(f"\n正在获取 {len(candidate_names)} 个候选期刊的指标...")
    for name in candidate_names:
        metrics = get_journal_metrics_safe(name)
        if metrics.get('_sources'):
            metric_records.append(metrics)
    
    # 排序和分带
    print("\n正在进行智能排序...")
    ranked = assign_submission_bands(rank_metric_records(profile, metric_records, finder_results))
    
    # 限制结果数量
    ranked = ranked[:max_candidates]
    
    return {
        'profile': profile,
        'results': ranked,
        'finder_results': finder_results,
    }


# ============================================================
# 便捷函数
# ============================================================

def quick_select(title: str, abstract: str, keywords: List[str] = None) -> str:
    """快速选刊"""
    bundle = select_journals_with_finder(title, abstract, keywords)
    return format_full_report(bundle, title=title)


def extract_and_select(file_path: str) -> str:
    """
    从文件提取并选刊
    
    Args:
        file_path: Word 或 PDF 文件路径
    
    Returns:
        str: 格式化的报告
    """
    title, abstract, keywords = extract_from_file(file_path)
    
    print(f"提取的标题: {title[:50]}...")
    print(f"提取的摘要: {abstract[:100]}...")
    print(f"提取的关键词: {keywords}")
    
    bundle = select_journals_with_finder(title, abstract, keywords)
    return format_full_report(bundle, title=title)
