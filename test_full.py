#!/usr/bin/env python3
"""
sci-aiselect 完整测试脚本

测试 Journal Finder 和 AI 匹配功能
"""
import sys
import os
import json

# 添加 scripts 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from journal_finders import search_all_journal_finders


def test_paper():
    """测试论文"""
    title = "Glacial lake systems are redefining risk in a changing Himalayan cryosphere"
    abstract = """Glacial lakes are expanding rapidly across the Himalaya in response to ongoing climate warming, with important implications for downstream hazard systems. This study integrates multi-decadal satellite observations with published datasets to assess the evolution of 36 potentially dangerous glacial lakes across the Indian Himalayan Region, covering the period from the late twentieth century to the present decade. The results show widespread but spatially variable lake expansion, with several lakes exhibiting accelerated and non-linear growth linked to glacier–lake interactions and basin characteristics. Beyond lake dynamics, the analysis highlights the influence of sediment processes, transboundary settings, and compound hazard interactions in shaping GLOF risk, along with the increasing vulnerability of downstream hydropower infrastructure to such extreme events. A synthesis of existing studies further reveals inconsistencies in PDGL identification, limited availability of bathymetric data, and key observational gaps in current monitoring approaches. These findings indicate that glacial lake hazards in the Himalaya are evolving within complex and interconnected systems that are not adequately captured by existing frameworks, underscoring the need for more integrated approaches to hazard assessment and risk management."""
    
    keywords = ["glacial lakes", "GLOF", "Himalaya", "climate change", "hazard assessment", "remote sensing"]
    
    return title, abstract, keywords


def test_journal_finders(title: str, abstract: str, keywords: list, finders: list = None):
    """测试 Journal Finder"""
    print("\n" + "="*70)
    print("步骤 1: Journal Finder 初筛")
    print("="*70)
    
    config = {
        'timeout': 60000,
        'retry_count': 1,
    }
    
    if finders:
        # 只启用指定的 finders
        for f in ['elsevier', 'wiley', 'taylor_francis', 'springer', 'wos']:
            config[f] = {'enabled': f in finders}
    
    results = search_all_journal_finders(title, abstract, keywords, config)
    
    print(f"\n共找到 {len(results)} 个期刊")
    
    if results:
        print("\n前 10 个结果:")
        for i, result in enumerate(results[:10], 1):
            print(f"{i}. {result['journal_name']}")
            print(f"   来源: {result['source']}, 匹配度: {result['match_score']:.2f}")
    
    return results


def main():
    """主函数"""
    print("\n" + "="*70)
    print("sci-aiselect 完整测试")
    print("="*70)
    
    # 获取测试论文
    title, abstract, keywords = test_paper()
    
    print(f"\n论文标题: {title}")
    print(f"关键词: {', '.join(keywords)}")
    
    # 选择要测试的 Journal Finder
    print("\n请选择要测试的 Journal Finder:")
    print("1. 全部 (elsevier, wiley, taylor_francis, springer, wos)")
    print("2. 仅 Elsevier")
    print("3. 仅 Wiley")
    print("4. 仅 Taylor & Francis")
    print("5. 仅 Springer")
    print("6. 仅 WOS")
    print("7. 跳过 Journal Finder")
    
    choice = input("\n请输入选项 (1-7): ").strip()
    
    finders = None
    skip_finders = False
    
    if choice == '2':
        finders = ['elsevier']
    elif choice == '3':
        finders = ['wiley']
    elif choice == '4':
        finders = ['taylor_francis']
    elif choice == '5':
        finders = ['springer']
    elif choice == '6':
        finders = ['wos']
    elif choice == '7':
        skip_finders = True
    
    # 测试 Journal Finder
    finder_results = []
    if not skip_finders:
        finder_results = test_journal_finders(title, abstract, keywords, finders)
    
    # 保存结果
    output_file = os.path.join(os.path.dirname(__file__), 'test_results.json')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'title': title,
            'abstract': abstract[:200] + '...',
            'keywords': keywords,
            'finder_results': finder_results[:20],
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_file}")
    
    print("\n" + "="*70)
    print("测试完成")
    print("="*70)


if __name__ == '__main__':
    main()
