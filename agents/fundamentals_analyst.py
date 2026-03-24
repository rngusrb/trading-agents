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

    # 데이터 수집
    profile = fetch_company_profile(ticker)
    financials = fetch_basic_financials(ticker)
    earnings = fetch_earnings(ticker)
    recommendations = fetch_recommendation_trends(ticker)

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
    except Exception as e:
        print(f"LLM analysis error: {e}")
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
    """분석 컨텍스트 문자열 생성"""
    lines = [
        f"Ticker: {ticker}",
        f"Analysis Date: {date}",
        "",
        "=== Company Profile ===",
        f"Name: {profile.get('name', 'N/A')}",
        f"Industry: {profile.get('finnhubIndustry', 'N/A')}",
        f"Market Cap: {profile.get('marketCapitalization', 'N/A')}B",
        "",
        "=== Key Financial Metrics ===",
        f"P/E Ratio: {financials.get('peBasicExclExtraTTM', 'N/A')}",
        f"P/B Ratio: {financials.get('pbQuarterly', 'N/A')}",
        f"ROE: {financials.get('roeTTM', 'N/A')}%",
        f"Debt/Equity: {financials.get('totalDebt/totalEquityQuarterly', 'N/A')}",
        f"Revenue Growth YoY: {financials.get('revenueGrowthTTMYoy', 'N/A')}%",
        f"EPS Growth: {financials.get('epsGrowthTTMYoy', 'N/A')}%",
        "",
        "=== Recent Earnings ===",
    ]

    for e in earnings[:2]:
        lines.append(
            f"  Q{e.get('period', 'N/A')}: EPS Actual={e.get('actual', 'N/A')}, "
            f"Estimate={e.get('estimate', 'N/A')}, "
            f"Surprise={e.get('surprisePercent', 'N/A')}%"
        )

    if market_data:
        lines.extend([
            "",
            "=== Current Price ===",
            f"Close: ${market_data.close:.2f}",
            f"Volume: {market_data.volume:,}",
        ])

    return "\n".join(lines)


def _fallback_analysis(financials: dict) -> dict:
    """LLM 실패 시 규칙 기반 폴백 분석"""
    pe = financials.get('peBasicExclExtraTTM')
    roe = financials.get('roeTTM')

    signal = 'neutral'
    confidence = 0.4

    if pe and roe:
        if float(pe) < 20 and float(roe) > 15:
            signal = 'bullish'
            confidence = 0.65
        elif float(pe) > 40 or float(roe) < 5:
            signal = 'bearish'
            confidence = 0.60

    return {
        'signal': signal,
        'confidence': confidence,
        'summary': f'Rule-based analysis: P/E={pe}, ROE={roe}%',
        'key_points': [
            f'P/E ratio: {pe}',
            f'ROE: {roe}%',
            'Fallback analysis used'
        ]
    }
