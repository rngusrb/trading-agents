"""
main.py — TradingAgents 백테스팅 진입점
AAPL 2024.01~03 백테스팅 실행
논문 벤치마크: AAPL +26.62%
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()


def run_backtest(
    ticker: str = "AAPL",
    start_date: str = "2024-01-02",
    end_date: str = "2024-03-29",
    initial_capital: float = 100_000.0
):
    """
    백테스팅 실행

    Args:
        ticker: 종목 코드
        start_date: 시작 날짜
        end_date: 종료 날짜
        initial_capital: 초기 자본
    """
    from backtest.engine import BacktestEngine
    from backtest.metrics import format_results_table

    engine = BacktestEngine(initial_capital=initial_capital)
    results = engine.run(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        trading_days_interval=5  # 매주 금요일 분석
    )

    if results:
        print(format_results_table(results))
        print(f"\n논문 벤치마크 (AAPL 2024 Q1): +26.62%")
        print(f"우리 시스템:                   {results.get('total_return_pct', 0):+.2f}%")
    return results


def run_single_analysis(ticker: str = "AAPL", date: str = "2024-01-15"):
    """
    단일 날짜 분석 실행 (end-to-end 파이프라인 테스트)

    Args:
        ticker: 종목 코드
        date: 분석 날짜
    """
    from graph.workflow import run_pipeline

    print(f"\n단일 분석: {ticker} @ {date}")
    print("="*50)

    final_state = run_pipeline(ticker, date)
    decision = final_state.get('trade_decision')

    if decision:
        print(f"\n최종 트레이딩 결정:")
        print(f"  종목:     {decision.ticker}")
        print(f"  날짜:     {decision.date}")
        print(f"  액션:     {decision.action.upper()}")
        print(f"  비중:     {decision.quantity:.0%}")
        print(f"  리스크:   {decision.risk_score:.0%}")
        print(f"  승인:     {'✅ 승인' if decision.approved else '❌ 거절'}")
        print(f"  근거:     {decision.reasoning[:200]}...")
    else:
        print("결정 생성 실패")

    return final_state


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='TradingAgents 백테스팅')
    parser.add_argument('--mode', choices=['backtest', 'single'], default='single',
                        help='실행 모드 (backtest: 전체 백테스팅, single: 단일 분석)')
    parser.add_argument('--ticker', default='AAPL', help='종목 코드')
    parser.add_argument('--start', default='2024-01-02', help='시작 날짜 (백테스팅)')
    parser.add_argument('--end', default='2024-03-29', help='종료 날짜 (백테스팅)')
    parser.add_argument('--date', default='2024-01-15', help='분석 날짜 (단일 모드)')
    parser.add_argument('--capital', type=float, default=100000.0, help='초기 자본')

    args = parser.parse_args()

    if args.mode == 'backtest':
        run_backtest(args.ticker, args.start, args.end, args.capital)
    else:
        run_single_analysis(args.ticker, args.date)
