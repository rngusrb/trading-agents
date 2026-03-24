"""
test_backtest.py — 백테스팅 엔진 + 워크플로우 통합 Mock 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from models.schemas import MarketData, AnalystReport, ResearchReport, TradeDecision


def make_mock_final_state(action="buy", approved=True, quantity=0.5):
    """Mock 최종 파이프라인 상태 생성"""
    reports = [
        AnalystReport(
            analyst_type=t, ticker="AAPL", date="2024-01-15",
            signal="bullish", confidence=0.75,
            summary=f"{t} analysis", key_points=["p1", "p2", "p3"]
        )
        for t in ['fundamentals', 'sentiment', 'news', 'technical']
    ]
    research = ResearchReport(
        ticker="AAPL", date="2024-01-15",
        bull_case="Strong bull case", bear_case="Weak bear case",
        consensus="buy", conviction=0.72
    )
    decision = TradeDecision(
        ticker="AAPL", date="2024-01-15",
        action=action, quantity=quantity,
        reasoning="Strong signals", risk_score=0.3, approved=approved
    )
    return {
        'ticker': 'AAPL',
        'date': '2024-01-15',
        'market_data': MarketData(
            ticker="AAPL", date="2024-01-15",
            open=185.0, high=190.0, low=183.0, close=188.5, volume=50000000
        ),
        'analyst_reports': reports,
        'research_report': research,
        'trade_decision': decision,
        'messages': [],
        'next_agent': 'done'
    }


class TestMetrics:
    """성과 지표 계산 테스트"""

    def test_total_return(self):
        from backtest.metrics import calculate_metrics

        portfolio_values = [
            {'date': '2024-01-15', 'total_value': 100000},
            {'date': '2024-01-22', 'total_value': 105000},
            {'date': '2024-01-29', 'total_value': 110000},
        ]
        result = calculate_metrics(100000, 110000, portfolio_values, [])
        assert result['total_return_pct'] == 10.0

    def test_max_drawdown(self):
        from backtest.metrics import _calculate_max_drawdown

        values = [100000, 110000, 90000, 95000]
        dd = _calculate_max_drawdown(values)
        # 110000에서 90000으로 낙폭 = 18.18%
        assert dd > 18.0
        assert dd < 19.0

    def test_sharpe_ratio(self):
        from backtest.metrics import _calculate_sharpe

        # 양의 수익률 시계열 → 양의 샤프
        returns = [0.01, 0.02, 0.005, 0.015, 0.01] * 10
        sharpe = _calculate_sharpe(returns, 0.05)
        assert sharpe > 0

    def test_win_rate(self):
        from backtest.metrics import _calculate_win_rate

        trades = [
            {'action': 'buy', 'price': 100, 'ticker': 'AAPL', 'shares': 1, 'date': '2024-01-01', 'value': 100},
            {'action': 'sell', 'price': 110, 'ticker': 'AAPL', 'shares': 1, 'date': '2024-01-15', 'value': 110},
            {'action': 'buy', 'price': 110, 'ticker': 'AAPL', 'shares': 1, 'date': '2024-02-01', 'value': 110},
            {'action': 'sell', 'price': 105, 'ticker': 'AAPL', 'shares': 1, 'date': '2024-02-15', 'value': 105},
        ]
        win_rate = _calculate_win_rate(trades)
        assert win_rate == 50.0  # 1 win, 1 loss

    def test_empty_portfolio(self):
        from backtest.metrics import calculate_metrics

        result = calculate_metrics(100000, 100000, [], [])
        assert result['total_return_pct'] == 0.0
        assert result['sharpe_ratio'] == 0.0


class TestBacktestEngine:
    """백테스팅 엔진 테스트"""

    @patch('backtest.engine.fetch_historical_data')
    @patch('backtest.engine.run_pipeline')
    def test_run_backtest(self, mock_pipeline, mock_hist):
        """정상 케이스: 백테스팅 완주"""
        import pandas as pd
        import numpy as np
        from backtest.engine import BacktestEngine

        # Mock 가격 데이터 (60 영업일)
        dates = pd.date_range('2024-01-02', periods=60, freq='B')
        prices = 185.0 + np.cumsum(np.random.randn(60) * 1.5)
        prices = np.maximum(prices, 150)  # 최소값 보장

        mock_df = pd.DataFrame({
            'Open': prices * 0.995,
            'High': prices * 1.01,
            'Low': prices * 0.99,
            'Close': prices,
            'Volume': np.random.randint(40000000, 80000000, 60)
        }, index=dates)
        mock_hist.return_value = mock_df

        # Mock 파이프라인: buy 결정 반환
        mock_pipeline.return_value = make_mock_final_state('buy', True, 0.5)

        engine = BacktestEngine(initial_capital=100000)
        results = engine.run("AAPL", "2024-01-02", "2024-03-29", trading_days_interval=10)

        assert 'total_return_pct' in results
        assert 'sharpe_ratio' in results
        assert 'max_drawdown_pct' in results
        assert results['ticker'] == 'AAPL'

    @patch('backtest.engine.fetch_historical_data')
    @patch('backtest.engine.run_pipeline')
    def test_run_backtest_hold(self, mock_pipeline, mock_hist):
        """hold 결정 - 수익률 = 0 근방"""
        import pandas as pd
        import numpy as np
        from backtest.engine import BacktestEngine

        dates = pd.date_range('2024-01-02', periods=30, freq='B')
        prices = np.full(30, 185.0)
        mock_df = pd.DataFrame({
            'Open': prices, 'High': prices * 1.01, 'Low': prices * 0.99,
            'Close': prices, 'Volume': np.full(30, 50000000)
        }, index=dates)
        mock_hist.return_value = mock_df

        # approved=False → 거래 없음
        mock_pipeline.return_value = make_mock_final_state('hold', False, 0.0)

        engine = BacktestEngine(initial_capital=100000)
        results = engine.run("AAPL", "2024-01-02", "2024-01-31", trading_days_interval=5)

        assert results['total_return_pct'] == 0.0
        assert results['total_trades'] == 0


class TestWorkflow:
    """LangGraph 워크플로우 통합 테스트 (Mock)"""

    @patch('graph.workflow.fetch_market_data')
    @patch('graph.workflow.analyze_fundamentals')
    @patch('graph.workflow.analyze_sentiment')
    @patch('graph.workflow.analyze_news')
    @patch('graph.workflow.analyze_technical')
    @patch('graph.workflow.conduct_research')
    @patch('graph.workflow.make_trade_decision')
    @patch('graph.workflow.assess_and_approve')
    def test_full_pipeline(
        self,
        mock_risk, mock_trader, mock_researcher,
        mock_technical, mock_news, mock_sentiment, mock_fundamentals,
        mock_market
    ):
        """End-to-End 파이프라인 테스트"""
        from graph.workflow import run_pipeline

        # Mock 데이터
        market = MarketData(
            ticker="AAPL", date="2024-01-15",
            open=185.0, high=190.0, low=183.0, close=188.5, volume=50000000
        )
        mock_market.return_value = market

        analyst_report = AnalystReport(
            analyst_type="fundamentals", ticker="AAPL", date="2024-01-15",
            signal="bullish", confidence=0.8,
            summary="Strong", key_points=["p1", "p2", "p3"]
        )
        mock_fundamentals.return_value = analyst_report
        mock_sentiment.return_value = analyst_report._copy_with_type("sentiment")
        mock_news.return_value = analyst_report._copy_with_type("news")
        mock_technical.return_value = analyst_report._copy_with_type("technical")

        research = ResearchReport(
            ticker="AAPL", date="2024-01-15",
            bull_case="Bull", bear_case="Bear",
            consensus="buy", conviction=0.72
        )
        mock_researcher.return_value = research

        trade = TradeDecision(
            ticker="AAPL", date="2024-01-15",
            action="buy", quantity=0.5,
            reasoning="Strong", risk_score=0.3, approved=False
        )
        mock_trader.return_value = trade

        approved_trade = TradeDecision(
            ticker="AAPL", date="2024-01-15",
            action="buy", quantity=0.4,
            reasoning="Approved", risk_score=0.3, approved=True
        )
        mock_risk.return_value = approved_trade

        # 파이프라인 실행
        final_state = run_pipeline("AAPL", "2024-01-15")

        assert final_state is not None
        assert final_state['ticker'] == "AAPL"
        decision = final_state['trade_decision']
        assert decision is not None
        assert decision.approved is True
        assert decision.action == "buy"


# AnalystReport에 _copy_with_type 헬퍼 메서드 임시 패치
def _analyst_copy_with_type(self, analyst_type):
    return AnalystReport(
        analyst_type=analyst_type, ticker=self.ticker, date=self.date,
        signal=self.signal, confidence=self.confidence,
        summary=self.summary, key_points=self.key_points,
        data_sources=self.data_sources
    )


AnalystReport._copy_with_type = _analyst_copy_with_type


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
