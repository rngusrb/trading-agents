"""
technical_indicators.py — ta 라이브러리 기반 기술적 지표 계산
(pandas-ta 대신 ta 라이브러리 사용 - Python 3.10 호환)
"""
import pandas as pd
import ta


def calculate_indicators(df: pd.DataFrame) -> dict:
    """
    OHLCV 데이터로 기술적 지표 계산

    Args:
        df: OHLCV DataFrame (Open, High, Low, Close, Volume 컬럼 필요)

    Returns:
        dict: RSI, MACD, Bollinger Bands, SMA, EMA, ATR 지표
    """
    if df.empty or len(df) < 2:
        return {}

    indicators = {}
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df.get('Volume', pd.Series(dtype=float))

    try:
        # RSI (14일)
        rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi()
        if not rsi.empty and not pd.isna(rsi.iloc[-1]):
            indicators['RSI_14'] = round(float(rsi.iloc[-1]), 2)

        # MACD
        macd_obj = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
        macd_line = macd_obj.macd()
        signal_line = macd_obj.macd_signal()
        hist = macd_obj.macd_diff()
        if not macd_line.empty and not pd.isna(macd_line.iloc[-1]):
            indicators['MACD'] = round(float(macd_line.iloc[-1]), 4)
        if not signal_line.empty and not pd.isna(signal_line.iloc[-1]):
            indicators['MACD_Signal'] = round(float(signal_line.iloc[-1]), 4)
        if not hist.empty and not pd.isna(hist.iloc[-1]):
            indicators['MACD_Hist'] = round(float(hist.iloc[-1]), 4)

        # Bollinger Bands (20일, 2σ)
        bb_obj = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        bbl = bb_obj.bollinger_lband()
        bbm = bb_obj.bollinger_mavg()
        bbu = bb_obj.bollinger_hband()
        if not bbl.empty and not pd.isna(bbl.iloc[-1]):
            indicators['BB_Lower'] = round(float(bbl.iloc[-1]), 2)
        if not bbm.empty and not pd.isna(bbm.iloc[-1]):
            indicators['BB_Middle'] = round(float(bbm.iloc[-1]), 2)
        if not bbu.empty and not pd.isna(bbu.iloc[-1]):
            indicators['BB_Upper'] = round(float(bbu.iloc[-1]), 2)

        # SMA 20, 50
        sma20 = ta.trend.SMAIndicator(close=close, window=20).sma_indicator()
        sma50 = ta.trend.SMAIndicator(close=close, window=50).sma_indicator()
        if not sma20.empty and not pd.isna(sma20.iloc[-1]):
            indicators['SMA_20'] = round(float(sma20.iloc[-1]), 2)
        if not sma50.empty and not pd.isna(sma50.iloc[-1]):
            indicators['SMA_50'] = round(float(sma50.iloc[-1]), 2)

        # EMA 12, 26
        ema12 = ta.trend.EMAIndicator(close=close, window=12).ema_indicator()
        ema26 = ta.trend.EMAIndicator(close=close, window=26).ema_indicator()
        if not ema12.empty and not pd.isna(ema12.iloc[-1]):
            indicators['EMA_12'] = round(float(ema12.iloc[-1]), 2)
        if not ema26.empty and not pd.isna(ema26.iloc[-1]):
            indicators['EMA_26'] = round(float(ema26.iloc[-1]), 2)

        # ATR (14일)
        atr = ta.volatility.AverageTrueRange(
            high=high, low=low, close=close, window=14
        ).average_true_range()
        if not atr.empty and not pd.isna(atr.iloc[-1]):
            indicators['ATR_14'] = round(float(atr.iloc[-1]), 4)

        # Volume SMA 20
        if not volume.empty:
            vol_sma = ta.trend.SMAIndicator(close=volume.astype(float), window=20).sma_indicator()
            if not vol_sma.empty and not pd.isna(vol_sma.iloc[-1]):
                indicators['Volume_SMA_20'] = int(vol_sma.iloc[-1])

    except Exception as e:
        print(f"Indicator calculation error: {e}")

    return indicators


def interpret_signals(indicators: dict, current_price: float) -> dict:
    """
    기술적 지표 신호 해석

    Args:
        indicators: calculate_indicators() 결과
        current_price: 현재 가격

    Returns:
        dict: 각 지표별 신호 (bullish/bearish/neutral)
    """
    signals = {}

    rsi = indicators.get('RSI_14')
    if rsi is not None:
        if rsi < 30:
            signals['RSI'] = 'bullish'
        elif rsi > 70:
            signals['RSI'] = 'bearish'
        else:
            signals['RSI'] = 'neutral'

    macd_hist = indicators.get('MACD_Hist')
    if macd_hist is not None:
        signals['MACD'] = 'bullish' if macd_hist > 0 else 'bearish'

    bb_upper = indicators.get('BB_Upper')
    bb_lower = indicators.get('BB_Lower')
    if bb_upper and bb_lower and current_price > 0:
        if current_price < bb_lower:
            signals['BB'] = 'bullish'
        elif current_price > bb_upper:
            signals['BB'] = 'bearish'
        else:
            signals['BB'] = 'neutral'

    sma20 = indicators.get('SMA_20')
    sma50 = indicators.get('SMA_50')
    if sma20 and sma50:
        signals['SMA_Trend'] = 'bullish' if sma20 > sma50 else 'bearish'

    return signals
