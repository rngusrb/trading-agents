"""
risk_manager.py — 리스크 관리팀 + Fund Manager 에이전트
3명의 리스크 분석가 (Risky/Neutral/Safe) + Fund Manager 최종 승인
DECISION_MODEL + MANAGER_MODEL 사용
"""
import os
import json
from typing import Optional
from dotenv import load_dotenv
import anthropic
from agents import parse_llm_json
from models.schemas import TradeDecision, ResearchReport, AnalystReport, MarketData

load_dotenv()

DECISION_MODEL = os.getenv('DECISION_MODEL', 'claude-sonnet-4-6')
MANAGER_MODEL = os.getenv('MANAGER_MODEL', 'claude-opus-4-6')


def assess_and_approve(
    trade_decision: TradeDecision,
    research_report: ResearchReport,
    analyst_reports: list[AnalystReport],
    market_data: Optional[MarketData] = None,
    config: dict = None
) -> TradeDecision:
    """
    리스크 평가 및 Fund Manager 최종 승인

    Args:
        trade_decision: Trader의 초안 결정
        research_report: 리서치 보고서
        analyst_reports: 애널리스트 보고서들
        market_data: 현재 주가 데이터
        config: 시스템 설정 (선택, 기본값: DEFAULT_CONFIG)

    Returns:
        TradeDecision: 승인/수정된 최종 결정 (approved=True/False)
    """
    from config import get_config
    cfg = get_config(config)
    decision_model = cfg.get("decision_llm", DECISION_MODEL)
    manager_model = cfg.get("deep_think_llm", MANAGER_MODEL)

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    context = _build_risk_context(trade_decision, research_report, analyst_reports, market_data)

    # 3명의 리스크 분석가 의견
    risky_opinion = _get_risk_opinion(client, 'risky', context, trade_decision, decision_model)
    neutral_opinion = _get_risk_opinion(client, 'neutral', context, trade_decision, decision_model)
    safe_opinion = _get_risk_opinion(client, 'safe', context, trade_decision, decision_model)

    # Fund Manager 최종 결정
    final_decision = _fund_manager_decision(
        client, trade_decision, risky_opinion, neutral_opinion, safe_opinion, context, manager_model
    )

    return TradeDecision(
        ticker=trade_decision.ticker,
        date=trade_decision.date,
        action=final_decision.get('action', trade_decision.action),
        quantity=float(final_decision.get('quantity', trade_decision.quantity)),
        reasoning=final_decision.get('reasoning', trade_decision.reasoning),
        risk_score=float(final_decision.get('risk_score', trade_decision.risk_score)),
        approved=final_decision.get('approved', False)
    )


def _build_risk_context(
    trade_decision: TradeDecision,
    research_report: ResearchReport,
    analyst_reports: list[AnalystReport],
    market_data: Optional[MarketData]
) -> str:
    """리스크 평가 컨텍스트 문자열 생성"""
    lines = [
        f"Ticker: {trade_decision.ticker}",
        f"Date: {trade_decision.date}",
        "",
        "=== Proposed Trade Decision ===",
        f"Action: {trade_decision.action.upper()}",
        f"Quantity: {trade_decision.quantity:.0%} of capital",
        f"Risk Score: {trade_decision.risk_score:.0%}",
        f"Reasoning: {trade_decision.reasoning[:300]}",
        "",
        "=== Research Consensus ===",
        f"Consensus: {research_report.consensus.upper()} (conviction: {research_report.conviction:.0%})",
        "",
        "=== Analyst Signals ===",
    ]
    for r in analyst_reports:
        lines.append(f"  {r.analyst_type}: {r.signal} ({r.confidence:.0%})")

    if market_data:
        lines.extend([
            "",
            f"Current Price: ${market_data.close:.2f}",
            f"Volume: {market_data.volume:,}",
        ])

    return "\n".join(lines)


def _get_risk_opinion(
    client: anthropic.Anthropic,
    analyst_type: str,
    context: str,
    trade_decision: TradeDecision,
    model: str = None
) -> str:
    """개별 리스크 분석가 의견 수렴"""
    personas = {
        'risky': "You are an aggressive risk analyst who prioritizes returns over safety. You favor taking larger positions when the opportunity looks good.",
        'neutral': "You are a balanced risk analyst who weighs both risk and reward equally. You prefer moderate position sizes.",
        'safe': "You are a conservative risk analyst who prioritizes capital preservation. You are cautious about large positions and prefer to minimize downside."
    }

    prompt = f"""{personas[analyst_type]}

Review this proposed trade and provide your risk assessment.

{context}

Provide your opinion on:
1. Is this trade appropriate? (approve/modify/reject)
2. Your recommended position size (0.0-1.0)
3. Key risks or opportunities you see

Keep your response concise (2-3 sentences)."""

    use_model = model or DECISION_MODEL
    try:
        message = client.messages.create(
            model=use_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Risk analyst ({analyst_type}) error: {e}")
        return f"{analyst_type.capitalize()} analyst: Unable to assess. Default to original decision."


def _fund_manager_decision(
    client: anthropic.Anthropic,
    trade_decision: TradeDecision,
    risky_opinion: str,
    neutral_opinion: str,
    safe_opinion: str,
    context: str,
    model: str = None
) -> dict:
    """Fund Manager 최종 결정"""
    prompt = f"""You are the Fund Manager making the final investment decision.

You have received opinions from three risk analysts and the original trader's proposal.
Your job is to make the final call, ensuring the portfolio's best interest.

=== ORIGINAL TRADE PROPOSAL ===
{context}

=== RISKY ANALYST ===
{risky_opinion}

=== NEUTRAL ANALYST ===
{neutral_opinion}

=== SAFE ANALYST ===
{safe_opinion}

Make your final decision. You can:
- Approve the trade as-is
- Modify the position size
- Change the action (e.g., reduce from buy to hold)
- Reject the trade entirely

Respond with ONLY a raw JSON object. No markdown, no code blocks, no explanation before or after.
{{
    "action": "buy|sell|short|cover|hold",
    "quantity": 0.0-1.0,
    "reasoning": "final decision rationale",
    "risk_score": 0.0-1.0,
    "approved": true|false
}}"""

    use_model = model or MANAGER_MODEL
    try:
        message = client.messages.create(
            model=use_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_llm_json(message.content[0].text)
        return result
    except Exception as e:
        print(f"Fund Manager decision error: {e}")
        # 폴백: 리스크 점수가 낮으면 승인
        approved = trade_decision.risk_score < 0.6
        return {
            'action': trade_decision.action,
            'quantity': trade_decision.quantity,
            'reasoning': f'Fallback approval based on risk score {trade_decision.risk_score:.0%}',
            'risk_score': trade_decision.risk_score,
            'approved': approved
        }
