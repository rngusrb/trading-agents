"""
news_analyst.py — 뉴스 분석 에이전트
Finnhub 뉴스 데이터 기반 시장 뉴스 감성 및 영향도 분석
ANALYST_MODEL (claude-haiku) 사용으로 비용 최적화
"""
import os
import json
from dotenv import load_dotenv
import anthropic
from agents import parse_llm_json
from models.schemas import AnalystReport
from tools.news_fetcher import fetch_company_news, extract_news_summary

load_dotenv()

ANALYST_MODEL = os.getenv('ANALYST_MODEL', 'claude-haiku-4-5-20251001')


def analyze_news(ticker: str, date: str, config: dict = None) -> AnalystReport:
    """
    뉴스 분석 실행

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD
        config: 시스템 설정 (선택, 기본값: DEFAULT_CONFIG)

    Returns:
        AnalystReport: 뉴스 분석 보고서
    """
    from config import get_config
    cfg = get_config(config)
    model = cfg.get("quick_think_llm", ANALYST_MODEL)

    raw_news = fetch_company_news(ticker, date, days_back=7)
    news_items = extract_news_summary(raw_news)
    context = _build_news_context(ticker, date, news_items)

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    prompt = f"""You are a financial news analyst. Analyze the following news articles and assess their impact on the stock.

{context}

Respond with ONLY a raw JSON object. No markdown, no code blocks, no explanation before or after.
{{
    "signal": "bullish|bearish|neutral",
    "confidence": 0.0-1.0,
    "summary": "brief news impact summary",
    "key_points": ["point1", "point2", "point3"]
}}"""

    try:
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_llm_json(message.content[0].text)
        print(f"[NewsAnalyst] ✅ LLM OK — signal={result.get('signal')}, confidence={result.get('confidence')}")
    except Exception as e:
        print(f"[NewsAnalyst] ❌ LLM error: {e} — fallback 사용")
        result = _fallback_news_analysis(news_items)

    return AnalystReport(
        analyst_type="news",
        ticker=ticker,
        date=date,
        signal=result.get('signal', 'neutral'),
        confidence=float(result.get('confidence', 0.5)),
        summary=result.get('summary', 'News analysis complete'),
        key_points=result.get('key_points', ['News data analyzed']),
        data_sources=["finnhub_news"]
    )


def _build_news_context(ticker: str, date: str, news_items: list[dict]) -> str:
    """뉴스 분석 컨텍스트 문자열 생성"""
    lines = [
        f"Ticker: {ticker}",
        f"Analysis Date: {date}",
        f"Total News Articles: {len(news_items)}",
        "",
        "=== Recent News Headlines ===",
    ]
    for i, item in enumerate(news_items[:10], 1):
        lines.append(f"\n{i}. [{item.get('source', 'Unknown')}]")
        lines.append(f"   Headline: {item.get('headline', 'N/A')}")
        summary = item.get('summary', '')
        if summary:
            lines.append(f"   Summary: {summary[:200]}...")
    if not news_items:
        lines.append("No recent news articles found.")
    return "\n".join(lines)


def _fallback_news_analysis(news_items: list[dict]) -> dict:
    """LLM 실패 시 규칙 기반 폴백 분석"""
    if not news_items:
        return {
            'signal': 'neutral',
            'confidence': 0.3,
            'summary': 'No news data available for analysis',
            'key_points': ['No recent news found', 'Defaulting to neutral stance']
        }

    bullish_keywords = ['beat', 'surge', 'growth', 'record', 'strong', 'upgrade']
    bearish_keywords = ['miss', 'decline', 'fall', 'weak', 'downgrade', 'cut']
    headlines = ' '.join(item.get('headline', '').lower() for item in news_items)
    bull_count = sum(1 for kw in bullish_keywords if kw in headlines)
    bear_count = sum(1 for kw in bearish_keywords if kw in headlines)

    if bull_count > bear_count + 1:
        signal, confidence = 'bullish', 0.6
    elif bear_count > bull_count + 1:
        signal, confidence = 'bearish', 0.6
    else:
        signal, confidence = 'neutral', 0.45

    return {
        'signal': signal,
        'confidence': confidence,
        'summary': f'Keyword analysis: {bull_count} bullish, {bear_count} bearish signals',
        'key_points': [
            f'Analyzed {len(news_items)} news articles',
            f'Bullish keywords: {bull_count}',
            f'Bearish keywords: {bear_count}'
        ]
    }
