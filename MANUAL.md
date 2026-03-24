# TradingAgents 시스템 메뉴얼

## 개요

TradingAgents는 LangGraph 기반 멀티에이전트 시스템입니다.
실제 투자 리서치 과정을 AI로 모사합니다. 여러 전문 AI 에이전트가 각자의 역할을 수행하고,
최종적으로 매수/매도/홀드 결정을 내립니다.

참조 논문: TradingAgents (arXiv:2412.20138)
논문 성과 벤치마크: AAPL +26.62%, GOOGL +24.36%, AMZN +23.21% (2024 Q1)

---

## 시스템 전체 흐름

```
입력: 종목코드 + 날짜
        ↓
[데이터 수집]
        ↓
[Analyst Team] ─ 4개 에이전트 순차 실행
  ├── Fundamentals Analyst  (재무제표, PER, ROE 등)
  ├── Sentiment Analyst     (Reddit 커뮤니티 여론)
  ├── News Analyst          (최근 뉴스 헤드라인)
  └── Technical Analyst     (RSI, MACD, 볼린저밴드 등)
        ↓
[Researcher Team] ─ 토론 구조
  ├── Bull Researcher  (매수 논거 강화)
  ├── Bear Researcher  (매도 논거 강화)
  └── Senior Analyst   (합의 도출)
        ↓
[Trader] ─ 최종 트레이딩 결정 (초안)
        ↓
[Risk Management Team] ─ 리스크 필터
  ├── Risky Analyst    (공격적 관점)
  ├── Neutral Analyst  (균형 관점)
  └── Safe Analyst     (보수적 관점)
        ↓
[Fund Manager] ─ 최종 승인/거절
        ↓
출력: TradeDecision (action, quantity, approved)
```

---

## 에이전트별 상세 설명

### 1. 데이터 수집 (fetch_data)

실행 파일: `tools/market_data.py`
사용 API: yfinance

하는 일:
- 지정한 날짜의 OHLCV 데이터 수집 (시가/고가/저가/종가/거래량)
- 이후 Technical Analyst에서 사용할 히스토리컬 데이터도 수집

출력: `MarketData` 객체
```
ticker, date, open, high, low, close, volume, indicators
```

---

### 2. Fundamentals Analyst (펀더멘털 분석)

실행 파일: `agents/fundamentals_analyst.py`
사용 API: Finnhub
사용 모델: claude-haiku (비용 절감)

하는 일:
- 기업 프로필 조회 (업종, 시총)
- 재무 지표 수집: PER, PBR, ROE, 부채비율, 매출 성장률
- 최근 4분기 EPS 실적 (어닝 서프라이즈 확인)
- 애널리스트 추천 트렌드
- 위 데이터를 Claude에게 전달 → bullish/bearish/neutral 판단

판단 기준 예시:
- PER < 20 + ROE > 15% → bullish 경향
- PER > 40 또는 ROE < 5% → bearish 경향

출력: `AnalystReport` (signal, confidence 0~1, summary, key_points)

---

### 3. Sentiment Analyst (감성 분석)

실행 파일: `agents/sentiment_analyst.py`
사용 API: Reddit PRAW
사용 모델: claude-haiku

하는 일:
- Reddit 4개 커뮤니티 검색: wallstreetbets, stocks, investing, StockMarket
- `$AAPL` 또는 `AAPL` 키워드로 최근 게시글 25개 수집
- 게시글 점수(upvote), 댓글 수, 인게이지먼트 계산
- 상위 5개 게시글 제목 Claude에게 전달 → 여론 판단

판단 기준 예시:
- 평균 점수 > 100 + 인게이지먼트 > 0.1 → bullish
- 평균 점수 < 0 → bearish

출력: `AnalystReport`

---

### 4. News Analyst (뉴스 분석)

실행 파일: `agents/news_analyst.py`
사용 API: Finnhub News
사용 모델: claude-haiku

하는 일:
- 기준 날짜 기준 최근 7일간 뉴스 수집
- 헤드라인 + 요약(500자) 추출
- 최근 10개 기사를 Claude에게 전달 → 주가 영향 판단

폴백 (LLM 실패 시) 키워드 분석:
- 긍정: beat, surge, growth, record, strong, upgrade
- 부정: miss, decline, fall, weak, downgrade, cut

출력: `AnalystReport`

---

### 5. Technical Analyst (기술적 분석)

