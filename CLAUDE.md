# CLAUDE.md — Trading Agents
# LangGraph 기반 멀티에이전트 금융 트레이딩 시스템
# 참조 논문: TradingAgents (arXiv:2412.20138)

## 프로젝트 목적
1. TradingAgents 논문 구조 기반 7에이전트 트레이딩 시스템 구축
2. Agent Teams 워크플로우로 각 에이전트 독립 개발 + 자동 통합
3. 백테스팅으로 성능 검증 후 페이퍼 트레이딩 → 실거래 확장

---

## 아키텍처 개요

```
[Analyst Team] ─────────────────────────── 병렬 실행
├── Fundamentals Analyst   yfinance + Finnhub
├── Sentiment Analyst      Reddit PRAW
├── News Analyst           Finnhub News
└── Technical Analyst      pandas-ta
         ↓
[Researcher Team] ─────────────────────── 토론/검증
├── Bull Researcher        매수 논거 강화
└── Bear Researcher        매도 논거 강화
         ↓
[Trader] ────────────────────────────────  최종 결정
         ↓
[Risk Management Team] ──────────────────  리스크 필터
├── Risky Analyst
├── Neutral Analyst
└── Safe Analyst
         ↓
[Fund Manager] ──────────────────────────  실행 승인
```

---

## 디렉토리 구조

```
trading-agents/
├── CLAUDE.md                    # 이 파일 (헌법)
├── PROGRESS.md                  # 진행상황
├── INTERFACE.md                 # 에이전트 간 데이터 계약
├── scratch.md                   # 작업 메모
├── watch_progress.py            # 파일 변경 감시 + Mac 알림
├── main.py                      # 백테스팅 진입점
├── requirements.txt
├── .env
├── .env.example
│
├── agents/                      # 7개 에이전트
│   ├── __init__.py
│   ├── fundamentals_analyst.py  # 창1 담당
│   ├── sentiment_analyst.py     # 창2 담당
│   ├── news_analyst.py          # 창3 담당
│   ├── technical_analyst.py     # 창4 담당
│   ├── researcher.py            # 창5 담당 (Bull + Bear)
│   ├── trader.py                # 창6 담당
│   └── risk_manager.py          # 창7 담당 (3명 + Fund Manager)
│
├── graph/                       # LangGraph 워크플로우
│   ├── __init__.py
│   ├── state.py                 # TradingAgentState 정의
│   └── workflow.py              # 전체 그래프 구성
│
├── tools/                       # 데이터 수집 도구
│   ├── __init__.py
│   ├── market_data.py           # yfinance 주가 데이터
│   ├── fundamentals.py          # Finnhub 펀더멘털
│   ├── news_fetcher.py          # Finnhub 뉴스
│   ├── social_data.py           # Reddit PRAW
│   └── technical_indicators.py  # pandas-ta 지표
│
├── models/
│   ├── __init__.py
│   └── schemas.py               # 공유 데이터 모델
│
├── backtest/
│   ├── __init__.py
│   ├── engine.py                # 백테스팅 엔진
│   └── metrics.py               # 성능 지표 계산
│
└── tests/
    ├── test_analysts.py
    ├── test_researcher.py
    ├── test_trader.py
    ├── test_risk_manager.py
    └── test_backtest.py
```

---

## 창 구조 (Agent Teams)

```
창0 (orchestrator / Fund Manager)
├── Agent Teams 총괄
├── 통합 테스트 실행
├── 로그 분석 + 문제점 파악
├── 재작업 지시
└── watch_progress.py 실행

창1 → fundamentals_analyst.py
창2 → sentiment_analyst.py
창3 → news_analyst.py
창4 → technical_analyst.py
창5 → researcher.py (Bull + Bear)
창6 → trader.py
창7 → risk_manager.py + fund_manager
```

---

## 데이터 모델 (INTERFACE.md 요약)
> ⚠️ 변경 시 창0 승인 필수

### MarketData
```python
class MarketData(BaseModel):
    ticker: str
    date: str                    # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: int
    indicators: dict             # RSI, MACD, BB 등
```

### AnalystReport
```python
class AnalystReport(BaseModel):
    analyst_type: str            # "fundamentals"|"sentiment"|"news"|"technical"
    ticker: str
    date: str
    signal: str                  # "bullish"|"bearish"|"neutral"
    confidence: float            # 0.0 ~ 1.0
    summary: str
    key_points: list[str]        # 핵심 포인트 3~5개
    data_sources: list[str]
    created_at: str
```

### ResearchReport
```python
class ResearchReport(BaseModel):
    ticker: str
    date: str
    bull_case: str
    bear_case: str
    consensus: str               # "buy"|"sell"|"hold"
    conviction: float
    created_at: str
```

