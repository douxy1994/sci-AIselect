"""
多源期刊指标聚合器
数据源：LetPub（IF/分区/审稿速度/SCI收录）+ OpenAlex（h-index/OA/APC）
使用公开页面和 OpenAlex 获取基础指标
"""
import requests
import time
import json
import os
import re
from typing import Dict, Optional, List, Any

try:
    from .letpub_client import lookup_journal
except ImportError:
    from letpub_client import lookup_journal

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets')
CACHE_FILE = os.path.join(CACHE_DIR, 'journal_cache.json')
FX_CACHE_FILE = os.path.join(CACHE_DIR, 'exchange_rate_cache.json')
CACHE_TTL = 7 * 86400  # 7天
FX_CACHE_TTL = 86400  # 1天


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _get_letpub_info(journal_name: str) -> Optional[Dict]:
    """从 LetPub 获取期刊详情"""
    try:
        return lookup_journal(journal_name)
    except Exception as e:
        print(f"LetPub 查询失败 [{journal_name}]: {e}")
        return None


def _get_openalex_info(journal_name: str, issn: str = None) -> Optional[Dict]:
    """从 OpenAlex 获取期刊指标"""
    try:
        # 优先用 ISSN 搜索（更精确）
        if issn:
            url = f"https://api.openalex.org/sources?filter=issn:{issn}&per_page=1"
        else:
            url = f"https://api.openalex.org/sources?search={requests.utils.quote(journal_name)}&per_page=1"

        resp = requests.get(url, timeout=15)
        data = resp.json()
        results = data.get('results', [])
        if not results:
            return None

        source = results[0]
        if not _openalex_source_matches(source, journal_name, issn):
            return None

        stats = source.get('summary_stats', {})

        return {
            'openalex_id': source.get('id', ''),
            'h_index': stats.get('h_index'),
            'i10_index': stats.get('i10_index'),
            '2yr_mean_citedness': round(stats.get('2yr_mean_citedness', 0), 2),
            'cited_by_count': source.get('cited_by_count'),
            'works_count': source.get('works_count'),
            'oa_works_count': source.get('oa_works_count'),
            'is_oa': source.get('is_oa'),
            'is_in_doaj': source.get('is_in_doaj'),
            'apc_prices': source.get('apc_prices') or [],
            'apc_usd': source.get('apc_usd') or _extract_apc_usd(source.get('apc_prices', [])),
            'host_organization': source.get('host_organization_name', ''),
            'country': source.get('country_code', ''),
        }
    except Exception as e:
        print(f"OpenAlex 查询失败 [{journal_name}]: {e}")
        return None


def _extract_apc_usd(apc_prices: list) -> Optional[int]:
    """从 apc_prices 提取 USD 价格"""
    for p in apc_prices:
        if p.get('currency') == 'USD':
            return p.get('price')
    return None


def _get_doaj_info(journal_name: str, issn: str = None) -> Optional[Dict]:
    """Fetch DOAJ journal metadata, including APC fields when present."""
    queries = []
    if issn:
        queries.append(issn)
    queries.append(journal_name)

    for query in queries:
        try:
            resp = requests.get(
                f"https://doaj.org/api/v4/search/journals/{requests.utils.quote(query)}",
                headers={"accept": "application/json", **HEADERS_FOR_PUBLIC_APIS},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"DOAJ 查询失败 [{journal_name}]: {e}")
            continue

        for result in data.get('results', [])[:10]:
            bibjson = result.get('bibjson', {}) or {}
            if not _doaj_record_matches(bibjson, journal_name, issn):
                continue
            apc = bibjson.get('apc', {}) or {}
            return {
                'doaj_id': result.get('id', ''),
                'doaj_title': bibjson.get('title', ''),
                'doaj_apc': apc,
                'doaj_apc_url': apc.get('url', ''),
                'doaj_publication_time_weeks': bibjson.get('publication_time_weeks'),
                'doaj_waiver': bibjson.get('waiver', {}),
                'doaj_is_oa': True,
            }

    return None


