"""
social_data.py — StockTwits API 기반 소셜 데이터 수집
Reddit PRAW 대체 (무료, API 키 불필요)
StockTwits API: https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json
"""
import os
import json
import urllib.request
import urllib.error
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def fetch_stocktwits_posts(ticker: str, date: str, limit: int = 30) -> list[dict]:
    """
    StockTwits 게시글 수집

    Args:
        ticker: 종목 코드 (예: "AAPL")
        date: 날짜 YYYY-MM-DD (기준일, StockTwits는 최근 데이터만 제공)
        limit: 최대 수집 게시글 수

    Returns:
        List[dict]: 게시글 목록 (body, sentiment, created_at, likes)
    """
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json?limit={min(limit, 30)}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'TradingAgents/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        messages = data.get('messages', [])
        posts = []
        for msg in messages:
            entities = msg.get('entities', {})
            sentiment = None
            if entities.get('sentiment'):
                sentiment = entities['sentiment'].get('basic', None)  # 'Bullish' or 'Bearish'
            likes = msg.get('likes', {})
            likes_count = likes.get('total', 0) if isinstance(likes, dict) else 0
            posts.append({
                'body': msg.get('body', ''),
                'sentiment': sentiment,  # 'Bullish', 'Bearish', or None
                'created_at': msg.get('created_at', ''),
                'likes': likes_count,
                'source': 'stocktwits',
            })
        return posts[:limit]

    except urllib.error.HTTPError as e:
        print(f"StockTwits HTTP error for {ticker}: {e.code}")
        return []
    except Exception as e:
        print(f"StockTwits fetch error for {ticker}: {e}")
        return []


def calculate_sentiment_metrics(posts: list[dict]) -> dict:
    """
    소셜 데이터 감성 지표 계산 (StockTwits 전용)

    Args:
        posts: StockTwits 게시글 목록

    Returns:
        dict: 감성 지표 (post_count, bullish_count, bearish_count, sentiment_ratio, engagement_score)
    """
    if not posts:
        return {
            'post_count': 0,
            'bullish_count': 0,
            'bearish_count': 0,
            'avg_likes': 0,
            'sentiment_ratio': 0.5,
            'engagement_score': 0.0,
        }

    bullish = sum(1 for p in posts if p.get('sentiment') == 'Bullish')
    bearish = sum(1 for p in posts if p.get('sentiment') == 'Bearish')
    total_with_sentiment = bullish + bearish
    sentiment_ratio = (bullish / total_with_sentiment) if total_with_sentiment > 0 else 0.5
    avg_likes = sum(p.get('likes', 0) for p in posts) / len(posts)
    engagement = min(1.0, avg_likes / 50)

    return {
        'post_count': len(posts),
        'bullish_count': bullish,
        'bearish_count': bearish,
        'avg_likes': round(avg_likes, 1),
        'sentiment_ratio': round(sentiment_ratio, 3),
        'engagement_score': round(engagement, 3),
    }


# Keep backward-compat alias for code that imports fetch_reddit_posts
def fetch_reddit_posts(ticker: str, date: str, limit: int = 25) -> list[dict]:
    """StockTwits로 대체된 소셜 데이터 수집 (하위 호환성)"""
    return fetch_stocktwits_posts(ticker, date, limit)
