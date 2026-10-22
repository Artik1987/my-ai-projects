import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests

# ── Настройки бирж ──
spot_exchange = ccxt.binance({'enableRateLimit': True})
futures_exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

def fetch_ohlcv(exchange, symbol, timeframe='1h', limit=100):
    """Загружает свечи и возвращает DataFrame."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Ошибка загрузки {symbol}: {e}")
        return None

def calculate_indicators(df):
    """Добавляет RSI и EMA в DataFrame."""
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema50'] = ta.ema(df['close'], length=50)
    return df

def generate_spot_signal(df):
    """Генерирует спотовый сигнал на основе последних данных."""
    last = df.iloc[-1]
    if pd.isna(last['rsi']) or pd.isna(last['ema20']) or pd.isna(last['ema50']):
        return "HOLD (недостаточно данных)"
    if last['rsi'] < 30 and last['ema20'] > last['ema50']:
        return "BUY (SPOT)"
    elif last['rsi'] > 70 and last['ema20'] < last['ema50']:
        return "SELL (SPOT)"
    else:
        return "HOLD (SPOT)"

def generate_futures_signal(df):
    """Генерирует фьючерсный сигнал с ценой входа, стоп-лоссом и тейк-профитом."""
    last = df.iloc[-1]
    if pd.isna(last['rsi']) or pd.isna(last['ema20']) or pd.isna(last['ema50']):
        return None
    price = last['close']
    # Пример расчёта стоп-лосса и тейк-профита (2% и 4%)
    if last['rsi'] < 40 and last['ema20'] > last['ema50'] and price > last['ema20']:
        sl = price * 0.98
        tp = price * 1.04
        return f"LONG (FUTURES) | Вход: {price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}"
    elif last['rsi'] > 60 and last['ema20'] < last['ema50'] and price < last['ema20']:
        sl = price * 1.02
        tp = price * 0.96
        return f"SHORT (FUTURES) | Вход: {price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}"
    else:
        return "HOLD (FUTURES)"

if __name__ == "__main__":
    print("🔍 Тестируем генерацию сигналов для BTC...\n")

    # Спот BTC
    df_spot = fetch_ohlcv(spot_exchange, 'BTC/USDT')
    if df_spot is not None:
        df_spot = calculate_indicators(df_spot)
        spot_signal = generate_spot_signal(df_spot)
        print(f"📊 BTC Спот: {spot_signal}")
        print(f"   RSI: {df_spot['rsi'].iloc[-1]:.2f}, EMA20: {df_spot['ema20'].iloc[-1]:.2f}, EMA50: {df_spot['ema50'].iloc[-1]:.2f}, Цена: {df_spot['close'].iloc[-1]:.2f}\n")

    # Фьючерс BTC
    df_fut = fetch_ohlcv(futures_exchange, 'BTC/USDT:USDT')
    if df_fut is not None:
        df_fut = calculate_indicators(df_fut)
        fut_signal = generate_futures_signal(df_fut)
        print(f"📈 BTC Фьючерс: {fut_signal}")
        print(f"   RSI: {df_fut['rsi'].iloc[-1]:.2f}, EMA20: {df_fut['ema20'].iloc[-1]:.2f}, EMA50: {df_fut['ema50'].iloc[-1]:.2f}, Цена: {df_fut['close'].iloc[-1]:.2f}\n")