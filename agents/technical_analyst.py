"""
technical_analyst.py — 기술적 분석 에이전트
pandas-ta 기반 기술적 지표 분석
ANALYST_MODEL (claude-haiku) 사용으로 비용 최적화
"""
import os
import json
from typing import Optional
from dotenv import load_dotenv
import anthropic
from agents import parse_llm_json
from models.schemas import AnalystReport, MarketData
from tools.market_data import fetch_historical_data
from tools.technical_indicators import calculate_indicators, interpret_signals

load_dotenv()

ANALYST_MODEL = os.getenv('ANALYST_MODEL', 'claude-haiku-4-5-20251001')


def analyze_technical(
    ticker: str,
    date: str,
    market_data: Optional[MarketData] = None,
    config: dict = None
) -> AnalystReport:
    """
    기술적 분석 실행

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD
        market_data: 현재 주가 데이터 (선택)
        config: 시스템 설정 (선택, 기본값: DEFAULT_CONFIG)

    Returns:
        AnalystReport: 기술적 분석 보고서
    """
    from config import get_config
    cfg = get_config(config)
    model = cfg.get("quick_think_llm", ANALYST_MODEL)

    # 히스토리컬 데이터 수집 (60일)
    from datetime import datetime, timedelta
    target_dt = datetime.strptime(date, '%Y-%m-%d')
    start_date = (target_dt - timedelta(days=90)).strftime('%Y-%m-%d')

    df = fetch_historical_data(ticker, start_date, date)
    indicators = calculate_indicators(df) if not df.empty else {}

    current_price = market_data.close if market_data else (
        float(df['Close'].iloc[-1]) if not df.empty else 0.0
    )
    signals = interpret_signals(indicators, current_price)

    context = _build_technical_context(ticker, date, indicators, signals, current_price)

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    prompt = f"""You are a technical analyst. Analyze the following technical indicators and provide a trading signal assessment.

{context}

Respond with ONLY a raw JSON object. No markdown, no code blocks, no explanation before or after.
{{
    "signal": "bullish|bearish|neutral",
    "confidence": 0.0-1.0,
    "summary": "brief technical analysis summary",
    "key_points": ["point1", "point2", "point3"]
}}"""

    try:
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_llm_json(message.content[0].text)
        print(f"[TechnicalAnalyst] ✅ LLM OK — signal={result.get('signal')}, confidence={result.get('confidence')}")
    except Exception as e:
        print(f"[TechnicalAnalyst] ❌ LLM error: {e} — fallback 사용")
        result = _fallback_technical_analysis(signals, indicators)

    # indicators를 market_data에 병합
    if market_data and indicators:
        market_data.indicators.update(indicators)

    return AnalystReport(
        analyst_type="technical",
        ticker=ticker,
        date=date,
        signal=result.get('signal', 'neutral'),
        confidence=float(result.get('confidence', 0.5)),
        summary=result.get('summary', 'Technical analysis complete'),
        key_points=result.get('key_points', ['Indicators analyzed']),
        data_sources=["yfinance", "pandas_ta"]
    )


def _build_technical_context(
    ticker: str,
    date: str,
    indicators: dict,
    signals: dict,
    current_price: float
) -> str:
    """기술적 분석 컨텍스트 문자열 생성"""
    lines = [
        f"Ticker: {ticker}",
        f"Analysis Date: {date}",
        f"Current Price: ${current_price:.2f}",
        "",
        "=== Technical Indicators ===",
        f"RSI (14): {indicators.get('RSI_14', 'N/A')}",
        f"MACD: {indicators.get('MACD', 'N/A')}",
        f"MACD Signal: {indicators.get('MACD_Signal', 'N/A')}",
        f"MACD Hist: {indicators.get('MACD_Hist', 'N/A')}",
        f"BB Upper: {indicators.get('BB_Upper', 'N/A')}",
        f"BB Middle: {indicators.get('BB_Middle', 'N/A')}",
        f"BB Lower: {indicators.get('BB_Lower', 'N/A')}",
        f"SMA 20: {indicators.get('SMA_20', 'N/A')}",
        f"SMA 50: {indicators.get('SMA_50', 'N/A')}",
        f"ATR 14: {indicators.get('ATR_14', 'N/A')}",
        "",
        "=== Signal Summary ===",
    ]
    for indicator, sig in signals.items():
        lines.append(f"  {indicator}: {sig}")
    return "\n".join(lines)


def _fallback_technical_analysis(signals: dict, indicators: dict) -> dict:
    """LLM 실패 시 규칙 기반 폴백 분석"""
    bull_count = sum(1 for s in signals.values() if s == 'bullish')
    bear_count = sum(1 for s in signals.values() if s == 'bearish')
    total = len(signals)

    if total == 0:
        return {
            'signal': 'neutral',
            'confidence': 0.3,
            'summary': 'Insufficient technical data',
            'key_points': ['Unable to calculate indicators', 'Insufficient price history']
        }

    if bull_count > total * 0.6:
        signal, confidence = 'bullish', 0.65
    elif bear_count > total * 0.6:
        signal, confidence = 'bearish', 0.65
    else:
        signal, confidence = 'neutral', 0.45

    return {
        'signal': signal,
        'confidence': confidence,
        'summary': f'Technical signals: {bull_count} bullish, {bear_count} bearish out of {total}',
        'key_points': [
            f'RSI: {indicators.get("RSI_14", "N/A")}',
            f'MACD Hist: {indicators.get("MACD_Hist", "N/A")}',
            f'Bullish signals: {bull_count}/{total}'
        ]
    }