실행 파일: `agents/technical_analyst.py`
사용 라이브러리: ta (Python 3.10 호환)
사용 모델: claude-haiku

하는 일:
- 최근 90일 히스토리컬 데이터 로드
- 기술적 지표 계산:

| 지표 | 설명 |
|------|------|
| RSI (14일) | 과매수(>70)/과매도(<30) 판단 |
| MACD | 추세 방향 및 강도 |
| 볼린저밴드 | 변동성 및 가격 위치 |
| SMA 20/50 | 단기/중기 이동평균 |
| EMA 12/26 | 지수이동평균 |
| ATR (14일) | 변동성 크기 |

- 지표 해석 후 Claude에게 전달 → 기술적 신호 판단

출력: `AnalystReport` + market_data.indicators 업데이트

---

### 6. Researcher (Bull/Bear 토론)

실행 파일: `agents/researcher.py`
사용 모델: claude-sonnet (고품질)

하는 일:
4개 애널리스트 보고서를 받아 3단계 토론 진행

**Step 1 - Bull Researcher:**
- 매수 논거를 최대한 강하게 구성
- 성장 잠재력, 저평가, 긍정적 촉매제에 집중

**Step 2 - Bear Researcher:**
- 매도 논거를 최대한 강하게 구성
- 하락 위험, 고평가, 부정적 촉매제에 집중

**Step 3 - Senior Analyst (합의):**
- 양쪽 논거를 모두 검토
- buy / sell / hold 중 합의 도출
- conviction (확신도 0~1) 산출

출력: `ResearchReport` (bull_case, bear_case, consensus, conviction)

---

### 7. Trader (트레이딩 결정)

실행 파일: `agents/trader.py`
사용 모델: claude-sonnet

하는 일:
리서치 보고서 + 4개 애널리스트 신호 + 현재 주가를 종합해 구체적 거래 지시 생성

포지션 크기 결정 규칙:
| conviction | quantity |
|-----------|----------|
| > 75% | 60~80% |
| 50~75% | 30~50% |
| < 50% | 10~30% |
| hold | 0% |

출력: `TradeDecision` (action, quantity, reasoning, risk_score, approved=False)
- 이 시점에서 approved=False. Risk Manager 승인 대기 상태

---

### 8. Risk Manager + Fund Manager (리스크 필터)

실행 파일: `agents/risk_manager.py`
사용 모델: claude-sonnet (3 Risk Analysts) + claude-opus (Fund Manager)

하는 일:
Trader의 초안 결정을 3명의 리스크 분석가가 검토

**Risky Analyst (공격적):**
- 수익 극대화 관점
- 좋은 기회면 더 큰 포지션 권장

**Neutral Analyst (균형):**
- 리스크/보상 균형
- 적정 포지션 선호

**Safe Analyst (보수적):**
- 자본 보전 최우선
- 포지션 축소 경향

**Fund Manager (최종 결정, claude-opus 사용):**
- 3명의 의견을 종합
- 거래 승인 / 포지션 크기 조정 / 거절 중 선택
- approved=True/False 결정

출력: `TradeDecision` (최종 수정본, approved=True/False)

---

## 데이터 모델

모든 에이전트 간 데이터는 Pydantic 모델로 검증됩니다.

### AnalystReport
```python
analyst_type: "fundamentals" | "sentiment" | "news" | "technical"
ticker: str
date: str              # YYYY-MM-DD
signal: "bullish" | "bearish" | "neutral"
confidence: float      # 0.0 ~ 1.0
summary: str
key_points: list[str]  # 핵심 포인트
data_sources: list[str]
```

### ResearchReport
```python
ticker: str
date: str
bull_case: str         # 매수 논거
bear_case: str         # 매도 논거
consensus: "buy" | "sell" | "hold"
conviction: float      # 0.0 ~ 1.0
```

### TradeDecision
```python
ticker: str
date: str
action: "buy" | "sell" | "hold"
quantity: float        # 0.0 ~ 1.0 (자본 비중)
reasoning: str
risk_score: float      # 0.0 (저위험) ~ 1.0 (고위험)
approved: bool         # Fund Manager 승인 여부
```

---

## LLM 모델 전략 (비용 최적화)

| 에이전트 | 모델 | 이유 |
|---------|------|------|
| 4개 Analyst | claude-haiku | 반복 실행, 비용 절감 |
| Researcher, Trader, Risk Analysts | claude-sonnet | 고품질 분석 필요 |
| Fund Manager | claude-opus | 최종 결정, 최고 품질 |