def _openalex_source_matches(source: Dict, journal_name: str, issn: str = None) -> bool:
    """Return True when an OpenAlex source plausibly matches the requested journal."""
    if issn:
        target_issn = _normalize_issn(issn)
        source_issns = [
            _normalize_issn(value)
            for value in [source.get('issn_l'), *_as_list(source.get('issn'))]
            if value
        ]
        if target_issn and target_issn in source_issns:
            return True

    target_name = _normalize_source_name(journal_name)
    source_names = [
        _normalize_source_name(value)
        for value in [source.get('display_name'), *_as_list(source.get('alternate_titles'))]
        if value
    ]
    return bool(target_name and any(target_name == name for name in source_names))


def _doaj_record_matches(bibjson: Dict, journal_name: str, issn: str = None) -> bool:
    if issn:
        target_issn = _normalize_issn(issn)
        record_issns = [
            _normalize_issn(value)
            for value in [bibjson.get('pissn'), bibjson.get('eissn'), *_as_list(bibjson.get('issn'))]
            if value
        ]
        if target_issn and target_issn in record_issns:
            return True

    target_name = _normalize_source_name(journal_name)
    title = _normalize_source_name(bibjson.get('title', ''))
    return bool(target_name and target_name == title)


def _as_list(value) -> List:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_issn(value: str) -> str:
    return re.sub(r'[^0-9Xx]', '', str(value or '')).upper()


