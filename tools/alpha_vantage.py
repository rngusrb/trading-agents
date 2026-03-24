"""
alpha_vantage.py — Alpha Vantage API 기반 데이터 수집
기술적 지표, 펀더멘털, 감성 데이터 제공
"""
import os
import json
import urllib.request
import urllib.error
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.alphavantage.co/query"


def _fetch(params: dict) -> Optional[dict]:
    """
    Alpha Vantage API 공통 요청

    Args:
        params: 쿼리 파라미터 딕셔너리

    Returns:
        Optional[dict]: API 응답 또는 None
    """
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY', 'demo')
    params['apikey'] = api_key
    query = '&'.join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE_URL}?{query}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'TradingAgents/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Alpha Vantage API error: {e}")
        return None


def fetch_daily_prices(ticker: str, outputsize: str = 'compact') -> Optional[dict]:
    """
    일별 주가 데이터 조회

    Args:
        ticker: 종목 코드 (예: "AAPL")
        outputsize: 'compact' (최근 100일) 또는 'full' (전체)

    Returns:
        dict: TIME_SERIES_DAILY 데이터 또는 None
    """
    data = _fetch({
        'function': 'TIME_SERIES_DAILY',
        'symbol': ticker,
        'outputsize': outputsize,
    })
    if not data or 'Time Series (Daily)' not in data:
        return None
    return data.get('Time Series (Daily)', {})


def fetch_company_overview(ticker: str) -> dict:
    """
    기업 개요 및 펀더멘털 데이터 조회

    Args:
        ticker: 종목 코드

    Returns:
        dict: 기업 개요 (P/E, ROE, EPS, MarketCap 등)
    """
    data = _fetch({'function': 'OVERVIEW', 'symbol': ticker})
    return data or {}


def fetch_earnings(ticker: str) -> list[dict]:
    """
    실적 데이터 조회

    Args:
        ticker: 종목 코드

    Returns:
        list[dict]: 분기별 EPS 실적 (최근 4분기)
    """
    data = _fetch({'function': 'EARNINGS', 'symbol': ticker})
    if not data:
        return []
    return data.get('quarterlyEarnings', [])[:4]  # 최근 4분기


def fetch_news_sentiment(ticker: str, limit: int = 10) -> list[dict]:
    """
    뉴스 & 감성 데이터 조회 (Alpha Vantage News Sentiment API)

    Args:
        ticker: 종목 코드
        limit: 최대 뉴스 수

    Returns:
        list[dict]: 뉴스 및 감성 점수
    """
    data = _fetch({
        'function': 'NEWS_SENTIMENT',
        'tickers': ticker,
        'limit': limit,
        'sort': 'RELEVANCE',
    })
    if not data or 'feed' not in data:
        return []
    return data.get('feed', [])[:limit]


def fetch_rsi(ticker: str, interval: str = 'daily', time_period: int = 14) -> Optional[dict]:
    """
    RSI 지표 조회

    Args:
        ticker: 종목 코드
        interval: 'daily', 'weekly', 'monthly'
        time_period: RSI 기간

    Returns:
        dict: 최근 RSI 값 {'date': str, 'RSI': float} 또는 None
    """
    data = _fetch({
        'function': 'RSI',
        'symbol': ticker,
        'interval': interval,
        'time_period': time_period,
        'series_type': 'close',
    })
    if not data or 'Technical Analysis: RSI' not in data:
        return None
    series = data['Technical Analysis: RSI']
    if not series:
        return None
    latest_date = sorted(series.keys())[-1]
    return {'date': latest_date, 'RSI': float(series[latest_date]['RSI'])}
