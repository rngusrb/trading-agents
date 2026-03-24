"""
test_trader.py — Trader + Risk Manager 에이전트 Mock 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from models.schemas import AnalystReport, ResearchReport, TradeDecision, MarketData


def make_research_report(consensus="buy", conviction=0.72):
    return ResearchReport(
        ticker="AAPL",
        date="2024-01-15",
        bull_case="Strong revenue growth and market leadership position.",
        bear_case="High valuation and potential macro headwinds.",
        consensus=consensus,
        conviction=conviction
    )


def make_analyst_reports():
    types_signals = [
        ('fundamentals', 'bullish'),
        ('sentiment', 'bullish'),
        ('news', 'neutral'),
        ('technical', 'bullish'),
    ]
    return [
        AnalystReport(
            analyst_type=t, ticker="AAPL", date="2024-01-15",
            signal=s, confidence=0.75,
            summary=f"{t} analysis", key_points=["p1", "p2", "p3"]
        )
        for t, s in types_signals
    ]


class TestTrader:
    """트레이더 에이전트 테스트"""

    def _make_mock_json_response(self, data):
        import json
        mock_content = MagicMock()
        mock_content.text = json.dumps(data)
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        return mock_response

    @patch('agents.trader.anthropic.Anthropic')
    def test_make_trade_decision_buy(self, mock_anthropic):
        """정상 케이스: buy 결정"""
        from agents.trader import make_trade_decision

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_json_response({
            "action": "buy",
            "quantity": 0.5,
            "reasoning": "Strong bullish signals across all analysts with good fundamentals",
            "risk_score": 0.35
        })

        result = make_trade_decision(
            "AAPL", "2024-01-15",
            make_research_report("buy", 0.72),
            make_analyst_reports()
        )

        assert isinstance(result, TradeDecision)
        assert result.ticker == "AAPL"
        assert result.action == "buy"
        assert result.quantity == 0.5
        assert result.risk_score == 0.35
        assert result.approved is False  # 승인 전

    @patch('agents.trader.anthropic.Anthropic')
    def test_make_trade_decision_hold(self, mock_anthropic):
        """hold 결정 케이스"""
        from agents.trader import make_trade_decision

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_json_response({
            "action": "hold",
            "quantity": 0.0,
            "reasoning": "Mixed signals, insufficient conviction to take position",
            "risk_score": 0.5
        })

        result = make_trade_decision(
            "AAPL", "2024-01-15",
            make_research_report("hold", 0.4),
            make_analyst_reports()
        )

        assert result.action == "hold"
        assert result.quantity == 0.0

    @patch('agents.trader.anthropic.Anthropic')
    def test_trade_decision_with_market_data(self, mock_anthropic):
        """주가 데이터 포함 케이스"""
        from agents.trader import make_trade_decision

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_json_response({
            "action": "buy",
            "quantity": 0.4,
            "reasoning": "Technical and fundamental alignment",
            "risk_score": 0.3
        })

        market_data = MarketData(
            ticker="AAPL", date="2024-01-15",
            open=185.0, high=190.0, low=183.0, close=188.5,
            volume=50000000,
            indicators={"RSI_14": 45.0, "MACD_Hist": 0.5}
        )

        result = make_trade_decision(
            "AAPL", "2024-01-15",
            make_research_report(), make_analyst_reports(), market_data
        )

        assert isinstance(result, TradeDecision)
        assert result.action == "buy"


class TestRiskManager:
    """리스크 관리 에이전트 테스트"""

    def _make_mock_json_response(self, data):
        import json
        mock_content = MagicMock()
        mock_content.text = json.dumps(data)
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        return mock_response

    def _make_mock_text_response(self, text):
        mock_content = MagicMock()
        mock_content.text = text
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        return mock_response

    @patch('agents.risk_manager.anthropic.Anthropic')
    def test_assess_and_approve(self, mock_anthropic):
        """정상 케이스: 승인 처리"""
        from agents.risk_manager import assess_and_approve

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        # 3 risk analysts + 1 fund manager = 4 calls
        mock_client.messages.create.side_effect = [
            self._make_mock_text_response("Risky analyst: Approve. Good risk/reward. Keep 0.5 position."),
            self._make_mock_text_response("Neutral analyst: Approve with slight reduction to 0.4."),
            self._make_mock_text_response("Safe analyst: Consider reducing to 0.3 for safety."),
            self._make_mock_json_response({
                "action": "buy",
                "quantity": 0.4,
                "reasoning": "Balanced risk management approval",
                "risk_score": 0.35,
                "approved": True
            })
        ]

        trade = TradeDecision(
            ticker="AAPL", date="2024-01-15",
            action="buy", quantity=0.5,
            reasoning="Strong signals", risk_score=0.35,
            approved=False
        )

        result = assess_and_approve(
            trade, make_research_report(), make_analyst_reports()
        )

        assert isinstance(result, TradeDecision)
        assert result.ticker == "AAPL"
        assert result.approved is True
        assert result.action == "buy"

    @patch('agents.risk_manager.anthropic.Anthropic')
    def test_assess_and_reject(self, mock_anthropic):
        """고위험 트레이드 거절 케이스"""
        from agents.risk_manager import assess_and_approve

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_client.messages.create.side_effect = [
            self._make_mock_text_response("Risky: Approve with caution."),
            self._make_mock_text_response("Neutral: Too risky, reduce size."),
            self._make_mock_text_response("Safe: Reject, risk too high."),
            self._make_mock_json_response({
                "action": "hold",
                "quantity": 0.0,
                "reasoning": "Risk too high, downgrade to hold",
                "risk_score": 0.85,
                "approved": False
            })
        ]

        trade = TradeDecision(
            ticker="AAPL", date="2024-01-15",
            action="buy", quantity=0.8,
            reasoning="Aggressive buy", risk_score=0.85,
            approved=False
        )

        result = assess_and_approve(
            trade, make_research_report(), make_analyst_reports()
        )

        assert result.approved is False

    @patch('agents.risk_manager.anthropic.Anthropic')
    def test_fund_manager_llm_error(self, mock_anthropic):
        """Fund Manager LLM 오류 시 폴백"""
        from agents.risk_manager import assess_and_approve

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        trade = TradeDecision(
            ticker="AAPL", date="2024-01-15",
            action="buy", quantity=0.5,
            reasoning="Test", risk_score=0.4,
            approved=False
        )

        result = assess_and_approve(
            trade, make_research_report(), make_analyst_reports()
        )

        assert isinstance(result, TradeDecision)
        assert result.ticker == "AAPL"
        # risk_score 0.4 < 0.6 이므로 폴백에서 approved=True
        assert result.approved is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
