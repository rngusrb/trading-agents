"""
test_researcher.py — Researcher 에이전트 Mock 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from models.schemas import AnalystReport, ResearchReport


def make_analyst_reports(signals=None):
    """테스트용 애널리스트 보고서 생성"""
    if signals is None:
        signals = ['bullish', 'bullish', 'neutral', 'bullish']
    types = ['fundamentals', 'sentiment', 'news', 'technical']
    return [
        AnalystReport(
            analyst_type=t,
            ticker="AAPL",
            date="2024-01-15",
            signal=s,
            confidence=0.75,
            summary=f"{t} analysis",
            key_points=["point1", "point2", "point3"]
        )
        for t, s in zip(types, signals)
    ]


class TestResearcher:
    """Bull/Bear 리서처 에이전트 테스트"""

    def _make_mock_text_response(self, text):
        mock_content = MagicMock()
        mock_content.text = text
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        return mock_response

    def _make_mock_json_response(self, data):
        import json
        return self._make_mock_text_response(json.dumps(data))

    @patch('agents.researcher.anthropic.Anthropic')
    def test_conduct_research_buy(self, mock_anthropic):
        """정상 케이스: buy 합의"""
        from agents.researcher import conduct_research

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        # bull_case, bear_case, consensus 순서로 응답
        mock_client.messages.create.side_effect = [
            self._make_mock_text_response("Strong bull case: revenue growth and market leadership..."),
            self._make_mock_text_response("Bear case: valuation concerns and competition..."),
            self._make_mock_json_response({
                "consensus": "buy",
                "conviction": 0.72,
                "rationale": "Bull case outweighs bear case"
            })
        ]

        reports = make_analyst_reports(['bullish', 'bullish', 'neutral', 'bullish'])
        result = conduct_research("AAPL", "2024-01-15", reports)

        assert isinstance(result, ResearchReport)
        assert result.ticker == "AAPL"
        assert result.date == "2024-01-15"
        assert result.consensus == "buy"
        assert result.conviction == 0.72
        assert len(result.bull_case) > 0
        assert len(result.bear_case) > 0

    @patch('agents.researcher.anthropic.Anthropic')
    def test_conduct_research_sell(self, mock_anthropic):
        """bearish 합의: sell 결과"""
        from agents.researcher import conduct_research

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_client.messages.create.side_effect = [
            self._make_mock_text_response("Bull case: some positive indicators..."),
            self._make_mock_text_response("Strong bear case: declining fundamentals..."),
            self._make_mock_json_response({
                "consensus": "sell",
                "conviction": 0.65,
                "rationale": "Risk outweighs reward"
            })
        ]

        reports = make_analyst_reports(['bearish', 'bearish', 'bearish', 'neutral'])
        result = conduct_research("AAPL", "2024-01-15", reports)

        assert result.consensus == "sell"
        assert result.conviction == 0.65

    @patch('agents.researcher.anthropic.Anthropic')
    def test_conduct_research_llm_error(self, mock_anthropic):
        """LLM 오류 시 폴백"""
        from agents.researcher import conduct_research

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        reports = make_analyst_reports()
        result = conduct_research("AAPL", "2024-01-15", reports)

        assert isinstance(result, ResearchReport)
        assert result.consensus in ["buy", "sell", "hold"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