### TradeDecision
```python
class TradeDecision(BaseModel):
    ticker: str
    date: str
    action: str                  # "buy"|"sell"|"hold"
    quantity: float              # 비중 0.0~1.0
    reasoning: str
    risk_score: float
    approved: bool               # Fund Manager 승인
    created_at: str
```

### TradingAgentState (LangGraph)
```python
class TradingAgentState(TypedDict):
    ticker: str
    date: str
    market_data: MarketData
    analyst_reports: list[AnalystReport]
    research_report: ResearchReport
    trade_decision: TradeDecision
    messages: list[BaseMessage]
    next_agent: str
```

---

## LLM 전략 (비용 최적화)

```python
ANALYST_MODEL  = "claude-haiku-4-5-20251001"   # 반복 실행, 저비용
DECISION_MODEL = "claude-sonnet-4-6"            # 의사결정, 고품질
MANAGER_MODEL  = "claude-opus-4-6"              # Fund Manager, 최고품질
```

---

## 멀티창 운영 규칙 (헌법)

### 규칙 1: PROGRESS.md 업데이트
- 파일 하나 완성할 때마다 업데이트
- 테스트 통과 후에만 ✅ 표시

### 규칙 2: 인터페이스 변경
- schemas.py, INTERFACE.md 변경은 창0 승인 필수

### 규칙 3: 알림
- Phase 완료 시 watch_progress.py → Mac 알림

### 규칙 4: 담당 범위
- 자기 담당 파일만 수정, 다른 창 파일 직접 수정 금지

### 규칙 5: 테스트
- Mock 테스트로 외부 API 의존성 제거
- 단위 테스트 통과 후에만 완료 표시

---

## Phase 계획

### Phase 1: 기반 세팅 (창0)
- [ ] 폴더 구조 생성
- [ ] requirements.txt
- [ ] models/schemas.py (전체 데이터 모델)
- [ ] graph/state.py (TradingAgentState)
- [ ] INTERFACE.md
- [ ] watch_progress.py
- [ ] .env.example
- **완료 조건**: 모델 검증 PASS + 알림 작동

### Phase 2: Tools (창0 또는 병렬)
- [ ] tools/market_data.py (yfinance)
- [ ] tools/technical_indicators.py (pandas-ta)
- [ ] tools/fundamentals.py (Finnhub)
- [ ] tools/news_fetcher.py (Finnhub News)
- [ ] tools/social_data.py (Reddit PRAW)
- **완료 조건**: 각 툴 Mock 테스트 PASS

### Phase 3: Analyst Team (창1~4 병렬)
- [ ] agents/fundamentals_analyst.py (창1)
- [ ] agents/sentiment_analyst.py (창2)
- [ ] agents/news_analyst.py (창3)
- [ ] agents/technical_analyst.py (창4)
- **완료 조건**: AnalystReport 형식 검증 PASS

### Phase 4: Researcher + Trader (창5~6)
- [ ] agents/researcher.py - Bull/Bear 토론 (창5)
- [ ] agents/trader.py - 최종 결정 (창6)
- **완료 조건**: ResearchReport + TradeDecision 검증 PASS

### Phase 5: Risk + Fund Manager (창7)
- [ ] agents/risk_manager.py (창7)
- **완료 조건**: TradeDecision.approved 검증 PASS

### Phase 6: LangGraph 통합 (창0)
- [ ] graph/workflow.py
- [ ] 전체 파이프라인 연결
- **완료 조건**: AAPL 단일 종목 end-to-end PASS

### Phase 7: 백테스팅 (창0)
- [ ] backtest/engine.py
- [ ] backtest/metrics.py
- [ ] main.py
- **완료 조건**: AAPL 2024.01~03 백테스팅 수익률 측정
- **벤치마크**: 논문 수치 AAPL +26.62%

---

## 기술 스택
- Python 3.11+
- langgraph, langchain-anthropic
- anthropic
- yfinance
- finnhub-python
- praw (Reddit)
- pandas-ta
- pydantic
- watchdog

## 코딩 규칙
- 타입 힌트 필수
- Pydantic 모델로 모든 데이터 검증
- 환경변수는 .env에서만 로드
- 함수 단위 docstring 필수
- Mock 테스트로 외부 API 의존성 제거
- 작업 후 PROGRESS.md 업데이트 필수

## 성능 벤치마크 (논문 기준)
- AAPL: +26.62%
- GOOGL: +24.36%
- AMZN: +23.21%
- 테스트 기간: 2024.01~03

## 주의사항
- 각 창은 자기 담당 파일만 수정
- 인터페이스 무단 변경 금지
- 테스트 없이 ✅ 표시 금지
- API 키는 절대 코드에 하드코딩 금지
