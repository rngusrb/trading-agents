# INTERFACE.md — 에이전트 간 데이터 계약
> ⚠️ 변경 시 창0(orchestrator) 승인 필수

## 데이터 흐름

```
MarketData → [Analyst Team] → AnalystReport[]
                                    ↓
                        [Researcher Team] → ResearchReport
                                                ↓
                                    [Trader] → TradeDecision (approved=False)
                                                        ↓
                                    [Risk Management] → TradeDecision (approved=True/False)
```

## 스키마 정의 위치
모든 스키마는 `models/schemas.py`에 정의됩니다.

## MarketData
| 필드 | 타입 | 설명 | 제약 |
|------|------|------|------|
| ticker | str | 종목 코드 | 필수 |
| date | str | 날짜 | YYYY-MM-DD |
| open | float | 시가 | 필수 |
| high | float | 고가 | 필수 |
| low | float | 저가 | 필수 |
| close | float | 종가 | 필수 |
| volume | int | 거래량 | >= 0 |
| indicators | dict | 기술적 지표 | 선택 |

## AnalystReport
| 필드 | 타입 | 설명 | 제약 |
|------|------|------|------|
| analyst_type | str | 애널리스트 유형 | fundamentals/sentiment/news/technical |
| ticker | str | 종목 코드 | 필수 |
| date | str | 분석 날짜 | YYYY-MM-DD |
| signal | str | 투자 신호 | bullish/bearish/neutral |
| confidence | float | 신뢰도 | 0.0~1.0 |
| summary | str | 분석 요약 | 필수 |
| key_points | list[str] | 핵심 포인트 | 최소 1개 |
| data_sources | list[str] | 데이터 소스 | 선택 |
| created_at | str | 생성 시각 | ISO 형식 |

## ResearchReport
| 필드 | 타입 | 설명 | 제약 |
|------|------|------|------|
| ticker | str | 종목 코드 | 필수 |
| date | str | 분석 날짜 | YYYY-MM-DD |
| bull_case | str | 매수 근거 | 필수 |
| bear_case | str | 매도 근거 | 필수 |
| consensus | str | 합의 결론 | buy/sell/hold |
| conviction | float | 확신도 | 0.0~1.0 |
| created_at | str | 생성 시각 | ISO 형식 |

## TradeDecision
| 필드 | 타입 | 설명 | 제약 |
|------|------|------|------|
| ticker | str | 종목 코드 | 필수 |
| date | str | 결정 날짜 | YYYY-MM-DD |
| action | str | 거래 액션 | buy/sell/hold |
| quantity | float | 포지션 비중 | 0.0~1.0 |
| reasoning | str | 결정 근거 | 필수 |
| risk_score | float | 리스크 점수 | 0.0~1.0 |
| approved | bool | Fund Manager 승인 | 기본 False |
| created_at | str | 생성 시각 | ISO 형식 |

## 변경 이력
| 날짜 | 변경 내용 | 승인자 |
|------|----------|--------|
| 2026-03-10 | 초기 스키마 정의 | orchestrator |
