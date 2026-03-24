"""
social_data.py — Reddit PRAW 기반 소셜 데이터 수집
"""
import os
from typing import Optional
import praw
from dotenv import load_dotenv

load_dotenv()


def get_reddit_client() -> praw.Reddit:
    """Reddit API 클라이언트 초기화"""
    return praw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID', 'placeholder'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET', 'placeholder'),
        user_agent=os.getenv('REDDIT_USER_AGENT', 'TradingAgents/1.0')
    )


def fetch_reddit_posts(ticker: str, date: str, limit: int = 25) -> list[dict]:
    """
    Reddit 게시글 수집

    Args:
        ticker: 종목 코드 (예: "AAPL")
        date: 날짜 YYYY-MM-DD (기준일)
        limit: 최대 수집 게시글 수

    Returns:
        List[dict]: 게시글 목록 (title, score, num_comments, subreddit)
    """
    try:
        reddit = get_reddit_client()
        subreddits = ['wallstreetbets', 'stocks', 'investing', 'StockMarket']
        posts = []

        per_sub = max(1, limit // len(subreddits))
        for subreddit_name in subreddits:
            subreddit = reddit.subreddit(subreddit_name)
            for submission in subreddit.search(
                query=f'${ticker} OR {ticker}',
                sort='new',
                limit=per_sub
            ):
                posts.append({
                    'title': submission.title,
                    'score': submission.score,
                    'num_comments': submission.num_comments,
                    'created_utc': submission.created_utc,
                    'subreddit': subreddit_name,
                    'url': submission.url
                })

        return posts
    except Exception as e:
        print(f"Reddit fetch error for {ticker}: {e}")
        return []


def calculate_sentiment_metrics(posts: list[dict]) -> dict:
    """
    소셜 데이터 감성 지표 계산

    Args:
        posts: Reddit 게시글 목록

    Returns:
        dict: 감성 지표 (post_count, avg_score, total_comments, engagement_score)
    """
    if not posts:
        return {
            'post_count': 0,
            'avg_score': 0,
            'total_comments': 0,
            'engagement_score': 0.0
        }

    total_score = sum(p.get('score', 0) for p in posts)
    total_comments = sum(p.get('num_comments', 0) for p in posts)
    avg_score = total_score / len(posts)
    engagement = (avg_score + total_comments / len(posts)) / 2
    normalized_engagement = min(1.0, engagement / 1000)

    return {
        'post_count': len(posts),
        'avg_score': avg_score,
        'total_comments': total_comments,
        'engagement_score': normalized_engagement
    }
