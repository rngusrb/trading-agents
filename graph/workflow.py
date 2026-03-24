"""
workflow.py — LangGraph 전체 워크플로우 구성
7개 에이전트를 연결하는 메인 그래프
"""
import os
from typing import Any
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from graph.state import TradingAgentState, create_initial_state
from models.schemas import MarketData
from tools.market_data import fetch_market_data
from agents.fundamentals_analyst import analyze_fundamentals
from agents.sentiment_analyst import analyze_sentiment
from agents.news_analyst import analyze_news
from agents.technical_analyst import analyze_technical
from agents.researcher import conduct_research
from agents.trader import make_trade_decision
from agents.risk_manager import assess_and_approve

load_dotenv()


# ─── 노드 함수들 ───────────────────────────────────────────────────────────────

def fetch_data_node(state: TradingAgentState) -> dict:
    """
    주가 데이터 수집 노드

    Args:
        state: 현재 워크플로우 상태

    Returns:
        dict: market_data 업데이트
    """
    ticker = state['ticker']
    date = state['date']
    market_data = fetch_market_data(ticker, date)
    return {"market_data": market_data}


def fundamentals_node(state: TradingAgentState) -> dict:
    """펀더멘털 분석 노드"""
    report = analyze_fundamentals(
        state['ticker'],
        state['date'],
        state.get('market_data')
    )
    existing = list(state.get('analyst_reports', []))
    existing.append(report)
    return {"analyst_reports": existing}


def sentiment_node(state: TradingAgentState) -> dict:
    """소셜 미디어 감성 분석 노드"""
    report = analyze_sentiment(state['ticker'], state['date'])
    existing = list(state.get('analyst_reports', []))
    existing.append(report)
    return {"analyst_reports": existing}


def news_node(state: TradingAgentState) -> dict:
    """뉴스 분석 노드"""
    report = analyze_news(state['ticker'], state['date'])
    existing = list(state.get('analyst_reports', []))
    existing.append(report)
    return {"analyst_reports": existing}


def technical_node(state: TradingAgentState) -> dict:
    """기술적 분석 노드"""
    report = analyze_technical(
        state['ticker'],
        state['date'],
        state.get('market_data')
    )
    existing = list(state.get('analyst_reports', []))
    existing.append(report)
    return {"analyst_reports": existing}


def researcher_node(state: TradingAgentState) -> dict:
    """Bull/Bear 리서처 노드"""
    research_report = conduct_research(
        state['ticker'],
        state['date'],
        state['analyst_reports']
    )
    return {"research_report": research_report}


def trader_node(state: TradingAgentState) -> dict:
    """트레이더 결정 노드"""
    trade_decision = make_trade_decision(
        state['ticker'],
        state['date'],
        state['research_report'],
        state['analyst_reports'],
        state.get('market_data')
    )
    return {"trade_decision": trade_decision}


def risk_manager_node(state: TradingAgentState) -> dict:
    """리스크 관리 + Fund Manager 승인 노드"""
    final_decision = assess_and_approve(
        state['trade_decision'],
        state['research_report'],
        state['analyst_reports'],
        state.get('market_data')
    )
    return {"trade_decision": final_decision}


# ─── 그래프 빌드 ───────────────────────────────────────────────────────────────

def build_workflow() -> Any:
    """
    LangGraph 워크플로우 빌드

    Returns:
        CompiledGraph: 실행 가능한 LangGraph 그래프
    """
    graph = StateGraph(TradingAgentState)

    # 노드 등록
    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("fundamentals_analyst", fundamentals_node)
    graph.add_node("sentiment_analyst", sentiment_node)
    graph.add_node("news_analyst", news_node)
    graph.add_node("technical_analyst", technical_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("trader", trader_node)
    graph.add_node("risk_manager", risk_manager_node)

    # 엣지 연결 (순차 실행)
    graph.set_entry_point("fetch_data")
    graph.add_edge("fetch_data", "fundamentals_analyst")
    graph.add_edge("fundamentals_analyst", "sentiment_analyst")
    graph.add_edge("sentiment_analyst", "news_analyst")
    graph.add_edge("news_analyst", "technical_analyst")
    graph.add_edge("technical_analyst", "researcher")
    graph.add_edge("researcher", "trader")
    graph.add_edge("trader", "risk_manager")
    graph.add_edge("risk_manager", END)

    return graph.compile()


def run_pipeline(ticker: str, date: str) -> TradingAgentState:
    """
    트레이딩 파이프라인 실행

    Args:
        ticker: 종목 코드 (예: "AAPL")
        date: 분석 날짜 (예: "2024-01-15")

    Returns:
        TradingAgentState: 최종 상태 (trade_decision 포함)
    """
    workflow = build_workflow()
    initial_state = create_initial_state(ticker, date)
    final_state = workflow.invoke(initial_state)
    return final_state
