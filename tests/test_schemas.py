"""
Phase 1 검증 테스트 - 데이터 모델 스키마 검증
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pydantic import ValidationError
from models.schemas import MarketData, AnalystReport, ResearchReport, TradeDecision


class TestMarketData:
    def test_valid_market_data(self):
        data = MarketData(
            ticker="AAPL",
            date="2024-01-15",
            open=185.0,
            high=190.0,
            low=183.0,
            close=188.5,
            volume=50000000,
            indicators={"RSI": 65.3, "MACD": 1.2}
        )
        assert data.ticker == "AAPL"
        assert data.close == 188.5

    def test_invalid_date_format(self):
        with pytest.raises(ValidationError):
            MarketData(
                ticker="AAPL",
                date="2024/01/15",  # 잘못된 형식
                open=185.0, high=190.0, low=183.0, close=188.5, volume=50000000
            )

    def test_negative_volume(self):
        with pytest.raises(ValidationError):
            MarketData(
                ticker="AAPL",
                date="2024-01-15",
                open=185.0, high=190.0, low=183.0, close=188.5,
                volume=-100  # 음수 거래량
            )


class TestAnalystReport:
    def test_valid_report(self):
        report = AnalystReport(
            analyst_type="fundamentals",
            ticker="AAPL",
            date="2024-01-15",
            signal="bullish",
            confidence=0.85,
            summary="Strong fundamentals",
            key_points=["Revenue growth", "High margins", "Strong cash flow"],
            data_sources=["yfinance", "finnhub"]
        )
        assert report.signal == "bullish"
        assert report.confidence == 0.85

    def test_invalid_signal(self):
        with pytest.raises(ValidationError):
            AnalystReport(
                analyst_type="fundamentals",
                ticker="AAPL",
                date="2024-01-15",
                signal="strong_buy",  # 잘못된 신호
                confidence=0.85,
                summary="Test",
                key_points=["point1"]
            )

    def test_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            AnalystReport(
                analyst_type="fundamentals",
                ticker="AAPL",
                date="2024-01-15",
                signal="bullish",
                confidence=1.5,  # 범위 초과
                summary="Test",
                key_points=["point1"]
            )


class TestResearchReport:
    def test_valid_report(self):
        report = ResearchReport(
            ticker="AAPL",
            date="2024-01-15",
            bull_case="Strong growth prospects",
            bear_case="High valuation concerns",
            consensus="buy",
            conviction=0.7
        )
        assert report.consensus == "buy"

    def test_invalid_consensus(self):
        with pytest.raises(ValidationError):
            ResearchReport(
                ticker="AAPL",
                date="2024-01-15",
                bull_case="Bull",
                bear_case="Bear",
                consensus="strong_buy",  # 잘못된 합의
                conviction=0.7
            )


class TestTradeDecision:
    def test_valid_decision(self):
        decision = TradeDecision(
            ticker="AAPL",
            date="2024-01-15",
            action="buy",
            quantity=0.5,
            reasoning="Strong signals across all analysts",
            risk_score=0.3,
            approved=True
        )
        assert decision.approved is True
        assert decision.quantity == 0.5

    def test_quantity_out_of_range(self):
        with pytest.raises(ValidationError):
            TradeDecision(
                ticker="AAPL",
                date="2024-01-15",
                action="buy",
                quantity=1.5,  # 범위 초과
                reasoning="Test",
                risk_score=0.3
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
