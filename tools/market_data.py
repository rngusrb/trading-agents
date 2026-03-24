"""
market_data.py — yfinance 기반 주가 데이터 수집 도구
"""
import os
from datetime import datetime, timedelta
from typing import Optional
import yfinance as yf
import pandas as pd
from models.schemas import MarketData


def fetch_market_data(ticker: str, date: str) -> Optional[MarketData]:
    """
    특정 날짜의 주가 데이터 조회

    Args:
        ticker: 종목 코드 (예: "AAPL")
        date: 날짜 YYYY-MM-DD

    Returns:
        MarketData 또는 None (데이터 없을 시)
    """
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d')
        start = (target_date - timedelta(days=5)).strftime('%Y-%m-%d')
        end = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')

        ticker_obj = yf.Ticker(ticker)
        hist = ticker_obj.history(start=start, end=end)

        if hist.empty:
            return None

        # 가장 가까운 날짜 데이터 사용
        row = hist.iloc[-1]

        return MarketData(
            ticker=ticker,
            date=date,
            open=float(row['Open']),
            high=float(row['High']),
            low=float(row['Low']),
            close=float(row['Close']),
            volume=int(row['Volume']),
            indicators={}
        )
    except Exception as e:
        print(f"market_data fetch error for {ticker} on {date}: {e}")
        return None


def fetch_historical_data(
    ticker: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    기간별 히스토리컬 데이터 조회

    Args:
        ticker: 종목 코드
        start_date: 시작 날짜 YYYY-MM-DD
        end_date: 종료 날짜 YYYY-MM-DD

    Returns:
        DataFrame: OHLCV 데이터
    """
    ticker_obj = yf.Ticker(ticker)
    hist = ticker_obj.history(start=start_date, end=end_date)
    if not hist.empty:
        hist.index = pd.to_datetime(hist.index)
        # yfinance는 tz-aware(UTC) 또는 시각이 포함된 Timestamp를 반환할 수 있음
        # pd.Timestamp('YYYY-MM-DD')는 자정(00:00:00)이므로
        # tz 제거 후 normalize()로 시각을 자정으로 통일해야 날짜 비교가 정확함
        if hist.index.tz is not None:
            hist.index = hist.index.tz_convert(None)
        hist.index = hist.index.normalize()
    return hist
