"""
news_fetcher.py — Finnhub 뉴스 API 기반 뉴스 데이터 수집
"""
import os
from datetime import datetime, timedelta
import finnhub
from dotenv import load_dotenv

load_dotenv()


def get_finnhub_client() -> finnhub.Client:
    """Finnhub 클라이언트 초기화"""
    api_key = os.getenv('FINNHUB_API_KEY', 'sandbox_key')
    return finnhub.Client(api_key=api_key)


def fetch_company_news(ticker: str, date: str, days_back: int = 7) -> list[dict]:
    """
    기업 관련 뉴스 수집

    Args:
        ticker: 종목 코드 (예: "AAPL")
        date: 기준 날짜 YYYY-MM-DD
        days_back: 뒤로 조회할 일수

    Returns:
        List[dict]: 뉴스 목록
    """
    try:
        client = get_finnhub_client()
        target_date = datetime.strptime(date, '%Y-%m-%d')
        start_date = (target_date - timedelta(days=days_back)).strftime('%Y-%m-%d')

        news = client.company_news(ticker, _from=start_date, to=date)
        return news or []
    except Exception as e:
        print(f"news fetch error for {ticker}: {e}")
        return []


def fetch_market_news(category: str = 'general', limit: int = 10) -> list[dict]:
    """
    시장 전반 뉴스 수집

    Args:
        category: 뉴스 카테고리 (general, forex, crypto, merger)
        limit: 최대 수집 뉴스 수

    Returns:
        List[dict]: 뉴스 목록
    """
    try:
        client = get_finnhub_client()
        news = client.general_news(category, min_id=0)
        return news[:limit] if news else []
    except Exception as e:
        print(f"market news fetch error: {e}")
        return []


def extract_news_summary(news_items: list[dict]) -> list[dict]:
    """
    뉴스 아이템에서 핵심 정보 추출

    Args:
        news_items: 원본 뉴스 목록

    Returns:
        List[dict]: 정제된 뉴스 목록
    """
    extracted = []
    for item in news_items:
        extracted.append({
            'headline': item.get('headline', ''),
            'summary': item.get('summary', '')[:500],
            'source': item.get('source', ''),
            'datetime': item.get('datetime', 0),
            'url': item.get('url', '')
        })
    return extracted
