"""
공유 데이터 모델 - TradingAgents 시스템의 모든 에이전트가 사용하는 Pydantic 스키마
참조: INTERFACE.md
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class MarketData(BaseModel):
    """주가 데이터 및 기술적 지표"""
    ticker: str = Field(..., description="종목 코드 (예: AAPL)")
    date: str = Field(..., description="날짜 YYYY-MM-DD")
    open: float = Field(..., description="시가")
    high: float = Field(..., description="고가")
    low: float = Field(..., description="저가")
    close: float = Field(..., description="종가")
    volume: int = Field(..., description="거래량")
    indicators: dict = Field(default_factory=dict, description="RSI, MACD, BB 등 기술적 지표")

    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        """날짜 형식 검증 YYYY-MM-DD"""
        datetime.strptime(v, '%Y-%m-%d')
        return v

    @field_validator('volume')
    @classmethod
    def validate_volume(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Volume cannot be negative")
        return v


class AnalystReport(BaseModel):
    """애널리스트 보고서 - 4개 애널리스트 공통 출력 형식"""
    analyst_type: str = Field(
        ...,
        description="애널리스트 유형",
        pattern="^(fundamentals|sentiment|news|technical)$"
    )
    ticker: str = Field(..., description="종목 코드")
    date: str = Field(..., description="분석 날짜 YYYY-MM-DD")
    signal: str = Field(
        ...,
        description="투자 신호",
        pattern="^(bullish|bearish|neutral)$"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도 0.0~1.0")
    summary: str = Field(..., description="분석 요약")
    key_points: list[str] = Field(..., min_length=1, description="핵심 포인트 3~5개")
    data_sources: list[str] = Field(default_factory=list, description="데이터 소스")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="생성 시각"
    )

    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        datetime.strptime(v, '%Y-%m-%d')
        return v


class ResearchReport(BaseModel):
    """리서치 보고서 - Bull/Bear 토론 결과"""
    ticker: str = Field(..., description="종목 코드")
    date: str = Field(..., description="분석 날짜 YYYY-MM-DD")
    bull_case: str = Field(..., description="매수 근거")
    bear_case: str = Field(..., description="매도 근거")
    consensus: str = Field(
        ...,
        description="합의 결론",
        pattern="^(buy|sell|hold|short|cover)$"
    )
    conviction: float = Field(..., ge=0.0, le=1.0, description="확신도 0.0~1.0")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="생성 시각"
    )

    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        datetime.strptime(v, '%Y-%m-%d')
        return v


class TradeDecision(BaseModel):
    """트레이딩 결정 - Trader + Risk Manager + Fund Manager 최종 출력"""
    ticker: str = Field(..., description="종목 코드")
    date: str = Field(..., description="결정 날짜 YYYY-MM-DD")
    action: str = Field(
        ...,
        description="거래 액션",
        pattern="^(buy|sell|hold|short|cover)$"
    )
    quantity: float = Field(..., ge=0.0, le=1.0, description="포지션 비중 0.0~1.0")
    reasoning: str = Field(..., description="결정 근거")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="리스크 점수 0.0~1.0")
    approved: bool = Field(default=False, description="Fund Manager 승인 여부")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="생성 시각"
    )

    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        datetime.strptime(v, '%Y-%m-%d')
        return v
