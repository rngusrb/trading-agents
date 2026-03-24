"""
fundamentals.py — Finnhub API 기반 펀더멘털 데이터 수집
"""
import os
from typing import Optional, Dict, Any
import finnhub
from dotenv import load_dotenv

load_dotenv()


def get_finnhub_client() -> finnhub.Client:
    """Finnhub 클라이언트 초기화"""
    api_key = os.getenv('FINNHUB_API_KEY', 'sandbox_key')
    return finnhub.Client(api_key=api_key)


def fetch_company_profile(ticker: str) -> Dict[str, Any]:
    """
    기업 프로필 조회

    Args:
        ticker: 종목 코드

    Returns:
        Dict: 기업 기본 정보
    """
    try:
        client = get_finnhub_client()
        profile = client.company_profile2(symbol=ticker)
        return profile or {}
    except Exception as e:
        print(f"company profile fetch error for {ticker}: {e}")
        return {}


def fetch_basic_financials(ticker: str) -> Dict[str, Any]:
    """
    기본 재무 지표 조회 (PER, PBR, ROE 등)

    Args:
        ticker: 종목 코드

    Returns:
        Dict: 재무 지표
    """
    try:
        client = get_finnhub_client()
        financials = client.company_basic_financials(ticker, 'all')
        return financials.get('metric', {}) or {}
    except Exception as e:
        print(f"basic financials fetch error for {ticker}: {e}")
        return {}


def fetch_earnings(ticker: str) -> list[Dict[str, Any]]:
    """
    실적 데이터 조회

    Args:
        ticker: 종목 코드

    Returns:
        List: 분기별 EPS 실적
    """
    try:
        client = get_finnhub_client()
        earnings = client.company_earnings(ticker, limit=4)
        return earnings or []
    except Exception as e:
        print(f"earnings fetch error for {ticker}: {e}")
        return []


def fetch_recommendation_trends(ticker: str) -> list[Dict[str, Any]]:
    """
    애널리스트 추천 트렌드 조회

    Args:
        ticker: 종목 코드

    Returns:
        List: 추천 트렌드 데이터
    """
    try:
        client = get_finnhub_client()
        trends = client.recommendation_trends(ticker)
        return trends or []
    except Exception as e:
        print(f"recommendation trends fetch error for {ticker}: {e}")
        return []
