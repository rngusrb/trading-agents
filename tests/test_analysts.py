"""
test_analysts.py — 애널리스트 에이전트 Mock 테스트
외부 API 의존성 없는 단위 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from models.schemas import AnalystReport, MarketData


class TestFundamentalsAnalyst:
    """펀더멘털 분석 에이전트 테스트"""

    def _make_mock_llm_response(self, signal="bullish", confidence=0.8):
        import json
        mock_content = MagicMock()
        mock_content.text = json.dumps({
            "signal": signal,
            "confidence": confidence,
            "summary": "Strong fundamentals with good growth metrics",
            "key_points": [
                "P/E ratio of 25 is reasonable",
                "ROE of 30% indicates strong profitability",
                "Revenue growing at 15% YoY"
            ]
        })
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        return mock_response

    @patch('agents.fundamentals_analyst.fetch_company_profile')
    @patch('agents.fundamentals_analyst.fetch_basic_financials')
    @patch('agents.fundamentals_analyst.fetch_earnings')
    @patch('agents.fundamentals_analyst.fetch_recommendation_trends')
    @patch('agents.fundamentals_analyst.anthropic.Anthropic')
    def test_analyze_fundamentals_bullish(
        self, mock_anthropic, mock_recommendations, mock_earnings,
        mock_financials, mock_profile
    ):
        """정상 케이스: bullish 신호 생성"""
        from agents.fundamentals_analyst import analyze_fundamentals

        mock_profile.return_value = {
            'name': 'Apple Inc.',
            'finnhubIndustry': 'Technology',
            'marketCapitalization': 3000
        }
        mock_financials.return_value = {
            'peBasicExclExtraTTM': 25.0,
            'roeTTM': 30.0,
            'revenueGrowthTTMYoy': 15.0,
            'pbQuarterly': 8.5
        }
        mock_earnings.return_value = [
            {'period': '2024Q3', 'actual': 1.64, 'estimate': 1.60, 'surprisePercent': 2.5}
        ]
        mock_recommendations.return_value = []

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_llm_response('bullish', 0.8)

        result = analyze_fundamentals("AAPL", "2024-01-15")

        assert isinstance(result, AnalystReport)
        assert result.analyst_type == "fundamentals"
        assert result.ticker == "AAPL"
        assert result.date == "2024-01-15"
        assert result.signal == "bullish"
        assert result.confidence == 0.8
        assert len(result.key_points) >= 1
        assert "finnhub" in result.data_sources

    @patch('agents.fundamentals_analyst.fetch_company_profile')
    @patch('agents.fundamentals_analyst.fetch_basic_financials')
    @patch('agents.fundamentals_analyst.fetch_earnings')
    @patch('agents.fundamentals_analyst.fetch_recommendation_trends')
    @patch('agents.fundamentals_analyst.anthropic.Anthropic')
    def test_analyze_fundamentals_with_market_data(
        self, mock_anthropic, mock_recommendations, mock_earnings,
        mock_financials, mock_profile
    ):
        """주가 데이터 포함 케이스"""
        from agents.fundamentals_analyst import analyze_fundamentals

        mock_profile.return_value = {}
        mock_financials.return_value = {}
        mock_earnings.return_value = []
        mock_recommendations.return_value = []

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_llm_response('neutral', 0.5)

        market_data = MarketData(
            ticker="AAPL",
            date="2024-01-15",
            open=185.0, high=190.0, low=183.0, close=188.5,
            volume=50000000
        )
        result = analyze_fundamentals("AAPL", "2024-01-15", market_data)

        assert isinstance(result, AnalystReport)
        assert result.ticker == "AAPL"


class TestSentimentAnalyst:
    """소셜 미디어 감성 분석 에이전트 테스트"""

    def _make_mock_llm_response(self, signal="bullish", confidence=0.7):
        import json
        mock_content = MagicMock()
        mock_content.text = json.dumps({
            "signal": signal,
            "confidence": confidence,
            "summary": "Positive social media sentiment with high engagement",
            "key_points": [
                "High post volume indicating strong interest",
                "Positive average score showing bullish sentiment",
                "Active community discussion"
            ]
        })
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        return mock_response

    @patch('agents.sentiment_analyst.fetch_reddit_posts')
    @patch('agents.sentiment_analyst.anthropic.Anthropic')
    def test_analyze_sentiment_bullish(self, mock_anthropic, mock_reddit):
        """정상 케이스: bullish 소셜 감성"""
        from agents.sentiment_analyst import analyze_sentiment

        mock_reddit.return_value = [
            {
                'title': 'AAPL looks amazing for Q1',
                'score': 500,
                'num_comments': 200,
                'subreddit': 'wallstreetbets',
                'created_utc': 1705276800.0
            },
            {
                'title': 'Apple earnings beat expectations',
                'score': 300,
                'num_comments': 150,
                'subreddit': 'stocks',
                'created_utc': 1705276800.0
            }
        ]

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_llm_response('bullish', 0.7)

        result = analyze_sentiment("AAPL", "2024-01-15")

        assert isinstance(result, AnalystReport)
        assert result.analyst_type == "sentiment"
        assert result.ticker == "AAPL"
        assert result.signal == "bullish"
        assert result.confidence == 0.7
        assert len(result.key_points) >= 1

    @patch('agents.sentiment_analyst.fetch_reddit_posts')
    @patch('agents.sentiment_analyst.anthropic.Anthropic')
    def test_analyze_sentiment_no_data(self, mock_anthropic, mock_reddit):
        """엣지 케이스: 소셜 데이터 없음"""
        from agents.sentiment_analyst import analyze_sentiment

        mock_reddit.return_value = []

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_llm_response('neutral', 0.3)

        result = analyze_sentiment("AAPL", "2024-01-15")

        assert isinstance(result, AnalystReport)
        assert result.analyst_type == "sentiment"
        assert result.signal in ["bullish", "bearish", "neutral"]


class TestNewsAnalyst:
    """뉴스 분석 에이전트 테스트"""

    def _make_mock_llm_response(self, signal="bearish", confidence=0.75):
        import json
        mock_content = MagicMock()
        mock_content.text = json.dumps({
            "signal": signal,
            "confidence": confidence,
            "summary": "Mixed news with some concerning headlines",
            "key_points": [
                "Revenue miss reported by major news sources",
                "Supply chain concerns highlighted",
                "Analyst downgrades noted"
            ]
        })
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        return mock_response

    @patch('agents.news_analyst.fetch_company_news')
    @patch('agents.news_analyst.anthropic.Anthropic')
    def test_analyze_news_bearish(self, mock_anthropic, mock_news):
        """정상 케이스: bearish 뉴스 신호"""
        from agents.news_analyst import analyze_news

        mock_news.return_value = [
            {
                'headline': 'Apple misses Q4 revenue estimates',
                'summary': 'Apple reported lower than expected revenue',
                'source': 'Reuters',
                'datetime': 1705276800,
                'url': 'https://example.com/1'
            }
        ]

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_llm_response('bearish', 0.75)

        result = analyze_news("AAPL", "2024-01-15")

        assert isinstance(result, AnalystReport)
        assert result.analyst_type == "news"
        assert result.ticker == "AAPL"
        assert result.signal == "bearish"
        assert result.confidence == 0.75
        assert "finnhub_news" in result.data_sources

    @patch('agents.news_analyst.fetch_company_news')
    @patch('agents.news_analyst.anthropic.Anthropic')
    def test_fallback_on_llm_error(self, mock_anthropic, mock_news):
        """LLM 오류 시 폴백 분석"""
        from agents.news_analyst import analyze_news

        mock_news.return_value = [
            {
                'headline': 'Apple reports record earnings beat',
                'summary': 'Strong Q1 results',
                'source': 'Reuters',
                'datetime': 1705276800,
                'url': 'https://example.com/1'
            }
        ]

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        result = analyze_news("AAPL", "2024-01-15")

        assert isinstance(result, AnalystReport)
        assert result.signal in ["bullish", "bearish", "neutral"]


class TestTechnicalAnalyst:
    """기술적 분석 에이전트 테스트"""

    def _make_mock_llm_response(self, signal="bullish", confidence=0.72):
        import json
        mock_content = MagicMock()
        mock_content.text = json.dumps({
            "signal": signal,
            "confidence": confidence,
            "summary": "RSI oversold with MACD crossover forming",
            "key_points": [
                "RSI at 28 indicates oversold condition",
                "MACD histogram turning positive",
                "Price near lower Bollinger Band"
            ]
        })
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        return mock_response

    @patch('agents.technical_analyst.fetch_historical_data')
    @patch('agents.technical_analyst.anthropic.Anthropic')
    def test_analyze_technical_bullish(self, mock_anthropic, mock_hist):
        """정상 케이스: bullish 기술적 신호"""
        import pandas as pd
        import numpy as np
        from agents.technical_analyst import analyze_technical

        # 60일치 Mock 주가 데이터
        dates = pd.date_range('2023-11-01', periods=60, freq='B')
        mock_df = pd.DataFrame({
            'Open': np.random.uniform(180, 195, 60),
            'High': np.random.uniform(185, 200, 60),
            'Low': np.random.uniform(175, 190, 60),
            'Close': np.random.uniform(180, 195, 60),
            'Volume': np.random.randint(40000000, 80000000, 60)
        }, index=dates)
        mock_hist.return_value = mock_df

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_llm_response('bullish', 0.72)

        result = analyze_technical("AAPL", "2024-01-15")

        assert isinstance(result, AnalystReport)
        assert result.analyst_type == "technical"
        assert result.ticker == "AAPL"
        assert result.signal == "bullish"
        assert result.confidence == 0.72
        assert "yfinance" in result.data_sources

    @patch('agents.technical_analyst.fetch_historical_data')
    @patch('agents.technical_analyst.anthropic.Anthropic')
    def test_analyze_technical_empty_data(self, mock_anthropic, mock_hist):
        """엣지 케이스: 데이터 없음"""
        import pandas as pd
        from agents.technical_analyst import analyze_technical

        mock_hist.return_value = pd.DataFrame()

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = self._make_mock_llm_response('neutral', 0.3)

        result = analyze_technical("AAPL", "2024-01-15")

        assert isinstance(result, AnalystReport)
        assert result.analyst_type == "technical"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