def _normalize_source_name(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def get_journal_metrics(journal_name: str, use_cache: bool = True) -> Dict:
    """
    聚合多源期刊公开指标

    Returns:
        {
            'name': 期刊名,
            'shortname': 简称,
            'issn': ISSN,
            # 来自 LetPub
            'impact_factor': 影响因子,
            'partition': 中科院分区（如 '1区'）,
            'partition_detail': {'大类': ..., '小类': ..., 'Top': ...},
            'sci_type': SCIE/ESCI/无,
            'speed': 审稿速度,
            'accept': 录用比例,
            'warning': 是否预警,
            'publisher_letpub': 出版商(LetPub),
            'field': 研究方向,
            # 来自 OpenAlex
            'h_index': h指数,
            '2yr_mean_citedness': 2年平均被引（类IF）,
            'cited_by_count': 总被引,
            'works_count': 总论文数,
            'is_oa': 是否OA,
            'apc_usd': 文章处理费(USD),
            'publisher_oa': 出版商(OpenAlex),
            # 来源标记
            '_sources': ['letpub', 'openalex'],
        }
    """
    cache = _load_cache()

    # 检查缓存
    if use_cache and journal_name in cache:
        cached = cache[journal_name]
        cached_sources = set(cached.get('_sources', []))
        is_complete = {'letpub', 'openalex'}.issubset(cached_sources) and not cached.get('_source_errors')
        if is_complete and time.time() - cached.get('_cached_at', 0) < CACHE_TTL:
            annotate_review_cycle(cached)
            annotate_apc(cached)
            return cached

    result = {'name': journal_name, '_sources': [], '_source_errors': {}, '_cached_at': time.time()}

    # 1. LetPub
    letpub = _get_letpub_info(journal_name)
    if letpub:
        result.update({
            'shortname': letpub.get('shortname', ''),
            'issn': letpub.get('issn', ''),
            'impact_factor': letpub.get('impact_factor'),
            'partition': _extract_partition(letpub),
            'partition_detail': letpub.get('ch_sci_2025'),
            'sci_type': letpub.get('_sci_type', ''),
            'speed': letpub.get('speed', ''),
            'accept': letpub.get('accept', ''),
            'apc_letpub_usd': letpub.get('oa_price'),
            'warning': letpub.get('warning', False),
            'publisher_letpub': letpub.get('publisher', ''),
            'field': letpub.get('field', ''),
        })
        result['_sources'].append('letpub')
        time.sleep(1)  # LetPub 请求间隔
    else:
        result['_source_errors']['letpub'] = 'not found or request failed'

    # 2. DOAJ（用于 APC 与 OA 元数据；失败不阻断完整缓存）
    issn = result.get('issn', '')
    doaj = _get_doaj_info(journal_name, issn if issn else None)
    if doaj:
        result.update({
            'doaj_id': doaj.get('doaj_id', ''),
            'doaj_title': doaj.get('doaj_title', ''),
            'doaj_apc': doaj.get('doaj_apc', {}),
            'doaj_apc_url': doaj.get('doaj_apc_url', ''),
            'doaj_publication_time_weeks': doaj.get('doaj_publication_time_weeks'),
            'doaj_waiver': doaj.get('doaj_waiver', {}),
            'is_in_doaj': True,
            'is_oa': True if result.get('is_oa') is None else result.get('is_oa'),
        })
        result['_sources'].append('doaj')
    else:
        result.setdefault('_apc_source_errors', {})['doaj'] = 'not found or request failed'

    # 3. OpenAlex（用 ISSN 或名称）
    openalex = _get_openalex_info(journal_name, issn if issn else None)
    if openalex:
        result.update({
            'h_index': openalex.get('h_index'),
            '2yr_mean_citedness': openalex.get('2yr_mean_citedness'),
            'cited_by_count': openalex.get('cited_by_count'),
            'works_count': openalex.get('works_count'),
            'oa_works_count': openalex.get('oa_works_count'),
            'is_oa': openalex.get('is_oa') if openalex.get('is_oa') is not None else result.get('is_oa'),
            'is_in_doaj': openalex.get('is_in_doaj'),
            'apc_prices': openalex.get('apc_prices', []),
            'apc_usd': openalex.get('apc_usd'),
            'publisher_oa': openalex.get('host_organization', ''),
        })
        result['_sources'].append('openalex')
    else:
        result['_source_errors']['openalex'] = 'not found or request failed'

    # 只缓存完整结果，避免一次临时网络失败污染后续推荐。
    annotate_review_cycle(result)
    annotate_apc(result)
    if result['_sources'] and not result['_source_errors']:
        cache[journal_name] = result
        _save_cache(cache)

    return result


HEADERS_FOR_PUBLIC_APIS = {
    "user-agent": "sci-aiselect/1.0 (journal selection assistant)",
}


def annotate_apc(record: Dict) -> Dict:
    """Attach APC amount, source, and live CNY conversion when data is available."""
    apc_info = resolve_apc_info(record)
    record.update(apc_info)
    return record


def resolve_apc_info(record: Dict) -> Dict:
    """Resolve APC with source priority: official/LetPub detail, DOAJ, then OpenAlex."""
    info = {
        'apc_amount': None,
        'apc_currency': '',
        'apc_cny': None,
        'apc_source': '',
        'apc_source_url': '',
        'apc_note': 'APC未获取',
        'apc_rate': None,
        'apc_rate_date': '',
    }

    letpub_usd = _to_float_or_none(record.get('apc_letpub_usd'))
    if letpub_usd is not None and letpub_usd > 0:
        info.update({
            'apc_amount': letpub_usd,
            'apc_currency': 'USD',
            'apc_source': 'LetPub详情/期刊页',
            'apc_note': '',
        })
        return _attach_cny_conversion(info)

    doaj_apc = record.get('doaj_apc') or {}
    if doaj_apc:
        if doaj_apc.get('has_apc') is False:
            info.update({
                'apc_amount': 0,
                'apc_currency': 'CNY',
                'apc_cny': 0,
                'apc_source': 'DOAJ',
                'apc_source_url': doaj_apc.get('url') or record.get('doaj_apc_url', ''),
                'apc_note': 'DOAJ标记无APC',
            })
            return info

        price = _best_doaj_apc_price(doaj_apc)
        if price:
            info.update({
                'apc_amount': price.get('price'),
                'apc_currency': str(price.get('currency') or '').upper(),
                'apc_source': 'DOAJ',
                'apc_source_url': doaj_apc.get('url') or record.get('doaj_apc_url', ''),
                'apc_note': '',
            })
            return _attach_cny_conversion(info)

    openalex_price = _best_openalex_apc_price(record)
    if openalex_price:
        info.update({
            'apc_amount': openalex_price.get('price'),
            'apc_currency': str(openalex_price.get('currency') or '').upper(),
            'apc_source': 'OpenAlex',
            'apc_note': '',
        })
        return _attach_cny_conversion(info)

    apc_usd = _to_float_or_none(record.get('apc_usd'))
    if apc_usd is not None and apc_usd > 0:
        info.update({
            'apc_amount': apc_usd,
            'apc_currency': 'USD',
            'apc_source': 'OpenAlex',
            'apc_note': '',
        })
        return _attach_cny_conversion(info)

    return info


def format_apc_line(record: Dict) -> str:
    """Format APC with original currency, CNY estimate, and source."""
    if not record.get('apc_source') and 'apc_amount' not in record:
        annotate_apc(record)

    amount = record.get('apc_amount')
    source = record.get('apc_source') or '未获取'
    note = record.get('apc_note', '')
    if amount is None:
        return note or 'APC未获取'
    if amount == 0:
        return f"无APC（{source}）"

    currency = record.get('apc_currency') or ''
    original = f"{currency} {int(amount) if float(amount).is_integer() else amount}"
    cny = record.get('apc_cny')
    if cny is not None:
        rate_date = record.get('apc_rate_date')
        date_part = f"，汇率日 {rate_date}" if rate_date else ''
        return f"{original}，约 RMB {int(round(cny))}（{source}{date_part}）"
    return f"{original}（{source}；人民币汇率未获取）"


def _best_doaj_apc_price(apc: Dict) -> Optional[Dict]:
    prices = apc.get('max') or apc.get('price') or []
    if isinstance(prices, dict):
        prices = [prices]
    return _first_price(prices)


def _best_openalex_apc_price(record: Dict) -> Optional[Dict]:
    prices = record.get('apc_prices') or []
    if prices:
        return _first_price(prices)
    if record.get('apc_usd'):
        return {'price': record.get('apc_usd'), 'currency': 'USD'}
    return None


def _first_price(prices: List[Dict]) -> Optional[Dict]:
    valid = [
        {'price': _to_float_or_none(p.get('price')), 'currency': str(p.get('currency') or '').upper()}
        for p in prices
        if isinstance(p, dict)
    ]
    valid = [p for p in valid if p['price'] is not None and p['currency']]
    if not valid:
        return None
    for p in valid:
        if p['currency'] == 'USD':
            return p
    return valid[0]


def _attach_cny_conversion(info: Dict) -> Dict:
    amount = _to_float_or_none(info.get('apc_amount'))
    currency = str(info.get('apc_currency') or '').upper()
    if amount is None:
        return info
    if amount == 0 or currency == 'CNY':
        info['apc_cny'] = amount
        info['apc_rate'] = 1
        return info

    rate_info = _get_cny_rate(currency)
    if rate_info:
        info['apc_rate'] = rate_info.get('rate')
        info['apc_rate_date'] = rate_info.get('date', '')
        info['apc_cny'] = round(amount * rate_info['rate'], 2)
    return info


def _get_cny_rate(currency: str) -> Optional[Dict]:
    currency = str(currency or '').upper()
    if not currency:
        return None
    if currency == 'CNY':
        return {'rate': 1.0, 'date': ''}

    cache = _load_json(FX_CACHE_FILE)
    cache_key = f"{currency}_CNY"
    cached = cache.get(cache_key)
    if cached and time.time() - cached.get('_cached_at', 0) < FX_CACHE_TTL:
        return cached

    try:
        resp = requests.get(
            "https://api.frankfurter.dev/v2/rates",
            params={"base": currency, "quotes": "CNY"},
            headers=HEADERS_FOR_PUBLIC_APIS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            row = data[0]
            rate = row.get('rate')
            date = row.get('date', '')
        else:
            rates = data.get('rates', {}) if isinstance(data, dict) else {}
            rate = rates.get('CNY') or data.get('rate') if isinstance(data, dict) else None
            date = data.get('date', '') if isinstance(data, dict) else ''
        if not rate:
            return None
        cache[cache_key] = {'rate': float(rate), 'date': date, '_cached_at': time.time()}
        _save_json(FX_CACHE_FILE, cache)
        return cache[cache_key]
    except Exception as e:
        print(f"汇率查询失败 [{currency}->CNY]: {e}")
        return None


def _load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def annotate_review_cycle(record: Dict) -> Dict:
    """Attach structured review-cycle metadata parsed from LetPub or journal-site text."""
    cycle = parse_review_cycle(record.get('speed', ''))
    record['review_cycle'] = cycle
    record['review_cycle_days'] = cycle.get('overall_days')
    record['review_cycle_source'] = cycle.get('source', '')
    return record


def parse_review_cycle(speed_text: str) -> Dict:
    """
    Parse LetPub/journal-site review timing text into comparable day counts.

    Priority:
    1. Official journal-site fields such as submission-to-acceptance.
    2. Official publisher averages such as Elsevier "平均19.9周".
    3. LetPub user-shared averages and ranges.
    """
    raw = str(speed_text or '').strip()
    cycle = {
        'raw': raw,
        'source': '',
        'first_decision_days': None,
        'review_days': None,
        'acceptance_days': None,
        'publication_days': None,
        'overall_days': None,
        'submission_to_publication_days': None,
        'label': _short_review_label(raw),
    }
    if not raw:
        return cycle

    text = raw.replace('；', ';')
    official = bool(re.search(r'(期刊官网数据|来源[^;；:：]{0,20}官网|time to first decision|review time|submission to acceptance)', text, re.I))
    label_map = [
        ('first_decision_days', r'time\s+to\s+first\s+decision'),
        ('review_days', r'review\s+time'),
        ('acceptance_days', r'(?:submission\s+to\s+acceptance|time\s+to\s+acceptance)'),
        ('publication_days', r'acceptance\s+to\s+publication'),
    ]
    for key, label_pattern in label_map:
        pattern = label_pattern + r'\s*[:：]?\s*(\d+(?:\.\d+)?)\s*([a-zA-Z\u4e00-\u9fff]*)'
        match = re.search(pattern, text, flags=re.I)
        if match:
            cycle[key] = _duration_to_days(float(match.group(1)), match.group(2) or 'days')

    official_average = re.search(
        r'来源[^;；:：]{0,20}官网\s*[:：]\s*平均?\s*(\d+(?:\.\d+)?)\s*(weeks?|周|个月|月|days?|天)',
        text,
        flags=re.I,
    )
    official_average_days = None
    if official_average:
        official_average_days = _duration_to_days(float(official_average.group(1)), official_average.group(2))

    user_average_days = _extract_user_review_days(text)

    if cycle['acceptance_days'] is not None:
        cycle['overall_days'] = cycle['acceptance_days']
    elif cycle['review_days'] is not None:
        cycle['overall_days'] = cycle['review_days']
    elif official_average_days is not None:
        cycle['overall_days'] = official_average_days
    elif user_average_days is not None:
        cycle['overall_days'] = user_average_days

    if cycle['overall_days'] is not None and cycle['publication_days'] is not None:
        cycle['submission_to_publication_days'] = cycle['overall_days'] + cycle['publication_days']

    if official and cycle['overall_days'] is not None:
        cycle['source'] = 'journal_official'
    elif user_average_days is not None:
        cycle['source'] = 'letpub_user'

    return cycle


def score_review_speed(record: Dict, enabled: bool = False) -> int:
    """Return an optional ranking adjustment for users who explicitly prefer fast review."""
    if not enabled:
        return 0

    cycle = record.get('review_cycle') or parse_review_cycle(record.get('speed', ''))
    days = cycle.get('submission_to_publication_days') or cycle.get('overall_days')
    if days is None:
        return -3
    if days <= 45:
        return 14
    if days <= 75:
        return 10
    if days <= 120:
        return 6
    if days <= 180:
        return 0
    if days <= 270:
        return -6
    return -12


def format_review_cycle(record: Dict) -> str:
    """Format structured review-cycle metadata for reports."""
    cycle = record.get('review_cycle') or parse_review_cycle(record.get('speed', ''))
    if not cycle.get('raw'):
        return '未获取'

    parts = []
    if cycle.get('first_decision_days') is not None:
        parts.append(f"初审约{_format_days(cycle['first_decision_days'])}")
    if cycle.get('overall_days') is not None:
        parts.append(f"整体约{_format_days(cycle['overall_days'])}")
    if cycle.get('publication_days') is not None:
        parts.append(f"接收后见刊约{_format_days(cycle['publication_days'])}")
    if not parts:
        return cycle.get('label') or '有审稿速度文本，需人工复核'

    source = cycle.get('source')
    source_label = '官网' if source == 'journal_official' else 'LetPub网友'
    return f"{'；'.join(parts)}（{source_label}）"


def review_preference_enabled(value: Any) -> bool:
    """Normalize explicit user preference for fast review/acceptance/publication."""
    if isinstance(value, bool):
        return value
    text = str(value or '').lower()
    return bool(re.search(r'(快审|审稿周期短|审稿快|尽快|快速接收|快速见刊|接收见刊|fast|quick|short review|rapid|speed)', text))


def has_wos_on_hold_status(record: Dict) -> bool:
    """Detect Clarivate/Web of Science On Hold status. Matching records must be excluded."""
    if not record:
        return False
    if record.get('wos_on_hold') is True or record.get('on_hold') is True:
        return True
    return _contains_wos_on_hold_text(record)


def _extract_user_review_days(text: str) -> Optional[int]:
    user_segment = text
    if '网友分享经验' in text:
        user_segment = text.split('网友分享经验', 1)[1]
    user_segment = re.split(r'来源[^;；:：]{0,20}官网', user_segment, maxsplit=1, flags=re.I)[0]

    avg = re.search(r'平均\s*(\d+(?:\.\d+)?)\s*(个月|月|weeks?|周|days?|天)', user_segment, flags=re.I)
    if avg:
        return _duration_to_days(float(avg.group(1)), avg.group(2))

    range_unit = re.search(r'(\d+(?:\.\d+)?)\s*[-~–]\s*(\d+(?:\.\d+)?)\s*(weeks?|周|days?|天|个月|月)', user_segment, flags=re.I)
    if range_unit:
        low = float(range_unit.group(1))
        high = float(range_unit.group(2))
        return _duration_to_days((low + high) / 2, range_unit.group(3))

    greater_than = re.search(r'>\s*(\d+(?:\.\d+)?)\s*(weeks?|周|days?|天|个月|月)', user_segment, flags=re.I)
    if greater_than:
        return int(_duration_to_days(float(greater_than.group(1)), greater_than.group(2)) * 1.25)

    number_unit = re.search(r'(\d+(?:\.\d+)?)\s*(weeks?|周|days?|天|个月|月)', user_segment, flags=re.I)
    if number_unit:
        return _duration_to_days(float(number_unit.group(1)), number_unit.group(2))

    return None


def _duration_to_days(value: float, unit: str) -> int:
    unit = str(unit or '').lower()
    if unit in ('天', 'day', 'days', 'd'):
        return int(round(value))
    if unit in ('周', 'week', 'weeks', 'w'):
        return int(round(value * 7))
    if unit in ('个月', '月', 'month', 'months', 'm'):
        return int(round(value * 30))
    return int(round(value))


def _to_float_or_none(value) -> Optional[float]:
    try:
        if value is None or value == '':
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_days(days: int) -> str:
    if days >= 60:
        return f"{round(days / 30, 1)}个月"
    return f"{days}天"


def _short_review_label(text: str) -> str:
    label = str(text or '').split('；')[0].replace('网友分享经验：', '').strip()
    return label[:80]


def _contains_wos_on_hold_text(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_wos_on_hold_text(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_wos_on_hold_text(v) for v in value)
    text = str(value or '')
    if not text:
        return False
    if not re.search(r'(wos|web\s*of\s*science|clarivate|master\s*journal|on\s*[- ]?hold|暂停收录|收录暂停)', text, re.I):
        return False
    return bool(re.search(r'(on\s*[- ]?hold|wos.{0,40}hold|web\s*of\s*science.{0,40}hold|clarivate.{0,40}hold|暂停收录|收录暂停)', text, re.I))


def _extract_partition(letpub_detail: Dict) -> str:
    """从 LetPub 详情提取分区文本"""
    if letpub_detail.get('partition'):
        return letpub_detail.get('partition', '')
    p = letpub_detail.get('ch_sci_2025')
    if isinstance(p, dict):
        return p.get('分区', '')
    elif isinstance(p, str):
        return p
    # fallback: sci_part
    return letpub_detail.get('sci_part', '')


def batch_metrics(journal_names: List[str], delay: float = 1.0) -> Dict[str, Dict]:
    """批量获取期刊指标"""
    results = {}
    unique_names = list(set(journal_names))
    for i, name in enumerate(unique_names):
        metrics = get_journal_metrics(name)
        if metrics.get('_sources'):
            results[name] = metrics
        if i < len(unique_names) - 1:
            time.sleep(delay)
    return results


def format_metrics_line(m: Dict) -> str:
    """一行格式化期刊指标"""
    parts = []

    # 收录类型
    sci = m.get('sci_type', '')
    if sci:
        s = sci.upper().replace(' ', '')
        if 'SCIE' in s:
            parts.append('SCIE')
        elif 'ESCI' in s:
            parts.append('⚠️ESCI')
        elif 'SSCI' in s:
            parts.append('SSCI')
        elif s != '无':
            parts.append(sci)
        else:
            parts.append('❌非SCI')
    elif 'letpub' in m.get('_sources', []):
        parts.append('❌非SCI')

    # IF
    if m.get('impact_factor'):
        parts.append(f"IF={m['impact_factor']}")

    # 分区
    p = m.get('partition', '')
    if p:
        parts.append(f"中科院{p}")

    # SJR Q分区（如果有的话）
    # h-index
    if m.get('h_index'):
        parts.append(f"h={m['h_index']}")

    # 审稿速度
    if m.get('speed'):
        speed = m['speed'].split('；')[0].replace('网友分享经验：', '').strip()
        if speed and len(speed) < 30:
            parts.append(speed)

    # OA
    if m.get('is_oa') is not None:
        oa_str = 'OA'
        if m.get('apc_usd'):
            oa_str += f"(${m['apc_usd']})"
        parts.append(oa_str if m['is_oa'] else '非OA')

    # 预警
    if m.get('warning'):
        parts.append('⚠️预警')

    return ' | '.join(parts) if parts else '无信息'


if __name__ == '__main__':
    for name in ['Journal of Hydrology', 'Water Resources Research', 'Water']:
        m = get_journal_metrics(name)
        print(f"{name}: {format_metrics_line(m)}")