단일 분석 시 Claude API 호출 횟수: 총 **10회**
- Analyst 4회 (haiku)
- Bull/Bear/Consensus 3회 (sonnet)
- Trader 1회 (sonnet)
- Risk Analysts 3회 (sonnet)
- Fund Manager 1회 (opus)

---

## 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
pip install ta  # pandas-ta 대신 (Python 3.10 호환)
```

### 2. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일에서 API 키 입력
```

필요한 API 키:
- `ANTHROPIC_API_KEY`: https://console.anthropic.com
- `FINNHUB_API_KEY`: https://finnhub.io (무료 플랜 가능)
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`: https://www.reddit.com/prefs/apps (없어도 동작)

### 3. 실행

**단일 날짜 분석:**
```bash
python main.py --mode single --ticker AAPL --date 2024-01-15
```

**백테스팅 (2024 Q1):**
```bash
python main.py --mode backtest --ticker AAPL --start 2024-01-02 --end 2024-03-29
```

**다른 종목:**
```bash
python main.py --mode single --ticker GOOGL --date 2024-01-15
python main.py --mode backtest --ticker AMZN --start 2024-01-02 --end 2024-03-29
```

---

## 백테스팅 엔진 동작 방식

실행 파일: `backtest/engine.py`

1. 지정 기간의 히스토리컬 가격 데이터 로드
2. 매 5 영업일마다 파이프라인 실행 (기본값, 변경 가능)
3. `approved=True`인 결정만 실제 거래 실행
4. 매수: 가용 현금의 `quantity` 비율만큼 투자
5. 매도: 보유 주식의 `quantity` 비율만큼 매도
6. 수수료: 거래금액의 0.1% 부과
7. 종료 시 전체 포지션 청산

**성과 지표:**
- 총 수익률 (vs Buy & Hold 비교)
- 샤프 비율 (연환산, 무위험수익률 5% 기준)
- 최대 낙폭 (MDD)
- 승률

---

## 폴백 메커니즘

각 에이전트는 API 실패 시 규칙 기반 분석으로 폴백합니다.
시스템이 절대 멈추지 않도록 설계되어 있습니다.

| 에이전트 | 폴백 동작 |
|---------|---------|
| Fundamentals | PER/ROE 기준 규칙 판단 |
| Sentiment | 게시글 점수/댓글 수 기준 판단 |
| News | 키워드 카운트 (beat/miss 등) |
| Technical | 지표 신호 다수결 |
| Researcher | hold 반환 |
| Trader | 리서치 합의 그대로 사용 |
| Fund Manager | risk_score < 0.6이면 승인 |

---

## 테스트

```bash
# 전체 테스트 (35개)
python -m pytest tests/ -v

# 개별 테스트
python -m pytest tests/test_schemas.py -v       # 데이터 모델
python -m pytest tests/test_analysts.py -v      # 4개 애널리스트
python -m pytest tests/test_researcher.py -v    # 리서처
python -m pytest tests/test_trader.py -v        # 트레이더 + 리스크
python -m pytest tests/test_backtest.py -v      # 백테스팅 엔진
```

모든 테스트는 Mock을 사용해 실제 API 호출 없이 실행됩니다.

---

## 파일 구조 요약

```
trading-agents/
├── main.py                      # 진입점
├── .env                         # API 키 (직접 생성)
├── .env.example                 # 환경변수 템플릿
│
├── agents/                      # AI 에이전트
│   ├── fundamentals_analyst.py
│   ├── sentiment_analyst.py
│   ├── news_analyst.py
│   ├── technical_analyst.py
│   ├── researcher.py
│   ├── trader.py
│   └── risk_manager.py
│
├── tools/                       # 데이터 수집
│   ├── market_data.py           # yfinance
│   ├── fundamentals.py          # Finnhub 재무
│   ├── news_fetcher.py          # Finnhub 뉴스
│   ├── social_data.py           # Reddit
│   └── technical_indicators.py  # ta 라이브러리
│
├── graph/                       # LangGraph
│   ├── state.py                 # 공유 상태 정의
│   └── workflow.py              # 파이프라인 연결
│
├── models/
│   └── schemas.py               # Pydantic 데이터 모델
│
├── backtest/
│   ├── engine.py                # 백테스팅 실행
│   └── metrics.py               # 성과 지표 계산
│
└── tests/                       # 단위 테스트 (35개)
```
