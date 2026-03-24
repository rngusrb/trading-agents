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


def analyze_sentiment(ticker: str, date: str) -> AnalystReport:
    """
    소셜 미디어 감성 분석 실행

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD

    Returns:
        AnalystReport: 감성 분석 보고서
    """
    posts = fetch_reddit_posts(ticker, date, limit=25)
    metrics = calculate_sentiment_metrics(posts)
    context = _build_sentiment_context(ticker, date, posts, metrics)

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    prompt = f"""You are a market sentiment analyst. Analyze the following social media data and assess market sentiment.

{context}

Respond in JSON format:
{{
    "signal": "bullish|bearish|neutral",
    "confidence": 0.0-1.0,
    "summary": "brief sentiment analysis summary",
    "key_points": ["point1", "point2", "point3"]
}}"""

    try:
        message = client.messages.create(
            model=ANALYST_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_llm_json(message.content[0].text)
    except Exception as e:
        print(f"LLM sentiment analysis error: {e}")
        result = _fallback_sentiment_analysis(metrics)

    return AnalystReport(
        analyst_type="sentiment",
        ticker=ticker,
        date=date,
        signal=result.get('signal', 'neutral'),
        confidence=float(result.get('confidence', 0.5)),
        summary=result.get('summary', 'Sentiment analysis complete'),
        key_points=result.get('key_points', ['Social data analyzed']),
        data_sources=["reddit_wallstreetbets", "reddit_stocks", "reddit_investing"]
    )


def _build_sentiment_context(
    ticker: str,
    date: str,
    posts: list[dict],
    metrics: dict
) -> str:
    """감성 분석 컨텍스트 문자열 생성"""
    lines = [
        f"Ticker: {ticker}",
        f"Analysis Date: {date}",
        "",
        "=== Reddit Social Metrics ===",
        f"Total Posts Found: {metrics['post_count']}",
        f"Average Post Score: {metrics['avg_score']:.1f}",
        f"Total Comments: {metrics['total_comments']}",
        f"Engagement Score: {metrics['engagement_score']:.3f}",
        "",
        "=== Recent Posts (Top 5) ===",
    ]
    for post in posts[:5]:
        lines.append(
            f"  [{post.get('subreddit', 'N/A')}] "
            f"Score: {post.get('score', 0)}, "
            f"Comments: {post.get('num_comments', 0)}\n"
            f"  Title: {post.get('title', 'N/A')[:100]}"
        )
    return "\n".join(lines)


def _fallback_sentiment_analysis(metrics: dict) -> dict:
    """LLM 실패 시 규칙 기반 폴백 분석"""
    post_count = metrics.get('post_count', 0)
    avg_score = metrics.get('avg_score', 0)
    engagement = metrics.get('engagement_score', 0)

    if post_count == 0:
        return {
            'signal': 'neutral',
            'confidence': 0.3,
            'summary': 'Insufficient social data for analysis',
            'key_points': ['No social media data found', 'Cannot determine market sentiment']
        }

    signal, confidence = 'neutral', 0.4
    if avg_score > 100 and engagement > 0.1:
        signal, confidence = 'bullish', 0.6
    elif avg_score < 0:
        signal, confidence = 'bearish', 0.55

    return {
        'signal': signal,
        'confidence': confidence,
        'summary': f'Rule-based sentiment: {post_count} posts, avg score {avg_score:.0f}',
        'key_points': [
            f'Post count: {post_count}',
            f'Average score: {avg_score:.0f}',
            f'Engagement: {engagement:.3f}'
        ]
    }
