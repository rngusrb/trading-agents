"""
metrics.py — 백테스팅 성과 지표 계산
Sharpe Ratio, Max Drawdown, Win Rate 등
"""
import math
from typing import Optional


def calculate_metrics(
    initial_capital: float,
    final_value: float,
    portfolio_values: list[dict],
    trades: list[dict],
    risk_free_rate: float = 0.05
) -> dict:
    """
    백테스팅 성과 지표 계산

    Args:
        initial_capital: 초기 자본
        final_value: 최종 포트폴리오 가치
        portfolio_values: 날짜별 포트폴리오 가치 기록
        trades: 거래 내역
        risk_free_rate: 무위험 수익률 (연간, 기본 5%)

    Returns:
        dict: total_return_pct, sharpe_ratio, max_drawdown_pct, win_rate
    """
    metrics = {}

    # 총 수익률
    if initial_capital > 0:
        metrics['total_return_pct'] = round(
            (final_value - initial_capital) / initial_capital * 100, 2
        )
    else:
        metrics['total_return_pct'] = 0.0

    # 포트폴리오 가치 시계열
    values = [v['total_value'] for v in portfolio_values]

    if len(values) >= 2:
        # 일별 수익률
        daily_returns = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                ret = (values[i] - values[i-1]) / values[i-1]
                daily_returns.append(ret)

        # 샤프 비율 (연환산)
        metrics['sharpe_ratio'] = _calculate_sharpe(daily_returns, risk_free_rate)

        # 최대 낙폭
        metrics['max_drawdown_pct'] = _calculate_max_drawdown(values)
    else:
        metrics['sharpe_ratio'] = 0.0
        metrics['max_drawdown_pct'] = 0.0

    # 승률 (매수/매도 쌍 기준)
    metrics['win_rate'] = _calculate_win_rate(trades)

    return metrics


def _calculate_sharpe(daily_returns: list[float], risk_free_rate: float) -> float:
    """
    샤프 비율 계산

    Args:
        daily_returns: 일별 수익률 목록
        risk_free_rate: 연간 무위험 수익률

    Returns:
        float: 샤프 비율 (연환산)
    """
    if not daily_returns:
        return 0.0

    n = len(daily_returns)
    mean_return = sum(daily_returns) / n
    daily_rf = risk_free_rate / 252

    excess_returns = [r - daily_rf for r in daily_returns]
    mean_excess = sum(excess_returns) / n

    variance = sum((r - mean_excess) ** 2 for r in excess_returns) / max(n - 1, 1)
    std_dev = math.sqrt(variance) if variance > 0 else 0

    if std_dev == 0:
        return 0.0

    # 연환산 (√252)
    return round(mean_excess / std_dev * math.sqrt(252), 3)


def _calculate_max_drawdown(values: list[float]) -> float:
    """
    최대 낙폭 계산

    Args:
        values: 포트폴리오 가치 시계열

    Returns:
        float: 최대 낙폭 (%)
    """
    if not values:
        return 0.0

    peak = values[0]
    max_dd = 0.0

    for value in values:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (peak - value) / peak * 100
            max_dd = max(max_dd, drawdown)

    return round(max_dd, 2)


def _calculate_win_rate(trades: list[dict]) -> float:
    """
    승률 계산 (매수 후 매도 쌍 기준)

    Args:
        trades: 거래 내역

    Returns:
        float: 승률 (%)
    """
    buy_trades = [t for t in trades if t['action'] == 'buy']
    sell_trades = [t for t in trades if 'sell' in t['action']]

    if not buy_trades or not sell_trades:
        return 0.0

    # 매수/매도 쌍 매칭
    pairs = min(len(buy_trades), len(sell_trades))
    wins = 0

    for i in range(pairs):
        buy_price = buy_trades[i]['price']
        sell_price = sell_trades[i]['price']
        if sell_price > buy_price:
            wins += 1

    return round(wins / pairs * 100, 1) if pairs > 0 else 0.0


def format_results_table(results: dict) -> str:
    """
    결과를 테이블 형식 문자열로 포맷

    Args:
        results: backtest engine 결과 dict

    Returns:
        str: 포맷된 테이블
    """
    lines = [
        "┌─────────────────────────────────────────┐",
        f"│  백테스팅 결과: {results.get('ticker', 'N/A'):<25}│",
        "├─────────────────────────────────────────┤",
        f"│  기간: {results.get('start_date')} ~ {results.get('end_date')}  │",
        f"│  총 수익률:    {results.get('total_return_pct', 0):>8.2f}%              │",
        f"│  B&H 수익률:   {results.get('buy_and_hold_return_pct', 0):>8.2f}%              │",
        f"│  샤프 비율:    {results.get('sharpe_ratio', 0):>8.3f}               │",
        f"│  최대 낙폭:    {results.get('max_drawdown_pct', 0):>8.2f}%              │",
        f"│  총 거래수:    {results.get('total_trades', 0):>8}회               │",
        f"│  승률:         {results.get('win_rate', 0):>8.1f}%              │",
        "└─────────────────────────────────────────┘",
    ]
    return "\n".join(lines)
