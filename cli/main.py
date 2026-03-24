"""
cli/main.py — TradingAgents CLI 인터페이스
실시간 진행상황 표시 + 모델/리서치 깊이 선택
"""
import argparse
import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from config import get_config


def parse_args():
    """CLI 인수 파싱"""
    parser = argparse.ArgumentParser(
        description='TradingAgents — LangGraph 멀티에이전트 트레이딩 시스템',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python cli/main.py --ticker AAPL --date 2024-01-15
  python cli/main.py --mode backtest --ticker AAPL --start 2024-01-02 --end 2024-01-31
  python cli/main.py --ticker GOOGL --quick-think claude-haiku-4-5-20251001 --deep-think claude-opus-4-6
        """
    )
    parser.add_argument('--mode', choices=['single', 'backtest'], default='single')
    parser.add_argument('--ticker', default='AAPL')
    parser.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument('--start', default='2024-01-02')
    parser.add_argument('--end', default='2024-03-29')
    parser.add_argument('--capital', type=float, default=100_000.0)
    parser.add_argument('--interval', type=int, default=1, help='거래 판단 주기 (영업일)')
    parser.add_argument('--quick-think', default='claude-haiku-4-5-20251001',
                        dest='quick_think', help='빠른 분석 모델 (애널리스트용)')
    parser.add_argument('--deep-think', default='claude-opus-4-6',
                        dest='deep_think', help='심층 분석 모델 (Fund Manager용)')
    parser.add_argument('--decision', default='claude-sonnet-4-6',
                        help='의사결정 모델 (Researcher/Trader용)')
    parser.add_argument('--debate-rounds', type=int, default=1, dest='debate_rounds',
                        help='Bull/Bear 토론 라운드 수')
    parser.add_argument('--report', action='store_true', help='HTML 리포트 생성')
    parser.add_argument('--provider', default='anthropic', help='LLM 프로바이더')
    return parser.parse_args()


def print_header(ticker: str, mode: str):
    """헤더 출력"""
    print("\n" + "="*60)
    print("  TradingAgents — LangGraph 멀티에이전트 트레이딩")
    print("="*60)
    print(f"  종목: {ticker} | 모드: {mode.upper()}")
    print("="*60 + "\n")


def run_single(args, config: dict):
    """단일 분석 실행"""
    from graph.workflow import run_pipeline

    print_header(args.ticker, 'single')
    print(f"[->] {args.ticker} @ {args.date} 분석 시작...\n")

    start_time = time.time()

    print("[1/7] 시장 데이터 수집...")
    final_state = run_pipeline(args.ticker, args.date, config=config)
    elapsed = time.time() - start_time

    decision = final_state.get('trade_decision')
    analyst_reports = final_state.get('analyst_reports', [])
    research_report = final_state.get('research_report')

    print(f"\n{'='*60}")
    print("  분석 결과 요약")
    print(f"{'='*60}")

    # Analyst signals
    print("\n[애널리스트 신호]")
    for r in analyst_reports:
        icon = 'UP' if r.signal == 'bullish' else ('DOWN' if r.signal == 'bearish' else '->')
        print(f"  [{icon}] {r.analyst_type:15s}: {r.signal:8s} ({r.confidence:.0%})")

    if research_report:
        print(f"\n[리서치 합의] {research_report.consensus.upper()} (확신도: {research_report.conviction:.0%})")

    if decision:
        action_icons = {'buy': 'BUY', 'sell': 'SELL', 'short': 'SHORT', 'cover': 'COVER', 'hold': 'HOLD'}
        icon = action_icons.get(decision.action, '?')
        print(f"\n[최종 결정]")
        print(f"  [{icon}] {decision.action.upper()} | 비중: {decision.quantity:.0%} | 리스크: {decision.risk_score:.0%} | {'승인' if decision.approved else '거절'}")
        print(f"  근거: {decision.reasoning[:200]}...")

    print(f"\n소요 시간: {elapsed:.1f}초")

    if args.report:
        print("\n[HTML 리포트 생성 중...]")
        from reports.generator import generate_report
        path = generate_report(final_state, mode='single')
        print(f"리포트 저장: {path}")

    return final_state


def run_backtest(args, config: dict):
    """백테스팅 실행"""
    from backtest.engine import BacktestEngine
    from backtest.metrics import format_results_table

    print_header(args.ticker, 'backtest')
    print(f"[->] {args.ticker} 백테스팅: {args.start} ~ {args.end}\n")

    engine = BacktestEngine(initial_capital=args.capital, config=config)
    results = engine.run(
        ticker=args.ticker,
        start_date=args.start,
        end_date=args.end,
        trading_days_interval=args.interval
    )

    if results:
        print(format_results_table(results))
        print(f"\n논문 벤치마크 (AAPL 2024 Q1): +26.62%")
        print(f"우리 시스템:                   {results.get('total_return_pct', 0):+.2f}%")

        if args.report:
            print("\n[HTML 리포트 생성 중...]")
            from reports.generator import generate_report
            path = generate_report(results, mode='backtest')
            print(f"리포트 저장: {path}")

    return results


def main():
    """메인 진입점"""
    args = parse_args()
    config = get_config({
        "llm_provider": args.provider,
        "quick_think_llm": args.quick_think,
        "deep_think_llm": args.deep_think,
        "decision_llm": args.decision,
        "max_debate_rounds": args.debate_rounds,
    })

    print(f"\n[설정]")
    print(f"  Quick-think LLM : {config['quick_think_llm']}")
    print(f"  Decision LLM    : {config['decision_llm']}")
    print(f"  Deep-think LLM  : {config['deep_think_llm']}")
    print(f"  토론 라운드      : {config['max_debate_rounds']}")

    if args.mode == 'backtest':
        run_backtest(args, config)
    else:
        run_single(args, config)


if __name__ == '__main__':
    main()
