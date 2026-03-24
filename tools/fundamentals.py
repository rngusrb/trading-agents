"""
fundamentals.py — Polygon.io 기반 펀더멘털 데이터 수집
look-ahead bias 방지: filing_date.lte=analysis_date 로 실제 공시일 기준 필터링

Polygon.io Starter Plan: 2년 과거 데이터 지원
엔드포인트: GET /vX/reference/financials
"""
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
BASE_URL = "https://api.polygon.io"


def _get(endpoint: str, params: dict) -> dict:
    """Polygon.io API 호출 공통 함수"""
    params['apiKey'] = POLYGON_API_KEY
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Polygon API error {endpoint}: {e}")
        return {}


def _val(obj: dict, *keys) -> Optional[float]:
    """중첩 dict에서 value 안전 추출. e.g. _val(inc, 'revenues', 'value')"""
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    try:
        return float(cur) if cur is not None else None
    except (TypeError, ValueError):
        return None


def fetch_company_profile(ticker: str, date: str = None) -> Dict[str, Any]:
    """
    기업 프로필 조회 (Polygon.io ticker details)

    Args:
        ticker: 종목 코드
        date: 분석 날짜 (미사용, 하위 호환성)

    Returns:
        dict: 기업 기본 정보
    """
    data = _get(f"/v3/reference/tickers/{ticker}", {})
    result = data.get('results', {})
    if not result:
        return {}

    market_cap = result.get('market_cap') or 0
    return {
        'name': result.get('name', ticker),
        'sector': result.get('sic_description', 'N/A'),
        'industry': result.get('sic_description', 'N/A'),
        'marketCapitalization': round(market_cap / 1e9, 2),
        'country': result.get('locale', 'N/A').upper(),
    }


def fetch_basic_financials(ticker: str, date: str) -> Dict[str, Any]:
    """
    분석 날짜 기준 실제 공시된 재무 지표 (look-ahead bias 완전 방지)

    filing_date.lte=analysis_date 로 공시일 기준 필터링.
    US 기업 중 Q4를 10-K(연간) 형태로만 신고하는 경우(e.g. AAPL) 처리:
    → quarterly + annual 모두 조회 후 더 최근 공시 기준으로 TTM 계산

    예시 (분석일 2025-01-15):
      quarterly: Q3(2024-08-02), Q2(2024-05-03), Q1(2024-02-02)
      annual:    FY2024(2024-11-01) ← 더 최근 → 이걸 TTM으로 사용

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD

    Returns:
        dict: TTM 매출/순이익/EPS, ROE, D/E, 매출성장률, 최신 분기일
    """
    result: Dict[str, Any] = {}
    params_base = {
        'ticker': ticker,
        'filing_date.lte': date,
        'limit': 8,
        'sort': 'filing_date',
        'order': 'desc',
    }

    # 분기 데이터 조회
    q_data = _get("/vX/reference/financials", {**params_base, 'timeframe': 'quarterly'})
    quarters = q_data.get('results', [])

    # 연간 데이터 조회 (Q4 포함 10-K 대응)
    a_data = _get("/vX/reference/financials", {**params_base, 'timeframe': 'annual', 'limit': 2})
    annuals = a_data.get('results', [])

    if not quarters and not annuals:
        print(f"[Fundamentals] ⚠️  {ticker} {date}: Polygon에서 데이터 없음")
        return result

    # 최신 공시일 비교: quarterly vs annual
    q_latest_date = quarters[0].get('filing_date', '1900-01-01') if quarters else '1900-01-01'
    a_latest_date = annuals[0].get('filing_date', '1900-01-01') if annuals else '1900-01-01'

    if a_latest_date > q_latest_date:
        # annual이 더 최신 → FY 데이터를 TTM 기준으로 사용
        ttm_source = [annuals[0]]
        latest = annuals[0]
        source_type = f"annual(FY, filed {a_latest_date[:10]})"
    else:
        # quarterly가 더 최신 → 최근 4분기 합산으로 TTM 계산
        ttm_source = quarters[:4]
        latest = quarters[0]
        source_type = f"quarterly({len(ttm_source)}Q, latest filed {q_latest_date[:10]})"

    result['latest_quarter'] = latest.get('period_of_report_date') or latest.get('filing_date', '')[:10]
    result['filing_date'] = latest.get('filing_date', '')[:10]
    result['data_source'] = source_type

    # ── Income Statement (TTM) ───────────────────────────────────────
    revenue_ttm = _sum_ttm(ttm_source, 'income_statement', 'revenues')
    net_income_ttm = _sum_ttm(ttm_source, 'income_statement', 'net_income_loss')
    eps_ttm = _sum_ttm(ttm_source, 'income_statement', 'diluted_earnings_per_share') \
           or _sum_ttm(ttm_source, 'income_statement', 'basic_earnings_per_share')

    if revenue_ttm is not None:
        result['revenue_ttm'] = revenue_ttm
    if net_income_ttm is not None:
        result['net_income_ttm'] = net_income_ttm
    if eps_ttm is not None:
        result['eps_ttm'] = round(eps_ttm, 4)

    # 매출 성장률 YoY (quarterly 기준 8Q 있을 때만)
    if len(quarters) >= 8:
        prior_rev = _sum_ttm(quarters[4:8], 'income_statement', 'revenues')
        if revenue_ttm and prior_rev and prior_rev != 0:
            result['revenue_growth_yoy'] = round(
                (revenue_ttm - prior_rev) / abs(prior_rev) * 100, 2
            )
    elif len(annuals) >= 2:
        # annual 2개로 YoY 계산
        prev_rev = _val(
            annuals[1].get('financials', {}).get('income_statement', {}), 'revenues', 'value'
        )
        if revenue_ttm and prev_rev and prev_rev != 0:
            result['revenue_growth_yoy'] = round(
                (revenue_ttm - prev_rev) / abs(prev_rev) * 100, 2
            )

    # ── Balance Sheet (최신 공시 기준) ───────────────────────────────
    bs = latest.get('financials', {}).get('balance_sheet', {})
    equity = _val(bs, 'equity_attributable_to_parent', 'value') \
          or _val(bs, 'equity', 'value')
    long_term_debt = _val(bs, 'long_term_debt', 'value') or 0
    current_debt = _val(bs, 'current_liabilities', 'value') or 0
    total_debt = long_term_debt + current_debt if (long_term_debt or current_debt) else None

    if equity is not None:
        result['stockholders_equity'] = equity
    if total_debt:
        result['total_debt'] = total_debt

    if result.get('net_income_ttm') and equity and equity != 0:
        result['roe'] = round(result['net_income_ttm'] / equity * 100, 2)
    if total_debt and equity and equity != 0:
        result['debt_to_equity'] = round(total_debt / equity, 3)

    return result


