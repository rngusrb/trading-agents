"""
fundamentals.py — yfinance 기반 펀더멘털 데이터 수집
look-ahead bias 방지: earnings_dates 실제 발표일 기준 필터링
(Finnhub 대체 — 현재 시점 데이터 반환 문제 해결)
"""
import pandas as pd
import yfinance as yf
from typing import Dict, Any, Optional


def _strip_tz(ts: pd.Timestamp) -> pd.Timestamp:
    """Timestamp에서 timezone 제거"""
    if ts.tz is not None:
        return ts.tz_convert(None)
    return ts


def _valid_cols_by_earnings(
    df: pd.DataFrame,
    ticker_obj,
    date: str,
    fallback_lag_days: int = 45,
) -> list:
    """
    earnings_dates 실제 발표일 기준으로 분석 날짜 이전에 공개된 분기만 반환.

    로직:
      1. ticker.earnings_dates에서 각 분기의 실제 발표일 조회
      2. 분기말 이후 90일 이내 발표일이 analysis_date 이전인 분기만 허용
      3. earnings_dates에 해당 분기 정보 없으면 fallback_lag_days 기준 사용
      4. 결과가 empty면 _all_cols_sorted fallback (경고 출력)

    예시 (분석일 2025-01-15):
      2024-12-31 분기 → 발표일 2025-01-30 > 2025-01-15 → ❌
      2024-09-30 분기 → 발표일 2024-10-31 < 2025-01-15 → ✅
    """
    if df.empty:
        return []

    analysis_dt = pd.Timestamp(date)

    # earnings_dates 인덱스 로드 (tz-naive)
    ann_index: pd.DatetimeIndex | None = None
    try:
        ed = ticker_obj.earnings_dates
        if ed is not None and not ed.empty:
            ann_index = ed.index.tz_convert(None)
    except Exception:
        pass

    valid = []
    for col in df.columns:
        q_end = _strip_tz(pd.Timestamp(col))

        if ann_index is not None:
            # 이 분기의 실제 발표일 찾기: 분기말 ~ +90일 범위
            window_end = q_end + pd.Timedelta(days=90)
            mask = (ann_index >= q_end) & (ann_index <= window_end)
            candidates = ann_index[mask]

            if len(candidates) > 0:
                ann_date = candidates.min()  # 가장 이른 발표일
                if ann_date < analysis_dt:
                    valid.append(col)
                continue  # 발표일 정보 있으면 lag 방식 skip

        # earnings_dates에 정보 없는 분기 → fallback: lag_days 방식
        cutoff = analysis_dt - pd.Timedelta(days=fallback_lag_days)
        if q_end <= cutoff:
            valid.append(col)

    return sorted(valid, key=lambda c: pd.Timestamp(c), reverse=True)


def _all_cols_sorted(df: pd.DataFrame) -> list:
    """DataFrame 컬럼 전체를 최신순 정렬 (timezone 제거, 오래된 것 우선)"""
    cols = []
    for col in df.columns:
        ts = _strip_tz(pd.Timestamp(col))
        cols.append((ts, col))
    return [c for _, c in sorted(cols, reverse=True)]


def _get(df: pd.DataFrame, row: str, col) -> Optional[float]:
    """DataFrame에서 값 안전 추출"""
    try:
        if row in df.index and col in df.columns:
            v = df.loc[row, col]
            return float(v) if pd.notna(v) else None
    except Exception:
        pass
    return None


def _ttm(df: pd.DataFrame, row: str, cols: list) -> Optional[float]:
    """최근 4분기 합산 (Trailing Twelve Months)"""
    if row not in df.index:
        return None
    vals = [_get(df, row, c) for c in cols[:4]]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def fetch_company_profile(ticker: str, date: str = None) -> Dict[str, Any]:
    """
    기업 프로필 조회 (정적 정보, look-ahead bias 무관)

    Args:
        ticker: 종목 코드
        date: 분석 날짜 (미사용, 하위 호환성)

    Returns:
        dict: 기업 기본 정보
    """
    try:
        info = yf.Ticker(ticker).info
        return {
            'name': info.get('shortName') or info.get('longName') or ticker,
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'marketCapitalization': round((info.get('marketCap') or 0) / 1e9, 2),
            'country': info.get('country', 'N/A'),
        }
    except Exception as e:
        print(f"company profile fetch error for {ticker}: {e}")
        return {}


