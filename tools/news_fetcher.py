"""
news_fetcher.py — Polygon.io 기반 뉴스 수집
look-ahead bias 방지: published_utc.lte=analysis_date 로 날짜 기준 필터링

Polygon.io Starter Plan: 2년 과거 뉴스 지원
엔드포인트: GET /v2/reference/news
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')
BASE_URL = "https://api.polygon.io"


def fetch_company_news(ticker: str, date: str, days_back: int = 7) -> list[dict]:
    """
    Polygon.io 뉴스 수집 (look-ahead bias 완전 방지)

    published_utc.lte=analysis_date 로 분석일 이전 기사만 가져옴.

    Args:
        ticker: 종목 코드
        date: 기준 날짜 YYYY-MM-DD (이 날짜 이전 뉴스만 반환)
        days_back: 조회 기간 (일)

    Returns:
        list[dict]: Polygon.io 뉴스 아이템 목록
    """
    try:
        target_dt = datetime.strptime(date, '%Y-%m-%d')
        start_dt = target_dt - timedelta(days=days_back)

        params = {
            'ticker': ticker,
            'published_utc.lte': target_dt.strftime('%Y-%m-%dT23:59:59Z'),
            'published_utc.gte': start_dt.strftime('%Y-%m-%dT00:00:00Z'),
            'limit': 20,
            'sort': 'published_utc',
            'order': 'desc',
            'apiKey': POLYGON_API_KEY,
        }
        resp = requests.get(f"{BASE_URL}/v2/reference/news", params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get('results', [])
        print(f"[News] {ticker} {date}: {len(results)}개 기사 수집 ({days_back}일 범위)")
        return results

    except Exception as e:
        print(f"[News] fetch error for {ticker}: {e}")
        return []


def fetch_market_news(category: str = 'general', limit: int = 10) -> list[dict]:
    """시장 전반 뉴스 (하위 호환성 유지)"""
    return []


def extract_news_summary(news_items: list[dict]) -> list[dict]:
    """
    Polygon.io 뉴스 아이템에서 핵심 정보 추출

    Args:
        news_items: fetch_company_news() 반환값

    Returns:
        list[dict]: headline, summary, source, datetime, url
    """
    extracted = []
    for item in news_items:
        extracted.append({
            'headline': item.get('title', ''),
            'summary': item.get('description', '')[:500],
            'source': (item.get('publisher') or {}).get('name', ''),
            'datetime': item.get('published_utc', ''),
            'url': item.get('article_url', ''),
        })
    return extracted
