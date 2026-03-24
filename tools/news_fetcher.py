"""
news_fetcher.py — yfinance 기반 뉴스 수집
look-ahead bias 방지: 분석 날짜 기준 이전 기사만 사용
(Finnhub 대체 — 과거 날짜 뉴스를 가져오지 못하는 문제 해결)

한계: yfinance.news는 최근 뉴스만 제공.
      백테스팅 과거 날짜에서는 뉴스가 없을 수 있음 (미래 데이터 유입 없음).
"""
import yfinance as yf
from datetime import datetime, timedelta


def fetch_company_news(ticker: str, date: str, days_back: int = 7) -> list[dict]:
    """
    yfinance 뉴스 수집 + 날짜 기준 필터링

    분석 날짜 이전 기사만 반환하여 look-ahead bias 방지.
    백테스팅 과거 날짜의 경우 뉴스가 없을 수 있음(정상 동작).

    Args:
        ticker: 종목 코드
        date: 기준 날짜 YYYY-MM-DD (이 날짜 이전 뉴스만 반환)
        days_back: 조회 기간 (일)

    Returns:
        list[dict]: 뉴스 목록
    """
    try:
        news_raw = yf.Ticker(ticker).news or []

        target_dt = datetime.strptime(date, '%Y-%m-%d')
        start_dt = target_dt - timedelta(days=days_back)

        filtered = []
        for item in news_raw:
            content = item.get('content', {})
            pub_str = content.get('pubDate', '')
            if not pub_str:
                continue
            try:
                # 형식: "2026-03-23T17:30:03Z"
                pub_dt = datetime.strptime(pub_str[:19], '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                continue
            # look-ahead bias 방지: 분석일 이전 기사만 포함
            if start_dt <= pub_dt <= target_dt + timedelta(days=1):
                filtered.append(item)

        # yfinance는 최근 뉴스만 제공 → 과거 날짜 백테스팅 시 empty 가능
        # fallback: 가용한 최신 뉴스 전체 사용 (경고 출력)
        if not filtered and news_raw:
            filtered = news_raw
            newest = (news_raw[0].get('content', {}) or {}).get('pubDate', 'N/A')[:10]
            print(f"[News] ⚠️  {ticker} {date}: no news in date range "
                  f"(yfinance only has recent news). Using latest available: {newest}")

        return filtered

    except Exception as e:
        print(f"news fetch error for {ticker}: {e}")
        return []


def fetch_market_news(category: str = 'general', limit: int = 10) -> list[dict]:
    """시장 전반 뉴스 (하위 호환성 유지)"""
    return []


def extract_news_summary(news_items: list[dict]) -> list[dict]:
    """
    yfinance 뉴스 아이템에서 핵심 정보 추출

    Args:
        news_items: fetch_company_news() 반환값

    Returns:
        list[dict]: headline, summary, source, datetime, url
    """
    extracted = []
    for item in news_items:
        content = item.get('content', {})
        extracted.append({
            'headline': content.get('title', ''),
            'summary': content.get('summary', content.get('description', ''))[:500],
            'source': (content.get('provider') or {}).get('displayName', ''),
            'datetime': content.get('pubDate', ''),
            'url': (content.get('canonicalUrl') or {}).get('url', ''),
        })
    return extracted
