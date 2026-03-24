"""
researcher.py — Bull/Bear 리서처 에이전트
애널리스트 보고서를 바탕으로 매수/매도 논거 강화 및 합의 도출
DECISION_MODEL (claude-sonnet) 사용으로 고품질 분석
"""
import os
import json
from dotenv import load_dotenv
import anthropic
from agents import parse_llm_json
from models.schemas import AnalystReport, ResearchReport

load_dotenv()

DECISION_MODEL = os.getenv('DECISION_MODEL', 'claude-sonnet-4-6')


def conduct_research(
    ticker: str,
    date: str,
    analyst_reports: list[AnalystReport]
) -> ResearchReport:
    """
    Bull/Bear 토론 기반 리서치 수행

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD
        analyst_reports: 4개 애널리스트 보고서

    Returns:
        ResearchReport: 매수/매도 논거 및 합의 보고서
    """
    context = _build_research_context(ticker, date, analyst_reports)

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    # Bull Researcher
    bull_case = _get_bull_case(client, ticker, context)

    # Bear Researcher
    bear_case = _get_bear_case(client, ticker, context)

    # 합의 도출
    consensus_result = _get_consensus(client, ticker, bull_case, bear_case, context)

    return ResearchReport(
        ticker=ticker,
        date=date,
        bull_case=bull_case,
        bear_case=bear_case,
        consensus=consensus_result.get('consensus', 'hold'),
        conviction=float(consensus_result.get('conviction', 0.5))
    )


def _build_research_context(
    ticker: str,
    date: str,
    analyst_reports: list[AnalystReport]
) -> str:
    """리서치 컨텍스트 문자열 생성"""
    lines = [
        f"Ticker: {ticker}",
        f"Date: {date}",
        "",
        "=== Analyst Reports Summary ===",
    ]
    for report in analyst_reports:
        lines.extend([
            f"\n[{report.analyst_type.upper()} ANALYST]",
            f"Signal: {report.signal} (confidence: {report.confidence:.0%})",
            f"Summary: {report.summary}",
            "Key Points:",
        ])
        for point in report.key_points:
            lines.append(f"  - {point}")

    # 신호 집계
    signals = [r.signal for r in analyst_reports]
    bull_count = signals.count('bullish')
    bear_count = signals.count('bearish')
    neutral_count = signals.count('neutral')
    avg_confidence = sum(r.confidence for r in analyst_reports) / len(analyst_reports) if analyst_reports else 0

    lines.extend([
        "",
        "=== Signal Aggregation ===",
        f"Bullish: {bull_count}, Bearish: {bear_count}, Neutral: {neutral_count}",
        f"Average Confidence: {avg_confidence:.0%}"
    ])
    return "\n".join(lines)


def _get_bull_case(client: anthropic.Anthropic, ticker: str, context: str) -> str:
    """Bull Researcher: 매수 논거 강화"""
    prompt = f"""You are the Bull Researcher. Your job is to construct the strongest possible BULLISH case for {ticker}.

Use the analyst reports below and find the best arguments for buying.
Focus on growth potential, undervaluation, positive catalysts, and technical support.

{context}

Provide a concise but compelling bull case (2-3 paragraphs)."""

    try:
        message = client.messages.create(
            model=DECISION_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Bull researcher error: {e}")
        return f"Bullish case for {ticker}: Positive analyst signals support buying opportunity."


def _get_bear_case(client: anthropic.Anthropic, ticker: str, context: str) -> str:
    """Bear Researcher: 매도 논거 강화"""
    prompt = f"""You are the Bear Researcher. Your job is to construct the strongest possible BEARISH case for {ticker}.

Use the analyst reports below and find the best arguments for selling or avoiding.
Focus on downside risks, overvaluation, negative catalysts, and technical weakness.

{context}

Provide a concise but compelling bear case (2-3 paragraphs)."""

    try:
        message = client.messages.create(
            model=DECISION_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Bear researcher error: {e}")
        return f"Bearish case for {ticker}: Risk factors warrant caution."


def _get_consensus(
    client: anthropic.Anthropic,
    ticker: str,
    bull_case: str,
    bear_case: str,
    original_context: str
) -> dict:
    """Bull/Bear 토론 후 합의 도출"""
    prompt = f"""You are a senior research analyst mediating between Bull and Bear perspectives on {ticker}.

=== BULL CASE ===
{bull_case}

=== BEAR CASE ===
{bear_case}

=== ORIGINAL DATA ===
{original_context}

After weighing both arguments, provide your consensus recommendation.

Respond in JSON format:
{{
    "consensus": "buy|sell|hold",
    "conviction": 0.0-1.0,
    "rationale": "brief explanation of the consensus decision"
}}"""

    try:
        message = client.messages.create(
            model=DECISION_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        return parse_llm_json(message.content[0].text)
    except Exception as e:
        print(f"Consensus error: {e}")
        # 폴백: 신호 다수결
        return {'consensus': 'hold', 'conviction': 0.4, 'rationale': 'Insufficient data for consensus'}
