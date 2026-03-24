"""
fundamentals_analyst.py — 펀더멘털 분석 에이전트
yfinance + Finnhub 데이터로 기업 펀더멘털 분석
ANALYST_MODEL (claude-haiku) 사용으로 비용 최적화
"""
import os
import json
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import anthropic
from agents import parse_llm_json
from models.schemas import AnalystReport, MarketData
from tools.fundamentals import (
    fetch_company_profile,
    fetch_basic_financials,
    fetch_earnings,
    fetch_recommendation_trends
)

load_dotenv()

ANALYST_MODEL = os.getenv('ANALYST_MODEL', 'claude-haiku-4-5-20251001')


def analyze_fundamentals(
    ticker: str,
    date: str,
    market_data: Optional[MarketData] = None,
    config: dict = None
) -> AnalystReport:
    """
    펀더멘털 분석 실행

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD
        market_data: 주가 데이터 (선택)
        config: 시스템 설정 (선택, 기본값: DEFAULT_CONFIG)

    Returns:
        AnalystReport: 펀더멘털 분석 보고서
    """
    from config import get_config
    cfg = get_config(config)
    model = cfg.get("quick_think_llm", ANALYST_MODEL)

    # 데이터 수집 (date 전달 → look-ahead bias 방지)
    profile = fetch_company_profile(ticker, date)
    financials = fetch_basic_financials(ticker, date)
    earnings = fetch_earnings(ticker, date)
    recommendations = fetch_recommendation_trends(ticker, date)

    # 분석 컨텍스트 구성
    context = _build_analysis_context(
        ticker, date, profile, financials, earnings, recommendations, market_data
    )

    # Claude에 분석 요청
    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    prompt = f"""You are a fundamental analyst. Analyze the following data and provide a structured assessment.

{context}

Respond with ONLY a raw JSON object. No markdown, no code blocks, no explanation before or after.
{{
    "signal": "bullish|bearish|neutral",
    "confidence": 0.0-1.0,
    "summary": "brief analysis summary",
    "key_points": ["point1", "point2", "point3"]
}}"""

    try:
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text
        # JSON 파싱
        result = parse_llm_json(response_text)
        print(f"[FundamentalsAnalyst] ✅ LLM OK — signal={result.get('signal')}, confidence={result.get('confidence')}")
    except Exception as e:
        print(f"[FundamentalsAnalyst] ❌ LLM error: {e} — fallback 사용")
        result = _fallback_analysis(financials)

    return AnalystReport(
        analyst_type="fundamentals",
        ticker=ticker,
        date=date,
        signal=result.get('signal', 'neutral'),
        confidence=float(result.get('confidence', 0.5)),
        summary=result.get('summary', 'Fundamental analysis complete'),
        key_points=result.get('key_points', ['Data analyzed']),
        data_sources=["finnhub", "yfinance"]
    )


def _build_analysis_context(
    ticker: str,
    date: str,
    profile: dict,
    financials: dict,
    earnings: list,
    recommendations: list,
    market_data: Optional[MarketData]
) -> str:
    """분석 컨텍스트 문자열 생성 (yfinance 기반 필드명)"""

    # P/E 계산: 주가 / TTM EPS
    pe_ratio = 'N/A'
    eps_ttm = financials.get('eps_ttm')
    if market_data and eps_ttm and eps_ttm != 0:
        pe_ratio = round(market_data.close / eps_ttm, 2)

    lines = [
        f"Ticker: {ticker}",
        f"Analysis Date: {date}",
        f"Data as of Quarter: {financials.get('latest_quarter', 'N/A')}",
        "",
        "=== Company Profile ===",
        f"Name: {profile.get('name', 'N/A')}",
        f"Sector: {profile.get('sector', 'N/A')}",
        f"Industry: {profile.get('industry', 'N/A')}",
        f"Market Cap: ${profile.get('marketCapitalization', 'N/A')}B",
        "",
        "=== Key Financial Metrics (TTM, look-ahead bias free) ===",
        f"P/E Ratio (price/EPS_TTM): {pe_ratio}",
        f"EPS (TTM): {eps_ttm if eps_ttm is not None else 'N/A'}",
        f"Revenue (TTM): ${round(financials['revenue_ttm']/1e9,2)}B"
            if financials.get('revenue_ttm') else "Revenue (TTM): N/A",
        f"Net Income (TTM): ${round(financials['net_income_ttm']/1e9,2)}B"
            if financials.get('net_income_ttm') else "Net Income (TTM): N/A",
        f"ROE: {financials.get('roe', 'N/A')}%",
        f"Debt/Equity: {financials.get('debt_to_equity', 'N/A')}",
        f"Revenue Growth YoY: {financials.get('revenue_growth_yoy', 'N/A')}%",
        "",
        "=== Recent Quarterly EPS ===",
    ]

    for e in earnings[:3]:
        lines.append(
            f"  {e.get('period', 'N/A')}: EPS={e.get('actual', 'N/A')}"
        )

    if market_data:
        lines.extend([
            "",
            "=== Market Data ===",
            f"Price: ${market_data.close:.2f}",
            f"Volume: {market_data.volume:,}",
        ])

    return "\n".join(lines)


def _fallback_analysis(financials: dict) -> dict:
    """LLM 실패 시 규칙 기반 폴백 분석"""
    roe = financials.get('roe')
    de = financials.get('debt_to_equity')
    rev_growth = financials.get('revenue_growth_yoy')

    signal = 'neutral'
    confidence = 0.4

    if roe is not None:
        if roe > 20 and (de is None or de < 2):
            signal = 'bullish'
            confidence = 0.6
        elif roe < 5:
            signal = 'bearish'
            confidence = 0.55

    return {
        'signal': signal,
        'confidence': confidence,
        'summary': f'Rule-based: ROE={roe}%, D/E={de}, RevGrowth={rev_growth}%',
        'key_points': [
            f'ROE: {roe}%',
            f'Debt/Equity: {de}',
            f'Revenue Growth YoY: {rev_growth}%',
            'Fallback analysis used'
        ]
    }
