"""
sentiment_analyst.py — 소셜 미디어 감성 분석 에이전트
Reddit 데이터 기반 시장 심리 분석
ANALYST_MODEL (claude-haiku) 사용으로 비용 최적화
"""
import os
import json
from dotenv import load_dotenv
import anthropic
from agents import parse_llm_json
from models.schemas import AnalystReport
from tools.social_data import fetch_reddit_posts, calculate_sentiment_metrics

load_dotenv()

ANALYST_MODEL = os.getenv('ANALYST_MODEL', 'claude-haiku-4-5-20251001')


def analyze_sentiment(ticker: str, date: str, config: dict = None) -> AnalystReport:
    """
    소셜 미디어 감성 분석 실행

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD
        config: 시스템 설정 (선택, 기본값: DEFAULT_CONFIG)

    Returns:
        AnalystReport: 감성 분석 보고서
    """
    from config import get_config
    cfg = get_config(config)
    model = cfg.get("quick_think_llm", ANALYST_MODEL)

    posts = fetch_reddit_posts(ticker, date, limit=25)
    metrics = calculate_sentiment_metrics(posts)
    context = _build_sentiment_context(ticker, date, posts, metrics)

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    prompt = f"""You are a market sentiment analyst. Analyze the following social media data and assess market sentiment.

{context}

Respond with ONLY a raw JSON object. No markdown, no code blocks, no explanation before or after.
{{
    "signal": "bullish|bearish|neutral",
    "confidence": 0.0-1.0,
    "summary": "brief sentiment analysis summary",
    "key_points": ["point1", "point2", "point3"]
}}"""

    try:
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_llm_json(message.content[0].text)
        print(f"[SentimentAnalyst] ✅ LLM OK — signal={result.get('signal')}, confidence={result.get('confidence')}")
    except Exception as e:
        print(f"[SentimentAnalyst] ❌ LLM error: {e} — fallback 사용")
        result = _fallback_sentiment_analysis(metrics)

    return AnalystReport(
        analyst_type="sentiment",
        ticker=ticker,
        date=date,
        signal=result.get('signal', 'neutral'),
        confidence=float(result.get('confidence', 0.5)),
        summary=result.get('summary', 'Sentiment analysis complete'),
        key_points=result.get('key_points', ['Social data analyzed']),
        data_sources=["stocktwits"]
    )


def _build_sentiment_context(
    ticker: str,
    date: str,
    posts: list[dict],
    metrics: dict
) -> str:
    """감성 분석 컨텍스트 문자열 생성 (StockTwits 기반)"""
    lines = [
        f"Ticker: {ticker}",
        f"Analysis Date: {date}",
        "",
        "=== StockTwits Social Metrics ===",
        f"Total Posts: {metrics['post_count']}",
        f"Bullish Sentiment: {metrics['bullish_count']} posts",
        f"Bearish Sentiment: {metrics['bearish_count']} posts",
        f"Sentiment Ratio (Bullish): {metrics['sentiment_ratio']:.1%}",
        f"Avg Likes: {metrics['avg_likes']:.1f}",
        f"Engagement Score: {metrics['engagement_score']:.3f}",
        "",
        "=== Recent Posts (Top 5) ===",
    ]
    for post in posts[:5]:
        sentiment = post.get('sentiment', 'N/A')
        lines.append(
            f"  [{sentiment or 'N/A'}] Likes: {post.get('likes', 0)}\n"
            f"  {post.get('body', 'N/A')[:100]}"
        )
    return "\n".join(lines)


def _fallback_sentiment_analysis(metrics: dict) -> dict:
    """LLM 실패 시 규칙 기반 폴백 분석 (StockTwits 기반)"""
    ratio = metrics.get('sentiment_ratio', 0.5)
    post_count = metrics.get('post_count', 0)

    if post_count == 0:
        return {
            'signal': 'neutral',
            'confidence': 0.3,
            'summary': 'Insufficient social data for analysis',
            'key_points': ['No social media data found', 'Cannot determine market sentiment']
        }

    if ratio > 0.65:
        signal, conf = 'bullish', 0.6
    elif ratio < 0.35:
        signal, conf = 'bearish', 0.6
    else:
        signal, conf = 'neutral', 0.4

    return {
        'signal': signal,
        'confidence': conf,
        'summary': f'StockTwits sentiment: {ratio:.0%} bullish ({post_count} posts)',
        'key_points': [
            f'Post count: {post_count}',
            f'Bullish: {metrics.get("bullish_count", 0)}, Bearish: {metrics.get("bearish_count", 0)}',
            f'Sentiment ratio: {ratio:.0%}',
        ]
    }
