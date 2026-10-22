import ccxt
import time
import requests

# ── Спот Binance ──
spot_exchange = ccxt.binance({'enableRateLimit': True})

# ── Фьючерсы Binance (perpetual) ──
futures_exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

def get_top_30_symbols():
    """Топ-30 монет по капитализации через CoinGecko."""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 30, "page": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        return [c["symbol"].upper() for c in r.json()]
    except Exception as e:
        print(f"Ошибка CoinGecko: {e}")
        return ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOGE", "DOT", "LINK",
                "TRX", "MATIC", "SHIB", "LTC", "BCH", "UNI", "ATOM", "XLM", "ETC", "FIL",
                "APT", "ARB", "OP", "NEAR", "INJ", "SUI", "SEI", "TIA", "ICP", "RNDR"]

def fetch_spot(symbol, timeframe='1h', limit=100):
    """Свечи для спота с Binance."""
    try:
        return spot_exchange.fetch_ohlcv(f'{symbol}/USDT', timeframe, limit=limit)
    except Exception as e:
        return None

def fetch_futures(symbol, timeframe='1h', limit=100):
    """Свечи для фьючерсов с Binance (perpetual)."""
    try:
        return futures_exchange.fetch_ohlcv(f'{symbol}/USDT:USDT', timeframe, limit=limit)
    except Exception as e:
        return None

if __name__ == "__main__":
    symbols = get_top_30_symbols()
    stablecoins = {'USDT', 'USDC', 'DAI', 'BUSD', 'TUSD', 'USDD', 'FDUSD'}
    symbols = [s for s in symbols if s not in stablecoins]

    print(f"📊 Спот: загружаем данные для {len(symbols)} монет...")
    spot_ok = 0
    for sym in symbols:
        data = fetch_spot(sym)
        if data:
            spot_ok += 1
            print(f"  ✅ {sym}: {len(data)} свечей")
        else:
            print(f"  ❌ {sym}: нет данных")
        time.sleep(0.5)
    print(f"\nСпот: {spot_ok}/{len(symbols)} успешно\n")

    print(f"📈 Фьючерсы: загружаем BTC и ETH...")
    for sym in ["BTC", "ETH"]:
        data = fetch_futures(sym)
        if data:
            print(f"  ✅ {sym}: {len(data)} свечей (фьючерс)")
        else:
            print(f"  ❌ {sym}: нет данных")
        time.sleep(0.5)