def fetch_basic_financials(ticker: str, date: str) -> Dict[str, Any]:
    """
    분석 날짜 기준 실제 발표된 분기 재무 지표 (look-ahead bias 방지)

    earnings_dates 실제 발표일 기준으로 필터링.
    yfinance 한계: 최근 5분기만 제공 → 과거 날짜 백테스팅 시 empty 가능.
    이 경우 가장 오래된 분기 데이터를 fallback으로 사용 (경고 출력).

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD

    Returns:
        dict: TTM 매출/순이익/EPS, ROE, D/E, 매출성장률, 최신 분기일
    """
    result: Dict[str, Any] = {}
    try:
        t = yf.Ticker(ticker)

        # ── Income Statement ─────────────────────────────
        qf = t.quarterly_financials  # rows=지표, cols=분기말 날짜
        vcols_qf = _valid_cols_by_earnings(qf, t, date) if not qf.empty else []

        # yfinance 5분기 한계 fallback
        # 가용 분기 중 분석일에 가장 가까운 oldest 1개만 사용 (미래 오염 최소화)
        if not vcols_qf and not qf.empty:
            all_sorted = _all_cols_sorted(qf)  # newest-first
            oldest_col = all_sorted[-1]         # oldest available
            vcols_qf = [oldest_col]
            oldest_str = str(_strip_tz(pd.Timestamp(oldest_col)))[:10]
            print(f"[Fundamentals] ⚠️  {ticker} {date}: no pre-announcement quarters "
                  f"(yfinance 5Q limit). Fallback to closest: {oldest_str}")

        if vcols_qf:
            result['latest_quarter'] = str(_strip_tz(pd.Timestamp(vcols_qf[0])))[:10]

            revenue_ttm = _ttm(qf, 'Total Revenue', vcols_qf)
            net_income_ttm = _ttm(qf, 'Net Income', vcols_qf)
            eps_ttm = _ttm(qf, 'Diluted EPS', vcols_qf) or _ttm(qf, 'Basic EPS', vcols_qf)

            if revenue_ttm is not None:
                result['revenue_ttm'] = revenue_ttm
            if net_income_ttm is not None:
                result['net_income_ttm'] = net_income_ttm
            if eps_ttm is not None:
                result['eps_ttm'] = round(eps_ttm, 4)

            # 매출 성장률 YoY (최근 4Q vs 1년 전 4Q)
            if len(vcols_qf) >= 8:
                prior_rev = _ttm(qf, 'Total Revenue', vcols_qf[4:8])
                if revenue_ttm and prior_rev and prior_rev != 0:
                    result['revenue_growth_yoy'] = round(
                        (revenue_ttm - prior_rev) / abs(prior_rev) * 100, 2
                    )

        # ── Balance Sheet ─────────────────────────────────
        qbs = t.quarterly_balance_sheet
        vcols_bs = _valid_cols_by_earnings(qbs, t, date) if not qbs.empty else []
        if not vcols_bs and not qbs.empty:
            all_bs = _all_cols_sorted(qbs)
            vcols_bs = [all_bs[-1]]  # oldest available (closest to analysis_date)

        if vcols_bs:
            latest_bs = vcols_bs[0]
            equity = _get(qbs, 'Stockholders Equity', latest_bs) \
                  or _get(qbs, 'Common Stock Equity', latest_bs)
            total_debt = _get(qbs, 'Total Debt', latest_bs) or (
                (_get(qbs, 'Long Term Debt', latest_bs) or 0)
                + (_get(qbs, 'Current Debt', latest_bs) or 0)
            ) or None

            if equity is not None:
                result['stockholders_equity'] = equity
            if total_debt is not None:
                result['total_debt'] = total_debt

            # ROE = 순이익(TTM) / 자기자본
            if result.get('net_income_ttm') and equity and equity != 0:
                result['roe'] = round(result['net_income_ttm'] / equity * 100, 2)

            # D/E = 부채 / 자기자본
            if total_debt and equity and equity != 0:
                result['debt_to_equity'] = round(total_debt / equity, 3)

    except Exception as e:
        print(f"basic financials fetch error for {ticker}: {e}")

    return result


def fetch_earnings(ticker: str, date: str) -> list[Dict[str, Any]]:
    """
    분기별 EPS 실적 (earnings_dates 기준 발표일 이전 데이터만 반환)

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD

    Returns:
        list[dict]: 최근 4분기 EPS (period, actual)
    """
    try:
        t = yf.Ticker(ticker)
        qf = t.quarterly_financials
        if qf.empty:
            return []

        vcols = _valid_cols_by_earnings(qf, t, date)
        if not vcols:
            all_sorted = _all_cols_sorted(qf)
            vcols = [all_sorted[-1]]  # oldest available

        results = []
        for col in vcols[:4]:
            eps = _get(qf, 'Diluted EPS', col) or _get(qf, 'Basic EPS', col)
            results.append({
                'period': str(_strip_tz(pd.Timestamp(col)))[:10],
                'actual': round(eps, 4) if eps is not None else None,
                'estimate': None,
                'surprisePercent': None,
            })
        return results

    except Exception as e:
        print(f"earnings fetch error for {ticker}: {e}")
        return []


def fetch_recommendation_trends(ticker: str, date: str = None) -> list[Dict[str, Any]]:
    """
    애널리스트 추천 추이 (하위 호환성 유지, 빈 리스트 반환)
    yfinance 기본 API로는 과거 날짜 기준 추천 데이터 없음
    """
    return []


def get_fundamentals(ticker: str, date: str) -> Dict[str, Any]:
    """
    fetch_basic_financials 편의 래퍼

    Args:
        ticker: 종목 코드
        date: 분석 날짜 YYYY-MM-DD

    Returns:
        dict: 재무 지표 (latest_quarter, revenue_ttm, eps_ttm, roe, debt_to_equity 등)
    """
    return fetch_basic_financials(ticker, date)