def _sum_ttm(quarters: list, statement: str, field: str) -> Optional[float]:
    """분기 리스트에서 특정 재무 항목 합산 (TTM)"""
    vals = []
    for q in quarters:
        v = _val(q.get('financials', {}).get(statement, {}), field, 'value')
        if v is not None:
            vals.append(v)
    return sum(vals) if vals else None


def fetch_earnings(ticker: str, date: str) -> list[Dict[str, Any]]:
    """
    분기별 EPS 실적 (공시일 기준 look-ahead bias 방지)

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD

    Returns:
        list[dict]: 최근 4분기 EPS (period, actual)
    """
    data = _get("/vX/reference/financials", {
        'ticker': ticker,
        'timeframe': 'quarterly',
        'filing_date.lte': date,
        'limit': 4,
        'sort': 'filing_date',
        'order': 'desc',
    })

    results = []
    for q in data.get('results', []):
        inc = q.get('financials', {}).get('income_statement', {})
        eps = _val(inc, 'diluted_earnings_per_share', 'value') \
           or _val(inc, 'basic_earnings_per_share', 'value')
        period = q.get('period_of_report_date') or q.get('filing_date', '')[:10]
        results.append({
            'period': period,
            'actual': round(eps, 4) if eps is not None else None,
            'estimate': None,
            'surprisePercent': None,
        })
    return results


def fetch_recommendation_trends(ticker: str, date: str = None) -> list[Dict[str, Any]]:
    """애널리스트 추천 추이 (하위 호환성, 빈 리스트 반환)"""
    return []


def get_fundamentals(ticker: str, date: str) -> Dict[str, Any]:
    """
    fetch_basic_financials 편의 래퍼

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD

    Returns:
        dict: 재무 지표 (latest_quarter, revenue_ttm, eps_ttm, roe, debt_to_equity 등)
    """
    return fetch_basic_financials(ticker, date)
