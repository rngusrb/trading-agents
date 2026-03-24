"""
engine.py — 백테스팅 엔진
AAPL 2024.01~03 기간 백테스팅 실행
"""
import os
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from dotenv import load_dotenv

from tools.market_data import fetch_historical_data
from backtest.metrics import calculate_metrics
from graph.workflow import run_pipeline
from models.schemas import TradeDecision

load_dotenv()


class BacktestEngine:
    """
    트레이딩 에이전트 백테스팅 엔진

    매 거래일마다 파이프라인을 실행하고 성과를 측정합니다.
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        commission_rate: float = 0.001,
        config: dict = None
    ):
        """
        Args:
            initial_capital: 초기 투자 자본 (달러)
            commission_rate: 거래 수수료율 (0.1%)
            config: 시스템 설정 (선택, 기본값: DEFAULT_CONFIG)
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.config = config
        self.reset()

    def reset(self):
        """상태 초기화"""
        self.cash = self.initial_capital
        self.holdings: dict[str, float] = {}  # ticker -> shares (long)
        self.short_positions: dict[str, float] = {}  # ticker -> shares (short)
        self.trades: list[dict] = []
        self.portfolio_values: list[dict] = []

    def run(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        trading_days_interval: int = 5
    ) -> dict:
        """
        백테스팅 실행

        Args:
            ticker: 종목 코드
            start_date: 시작 날짜 YYYY-MM-DD
            end_date: 종료 날짜 YYYY-MM-DD
            trading_days_interval: 거래 판단 주기 (영업일)

        Returns:
            dict: 백테스팅 결과 (수익률, 거래 내역 등)
        """
        print(f"\n{'='*60}")
        print(f"백테스팅 시작: {ticker} ({start_date} ~ {end_date})")
        print(f"초기 자본: ${self.initial_capital:,.0f}")
        print(f"{'='*60}")

        # 히스토리컬 가격 데이터 로드
        price_df = fetch_historical_data(ticker, start_date, end_date)
        if price_df.empty:
            print("ERROR: 가격 데이터 없음")
            return {}

        trading_dates = self._get_trading_dates(price_df, trading_days_interval)
        print(f"거래일 수: {len(trading_dates)}일")

        for i, date_str in enumerate(trading_dates):
            print(f"\n[{i+1}/{len(trading_dates)}] {date_str} 분석 중...")

            try:
                # 파이프라인 실행
                final_state = run_pipeline(ticker, date_str, config=self.config)
                decision = final_state.get('trade_decision')

                if decision:
                    self._execute_trade(decision, price_df, date_str)
                    self._record_portfolio_value(ticker, price_df, date_str)
                    print(f"  → {decision.action.upper()} | 승인: {decision.approved} | 리스크: {decision.risk_score:.0%}")
                else:
                    print("  → 결정 없음 (hold)")

            except Exception as e:
                print(f"  ERROR: {e}")
                self._record_portfolio_value(ticker, price_df, date_str)

        # 최종 포지션 청산
        self._liquidate_all(ticker, price_df, end_date)

        return self._compile_results(ticker, start_date, end_date, price_df)

    def _get_trading_dates(self, df: pd.DataFrame, interval: int) -> list[str]:
        """거래 판단 날짜 목록 추출"""
        all_dates = df.index.strftime('%Y-%m-%d').tolist()
        return all_dates[::interval]

    def _execute_trade(
        self,
        decision: TradeDecision,
        price_df: pd.DataFrame,
        date_str: str
    ):
        """거래 실행"""
        if not decision.approved:
            return

        # 날짜에 맞는 가격 찾기
        price = self._get_price_on_date(price_df, date_str)
        if price is None:
            return

        ticker = decision.ticker
        action = decision.action
        quantity_ratio = decision.quantity

        if action == 'buy' and quantity_ratio > 0:
            # 매수: cash의 quantity_ratio만큼 투자
            invest_amount = self.cash * quantity_ratio
            cost = invest_amount * (1 + self.commission_rate)
            if cost <= self.cash:
                shares = invest_amount / price
                self.cash -= cost
                self.holdings[ticker] = self.holdings.get(ticker, 0) + shares
                self.trades.append({
                    'date': date_str,
                    'action': 'buy',
                    'ticker': ticker,
                    'shares': round(shares, 4),
                    'price': price,
                    'value': round(invest_amount, 2)
                })

        elif action == 'sell' and ticker in self.holdings:
            # 매도: 보유 주식의 quantity_ratio만큼 매도
            shares_to_sell = self.holdings[ticker] * quantity_ratio
            sell_amount = shares_to_sell * price * (1 - self.commission_rate)
            self.cash += sell_amount
            self.holdings[ticker] -= shares_to_sell
            if self.holdings[ticker] < 0.001:
                del self.holdings[ticker]
            self.trades.append({
                'date': date_str,
                'action': 'sell',
                'ticker': ticker,
                'shares': round(shares_to_sell, 4),
                'price': price,
                'value': round(sell_amount, 2)
            })

        elif action == 'short' and quantity_ratio > 0:
            # 숏 포지션: 주식을 빌려서 매도
            short_value = self.cash * quantity_ratio
            shares = short_value / price
            self.short_positions[ticker] = self.short_positions.get(ticker, 0) + shares
            self.cash += short_value * (1 - self.commission_rate)
            self.trades.append({
                'date': date_str,
                'action': 'short',
                'ticker': ticker,
                'shares': round(shares, 4),
                'price': price,
                'value': round(short_value, 2)
            })

        elif action == 'cover' and ticker in self.short_positions:
            # 숏 커버: 빌린 주식 상환
            shares_to_cover = self.short_positions[ticker] * quantity_ratio
            cost = shares_to_cover * price * (1 + self.commission_rate)
            self.cash -= cost
            self.short_positions[ticker] -= shares_to_cover
            if self.short_positions[ticker] < 0.001:
                del self.short_positions[ticker]
            self.trades.append({
                'date': date_str,
                'action': 'cover',
                'ticker': ticker,
                'shares': round(shares_to_cover, 4),
                'price': price,
                'value': round(cost, 2)
            })

    def _get_price_on_date(self, df: pd.DataFrame, date_str: str) -> Optional[float]:
        """특정 날짜 종가 조회"""
        try:
            # 날짜 변환
            target = pd.Timestamp(date_str)
            if target in df.index:
                return float(df.loc[target, 'Close'])
            # 가장 가까운 이전 날짜 사용
            available = df.index[df.index <= target]
            if not available.empty:
                return float(df.loc[available[-1], 'Close'])
        except Exception:
            pass
        return None

    def _record_portfolio_value(
        self,
        ticker: str,
        price_df: pd.DataFrame,
        date_str: str
    ):
        """포트폴리오 가치 기록"""
        price = self._get_price_on_date(price_df, date_str)
        holdings_value = 0.0
        if price and ticker in self.holdings:
            holdings_value = self.holdings[ticker] * price
        # 숏 포지션은 부채 (현재가격 * 보유수량)
        short_liability = 0.0
        if price and ticker in self.short_positions:
            short_liability = self.short_positions[ticker] * price
        total_value = self.cash + holdings_value - short_liability
        self.portfolio_values.append({
            'date': date_str,
            'cash': round(self.cash, 2),
            'holdings_value': round(holdings_value, 2),
            'short_liability': round(short_liability, 2),
            'total_value': round(total_value, 2)
        })

    def _liquidate_all(self, ticker: str, price_df: pd.DataFrame, end_date: str):
        """종료 시 모든 포지션 청산"""
        price = self._get_price_on_date(price_df, end_date)
        if ticker in self.holdings and self.holdings[ticker] > 0:
            if price:
                sell_amount = self.holdings[ticker] * price * (1 - self.commission_rate)
                self.cash += sell_amount
                self.trades.append({
                    'date': end_date,
                    'action': 'sell (liquidate)',
                    'ticker': ticker,
                    'shares': round(self.holdings[ticker], 4),
                    'price': price,
                    'value': round(sell_amount, 2)
                })
                del self.holdings[ticker]
        # 숏 포지션 청산 (커버)
        if ticker in self.short_positions and self.short_positions[ticker] > 0:
            if price:
                cover_cost = self.short_positions[ticker] * price * (1 + self.commission_rate)
                self.cash -= cover_cost
                self.trades.append({
                    'date': end_date,
                    'action': 'cover (liquidate)',
                    'ticker': ticker,
                    'shares': round(self.short_positions[ticker], 4),
                    'price': price,
                    'value': round(cover_cost, 2)
                })
                del self.short_positions[ticker]

    def _compile_results(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        price_df: pd.DataFrame
    ) -> dict:
        """백테스팅 결과 집계"""
        final_value = self.cash
        metrics = calculate_metrics(
            initial_capital=self.initial_capital,
            final_value=final_value,
            portfolio_values=self.portfolio_values,
            trades=self.trades
        )

        # Buy & Hold 벤치마크
        start_price = self._get_price_on_date(price_df, start_date)
        end_price = self._get_price_on_date(price_df, end_date)
        bnh_return = 0.0
        if start_price and end_price:
            bnh_return = (end_price - start_price) / start_price * 100

        results = {
            'ticker': ticker,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': self.initial_capital,
            'final_value': round(final_value, 2),
            'total_return_pct': metrics.get('total_return_pct', 0),
            'buy_and_hold_return_pct': round(bnh_return, 2),
            'sharpe_ratio': metrics.get('sharpe_ratio', 0),
            'max_drawdown_pct': metrics.get('max_drawdown_pct', 0),
            'total_trades': len(self.trades),
            'win_rate': metrics.get('win_rate', 0),
            'trades': self.trades,
            'portfolio_values': self.portfolio_values
        }

        self._print_summary(results)
        return results

    def _print_summary(self, results: dict):
        """결과 요약 출력"""
        print(f"\n{'='*60}")
        print(f"백테스팅 결과 요약: {results['ticker']}")
        print(f"{'='*60}")
        print(f"기간: {results['start_date']} ~ {results['end_date']}")
        print(f"초기 자본: ${results['initial_capital']:,.0f}")
        print(f"최종 가치: ${results['final_value']:,.0f}")
        print(f"수익률: {results['total_return_pct']:.2f}%")
        print(f"Buy & Hold: {results['buy_and_hold_return_pct']:.2f}%")
        print(f"샤프 비율: {results['sharpe_ratio']:.3f}")
        print(f"최대 낙폭: {results['max_drawdown_pct']:.2f}%")
        print(f"총 거래: {results['total_trades']}회")
        print(f"승률: {results['win_rate']:.1f}%")
        print(f"{'='*60}\n")
