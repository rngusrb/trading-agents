"""
reports/generator.py — HTML 리포트 생성기
에이전트 분석 결과를 HTML 리포트로 저장
"""
import os
import json
from datetime import datetime


def generate_report(data, mode: str = 'single') -> str:
    """
    HTML 리포트 생성

    Args:
        data: single 모드 = TradingAgentState, backtest 모드 = results dict
        mode: 'single' 또는 'backtest'

    Returns:
        str: 저장된 리포트 경로
    """
    os.makedirs('reports', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if mode == 'single':
        html = _generate_single_report(data, timestamp)
        filename = f"reports/single_{data.get('ticker','UNKNOWN')}_{timestamp}.html"
    else:
        html = _generate_backtest_report(data, timestamp)
        filename = f"reports/backtest_{data.get('ticker','UNKNOWN')}_{timestamp}.html"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    return filename


def _signal_color(signal: str) -> str:
    """신호에 따른 색상 반환"""
    return {'bullish': '#22c55e', 'bearish': '#ef4444', 'neutral': '#f59e0b'}.get(signal, '#6b7280')


def _action_color(action: str) -> str:
    """액션에 따른 색상 반환"""
    return {'buy': '#22c55e', 'sell': '#ef4444', 'short': '#dc2626', 'cover': '#16a34a', 'hold': '#6b7280'}.get(action, '#6b7280')


def _generate_single_report(state: dict, timestamp: str) -> str:
    """단일 분석 HTML 리포트 생성"""
    ticker = state.get('ticker', 'N/A')
    date = state.get('date', 'N/A')
    analyst_reports = state.get('analyst_reports', [])
    research_report = state.get('research_report')
    decision = state.get('trade_decision')

    # Analyst rows
    analyst_rows = ""
    for r in analyst_reports:
        color = _signal_color(r.signal)
        analyst_rows += f"""
        <tr>
            <td>{r.analyst_type}</td>
            <td><span style="color:{color};font-weight:bold">{r.signal.upper()}</span></td>
            <td>{r.confidence:.0%}</td>
            <td>{r.summary[:120]}...</td>
        </tr>"""

    # Key points
    key_points_html = ""
    for r in analyst_reports:
        key_points_html += f'<h4 style="margin-top:16px">{r.analyst_type.upper()} 핵심 포인트</h4><ul>'
        for point in r.key_points:
            key_points_html += f'<li>{point}</li>'
        key_points_html += '</ul>'

    # Research
    bull_case = research_report.bull_case.replace('\n', '<br>') if research_report else 'N/A'
    bear_case = research_report.bear_case.replace('\n', '<br>') if research_report else 'N/A'
    consensus = research_report.consensus.upper() if research_report else 'N/A'
    conviction = f"{research_report.conviction:.0%}" if research_report else 'N/A'

    # Decision
    action = decision.action.upper() if decision else 'N/A'
    action_color = _action_color(decision.action) if decision else '#6b7280'
    quantity = f"{decision.quantity:.0%}" if decision else 'N/A'
    risk_score = f"{decision.risk_score:.0%}" if decision else 'N/A'
    approved = '승인' if (decision and decision.approved) else '거절'
    reasoning = decision.reasoning if decision else 'N/A'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TradingAgents Report — {ticker} {date}</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#0f172a;color:#e2e8f0}}
  .container{{max-width:1100px;margin:0 auto;padding:24px}}
  h1{{color:#f8fafc;border-bottom:2px solid #334155;padding-bottom:12px}}
  h2{{color:#94a3b8;font-size:1rem;text-transform:uppercase;letter-spacing:.05em;margin-top:32px}}
  .card{{background:#1e293b;border-radius:12px;padding:20px;margin:12px 0;border:1px solid #334155}}
  table{{width:100%;border-collapse:collapse}}
  th{{background:#334155;color:#94a3b8;padding:10px;text-align:left;font-size:.85rem}}
  td{{padding:10px;border-bottom:1px solid #1e293b;font-size:.9rem}}
  tr:hover td{{background:#1e293b}}
  .decision-box{{display:flex;gap:16px;flex-wrap:wrap}}
  .metric{{background:#0f172a;border-radius:8px;padding:16px;flex:1;min-width:120px;text-align:center}}
  .metric .value{{font-size:1.8rem;font-weight:bold;margin:8px 0}}
  .metric .label{{color:#64748b;font-size:.8rem}}
  .bull{{background:#052e16;border:1px solid #16a34a;border-radius:8px;padding:16px;margin:8px 0}}
  .bear{{background:#450a0a;border:1px solid #dc2626;border-radius:8px;padding:16px;margin:8px 0}}
  .reasoning{{background:#0f172a;border-radius:8px;padding:16px;font-size:.9rem;line-height:1.6;color:#cbd5e1}}
</style>
</head>
<body>
<div class="container">
  <h1>TradingAgents 분석 리포트</h1>
  <p style="color:#64748b">종목: <strong style="color:#f8fafc">{ticker}</strong> &nbsp;|&nbsp; 날짜: <strong style="color:#f8fafc">{date}</strong> &nbsp;|&nbsp; 생성: {timestamp}</p>

  <h2>애널리스트 신호</h2>
  <div class="card">
    <table>
      <thead><tr><th>에이전트</th><th>신호</th><th>신뢰도</th><th>요약</th></tr></thead>
      <tbody>{analyst_rows}</tbody>
    </table>
  </div>

  <h2>핵심 분석 포인트</h2>
  <div class="card">{key_points_html}</div>

  <h2>Bull/Bear 토론</h2>
  <div class="bull"><strong style="color:#22c55e">BULL CASE</strong><br><br>{bull_case}</div>
  <div class="bear"><strong style="color:#ef4444">BEAR CASE</strong><br><br>{bear_case}</div>
  <div class="card">
    <strong>리서치 합의:</strong> <span style="font-weight:bold;font-size:1.1rem">{consensus}</span>
    &nbsp;|&nbsp; 확신도: {conviction}
  </div>

  <h2>최종 트레이딩 결정</h2>
  <div class="card">
    <div class="decision-box">
      <div class="metric"><div class="value" style="color:{action_color}">{action}</div><div class="label">액션</div></div>
      <div class="metric"><div class="value">{quantity}</div><div class="label">포지션 비중</div></div>
      <div class="metric"><div class="value">{risk_score}</div><div class="label">리스크</div></div>
      <div class="metric"><div class="value">{approved}</div><div class="label">승인</div></div>
    </div>
    <div class="reasoning" style="margin-top:16px">{reasoning}</div>
  </div>
</div>
</body>
</html>"""


def _generate_backtest_report(results: dict, timestamp: str) -> str:
    """백테스팅 HTML 리포트 생성"""
    ticker = results.get('ticker', 'N/A')
    start_date = results.get('start_date', 'N/A')
    end_date = results.get('end_date', 'N/A')
    total_return = results.get('total_return_pct', 0)
    bnh_return = results.get('buy_and_hold_return_pct', 0)
    sharpe = results.get('sharpe_ratio', 0)
    max_dd = results.get('max_drawdown_pct', 0)
    total_trades = results.get('total_trades', 0)
    win_rate = results.get('win_rate', 0)
    initial_capital = results.get('initial_capital', 100000)
    final_value = results.get('final_value', initial_capital)

    return_color = '#22c55e' if total_return >= 0 else '#ef4444'
    vs_bnh = total_return - bnh_return
    vs_color = '#22c55e' if vs_bnh >= 0 else '#ef4444'

    # Portfolio value chart data
    portfolio_values = results.get('portfolio_values', [])
    chart_labels = json.dumps([pv['date'] for pv in portfolio_values])
    chart_data = json.dumps([pv['total_value'] for pv in portfolio_values])

    # Trades table
    trades = results.get('trades', [])
    trade_rows = ""
    for t in trades:
        action_color = _action_color(t.get('action', 'hold'))
        trade_rows += f"""
        <tr>
          <td>{t.get('date','')}</td>
          <td><span style="color:{action_color};font-weight:bold">{t.get('action','').upper()}</span></td>
          <td>{t.get('shares',0):.2f}</td>
          <td>${t.get('price',0):.2f}</td>
          <td>${t.get('value',0):,.2f}</td>
        </tr>"""

    if not trade_rows:
        trade_rows = '<tr><td colspan="5" style="text-align:center;color:#64748b">거래 내역 없음</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TradingAgents Backtest — {ticker}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#0f172a;color:#e2e8f0}}
  .container{{max-width:1100px;margin:0 auto;padding:24px}}
  h1{{color:#f8fafc;border-bottom:2px solid #334155;padding-bottom:12px}}
  h2{{color:#94a3b8;font-size:1rem;text-transform:uppercase;letter-spacing:.05em;margin-top:32px}}
  .card{{background:#1e293b;border-radius:12px;padding:20px;margin:12px 0;border:1px solid #334155}}
  .metrics{{display:flex;gap:16px;flex-wrap:wrap}}
  .metric{{background:#1e293b;border-radius:12px;padding:20px;flex:1;min-width:150px;text-align:center;border:1px solid #334155}}
  .metric .value{{font-size:2rem;font-weight:bold;margin:8px 0}}
  .metric .label{{color:#64748b;font-size:.8rem}}
  table{{width:100%;border-collapse:collapse}}
  th{{background:#334155;color:#94a3b8;padding:10px;text-align:left;font-size:.85rem}}
  td{{padding:10px;border-bottom:1px solid #334155;font-size:.9rem}}
  .chart-container{{position:relative;height:300px}}
</style>
</head>
<body>
<div class="container">
  <h1>백테스팅 리포트</h1>
  <p style="color:#64748b">종목: <strong style="color:#f8fafc">{ticker}</strong> &nbsp;|&nbsp; 기간: <strong style="color:#f8fafc">{start_date} ~ {end_date}</strong> &nbsp;|&nbsp; 생성: {timestamp}</p>

  <h2>성과 지표</h2>
  <div class="metrics">
    <div class="metric"><div class="value" style="color:{return_color}">{total_return:+.2f}%</div><div class="label">총 수익률</div></div>
    <div class="metric"><div class="value">{bnh_return:+.2f}%</div><div class="label">Buy &amp; Hold</div></div>
    <div class="metric"><div class="value" style="color:{vs_color}">{vs_bnh:+.2f}%</div><div class="label">초과 수익</div></div>
    <div class="metric"><div class="value">{sharpe:.3f}</div><div class="label">샤프 비율</div></div>
    <div class="metric"><div class="value" style="color:#ef4444">{max_dd:.2f}%</div><div class="label">최대 낙폭</div></div>
    <div class="metric"><div class="value">{total_trades}</div><div class="label">총 거래</div></div>
    <div class="metric"><div class="value">{win_rate:.1f}%</div><div class="label">승률</div></div>
    <div class="metric"><div class="value">${final_value:,.0f}</div><div class="label">최종 가치</div></div>
  </div>

  <h2>포트폴리오 가치 추이</h2>
  <div class="card">
    <div class="chart-container">
      <canvas id="portfolioChart"></canvas>
    </div>
  </div>

  <h2>거래 내역</h2>
  <div class="card">
    <table>
      <thead><tr><th>날짜</th><th>액션</th><th>수량</th><th>가격</th><th>금액</th></tr></thead>
      <tbody>{trade_rows}</tbody>
    </table>
  </div>
</div>
<script>
const ctx = document.getElementById('portfolioChart').getContext('2d');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: {chart_labels},
    datasets: [{{
      label: '포트폴리오 가치',
      data: {chart_data},
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59,130,246,0.1)',
      fill: true,
      tension: 0.3,
      pointRadius: 2,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{legend: {{labels: {{color: '#e2e8f0'}}}}}},
    scales: {{
      x: {{ticks: {{color: '#64748b', maxTicksLimit: 10}}, grid: {{color: '#334155'}}}},
      y: {{ticks: {{color: '#64748b', callback: v => '$' + v.toLocaleString()}}, grid: {{color: '#334155'}}}}
    }}
  }}
}});
</script>
</body>
</html>"""
