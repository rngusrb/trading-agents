"""
trader.py — 트레이더 에이전트
리서치 보고서를 바탕으로 최종 트레이딩 결정
DECISION_MODEL (claude-sonnet) 사용
"""
import os
import json
from typing import Optional
from dotenv import load_dotenv
import anthropic
from agents import parse_llm_json
from models.schemas import ResearchReport, AnalystReport, MarketData, TradeDecision

load_dotenv()

DECISION_MODEL = os.getenv('DECISION_MODEL', 'claude-sonnet-4-6')


def make_trade_decision(
    ticker: str,
    date: str,
    research_report: ResearchReport,
    analyst_reports: list[AnalystReport],
    market_data: Optional[MarketData] = None
) -> TradeDecision:
    """
    최종 트레이딩 결정 수행

    Args:
        ticker: 종목 코드
        date: 결정 날짜 YYYY-MM-DD
        research_report: Bull/Bear 리서치 보고서
        analyst_reports: 4개 애널리스트 보고서
        market_data: 현재 주가 데이터

    Returns:
        TradeDecision: 트레이딩 결정 (approved=False, Risk Manager 승인 대기)
    """
    context = _build_trader_context(ticker, date, research_report, analyst_reports, market_data)

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    prompt = f"""You are an experienced stock trader making a trading decision.

{context}

Based on all available information, make a specific trading decision.

Rules:
- action: "buy" if overall outlook is positive, "sell" if negative, "hold" if uncertain
- quantity: position size as fraction 0.0-1.0 (e.g., 0.5 = 50% of available capital)
  - Strong conviction (>0.75): quantity 0.6-0.8
  - Moderate conviction (0.5-0.75): quantity 0.3-0.5
  - Low conviction (<0.5): quantity 0.1-0.3
  - Hold: quantity 0.0
- risk_score: estimated risk level 0.0 (low risk) to 1.0 (high risk)

Respond with ONLY a raw JSON object. No markdown, no code blocks, no explanation before or after.
{{
    "action": "buy|sell|hold",
    "quantity": 0.0-1.0,
    "reasoning": "detailed reasoning for the decision",
    "risk_score": 0.0-1.0
}}"""

    try:
        message = client.messages.create(
            model=DECISION_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_llm_json(message.content[0].text)
    except Exception as e:
        print(f"Trader decision error: {e}")
        result = _fallback_trade_decision(research_report)

    return TradeDecision(
        ticker=ticker,
        date=date,
        action=result.get('action', 'hold'),
        quantity=float(result.get('quantity', 0.0)),
        reasoning=result.get('reasoning', 'Decision based on research report'),
        risk_score=float(result.get('risk_score', 0.5)),
        approved=False  # Risk Manager 승인 대기
    )


def _build_trader_context(
    ticker: str,
    date: str,
    research_report: ResearchReport,
    analyst_reports: list[AnalystReport],
    market_data: Optional[MarketData]
) -> str:
    """트레이더 컨텍스트 문자열 생성"""
    lines = [
        f"Ticker: {ticker}",
        f"Decision Date: {date}",
        "",
        "=== Research Consensus ===",
        f"Recommendation: {research_report.consensus.upper()}",
        f"Conviction: {research_report.conviction:.0%}",
        "",
        "Bull Case:",
        research_report.bull_case[:500],
        "",
        "Bear Case:",
        research_report.bear_case[:500],
        "",
        "=== Analyst Signals ===",
    ]
    for r in analyst_reports:
        lines.append(f"  {r.analyst_type}: {r.signal} ({r.confidence:.0%} confidence)")

    if market_data:
        lines.extend([
            "",
            "=== Current Market Data ===",
            f"Price: ${market_data.close:.2f}",
            f"Volume: {market_data.volume:,}",
        ])
        if market_data.indicators:
            lines.append(f"RSI: {market_data.indicators.get('RSI_14', 'N/A')}")
            lines.append(f"MACD Hist: {market_data.indicators.get('MACD_Hist', 'N/A')}")

    return "\n".join(lines)


def _fallback_trade_decision(research_report: ResearchReport) -> dict:
    """LLM 실패 시 리서치 합의 기반 폴백"""
    consensus = research_report.consensus
    conviction = research_report.conviction

    if consensus == 'buy':
        quantity = min(0.8, conviction)
        risk_score = 1.0 - conviction
    elif consensus == 'sell':
        quantity = min(0.8, conviction)
        risk_score = conviction
    else:
        quantity = 0.0
        risk_score = 0.5

    return {
        'action': consensus,
        'quantity': round(quantity, 2),
        'reasoning': f'Fallback decision based on research consensus: {consensus} with {conviction:.0%} conviction',
        'risk_score': round(risk_score, 2)
    }
