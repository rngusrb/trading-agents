"""
TradingAgentState - LangGraph 워크플로우 상태 정의
모든 에이전트가 공유하는 상태 객체
"""
from typing import Optional, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from models.schemas import MarketData, AnalystReport, ResearchReport, TradeDecision


class TradingAgentState(TypedDict):
    """
    LangGraph 워크플로우 전체 상태

    각 에이전트는 이 상태를 읽고 자신의 결과를 추가합니다.
    messages는 add_messages reducer로 자동 누적됩니다.
    """
    # 기본 정보
    ticker: str
    date: str

    # 데이터 레이어
    market_data: Optional[MarketData]

    # 애널리스트 보고서 (4개)
    analyst_reports: list[AnalystReport]

    # 리서치 보고서 (Bull/Bear 토론 결과)
    research_report: Optional[ResearchReport]

    # 최종 트레이딩 결정
    trade_decision: Optional[TradeDecision]

    # LangGraph 메시지 히스토리 (add_messages reducer)
    messages: Annotated[list[BaseMessage], add_messages]

    # 다음 실행할 에이전트
    next_agent: str

    # 시스템 설정 (config/__init__.py)
    config: Optional[dict]


def create_initial_state(ticker: str, date: str, config: dict = None) -> TradingAgentState:
    """
    초기 상태 생성

    Args:
        ticker: 종목 코드 (예: "AAPL")
        date: 분석 날짜 (예: "2024-01-15")
        config: 시스템 설정 (선택)

    Returns:
        TradingAgentState: 초기화된 상태
    """
    return TradingAgentState(
        ticker=ticker,
        date=date,
        market_data=None,
        analyst_reports=[],
        research_report=None,
        trade_decision=None,
        messages=[],
        next_agent="fundamentals_analyst",
        config=config
    )
