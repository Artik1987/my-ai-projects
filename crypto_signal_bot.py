# crypto_signal_bot.py — бот для отправки сигналов в канал
import asyncio
import json
import os
import time
import requests
import pandas as pd
import pandas_ta as ta
import ccxt
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# ── Биржи ──
spot_exchange = ccxt.binance({'enableRateLimit': True})
futures_exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
kucoin_exchange = ccxt.kucoin({'enableRateLimit': True})
bybit_futures = ccxt.bybit({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})
okx_futures = ccxt.okx({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})

# ── Настройки ──
STATE_FILE = "signals_state.json"
STATUS_FILE = "last_status.txt"
DEPOSIT = 1000
RISK_PERCENT = 1
LEVERAGE = 20


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_top_100_symbols():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        return [c["symbol"].upper() for c in r.json()]
    except Exception as e:
        print(f"Ошибка CoinGecko: {e}")
        return ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOGE", "DOT", "LINK"]


def fetch_ohlcv(exchange, symbol, timeframe='1h', limit=100):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception as e:
        # Печатаем ошибку, чтобы понять, что сломано
        print(f"    ⚠️ Ошибка {symbol}: {str(e)[:100]}")
        return None


def calculate_indicators(df):
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema50'] = ta.ema(df['close'], length=50)
    return df


def get_spot_signal(df):
    last = df.iloc[-1]
    if pd.isna(last['rsi']) or pd.isna(last['ema20']) or pd.isna(last['ema50']):
        return None
    
    atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
    if pd.isna(atr):
        return None

    price = last['close']
    
    if last['rsi'] < 30 and last['ema20'] > last['ema50']:
        return {"signal": "BUY", "entry": price, "sl": price - atr * 1.5, "tp": price + atr * 3.0}
    elif last['rsi'] > 70 and last['ema20'] < last['ema50']:
        return {"signal": "SELL", "entry": price, "sl": price + atr * 1.5, "tp": price - atr * 3.0}
    return None


def get_futures_signal(df):
    last = df.iloc[-1]
    if pd.isna(last['rsi']) or pd.isna(last['ema20']) or pd.isna(last['ema50']):
        return None
    price = last['close']
    
    if last['rsi'] < 40 and last['ema20'] > last['ema50'] and price > last['ema20']:
        signal = "LONG"
        sl = price * 0.98
        tp = price * 1.04
    elif last['rsi'] > 60 and last['ema20'] < last['ema50'] and price < last['ema20']:
        signal = "SHORT"
        sl = price * 1.02
        tp = price * 0.96
    else:
        return None

    risk_amount = DEPOSIT * (RISK_PERCENT / 100)
    price_diff = abs(price - sl)
    
    if price_diff == 0:
        return None
        
    position_size = risk_amount / price_diff

    return {
        "signal": signal, 
        "entry": price, 
        "sl": sl, 
        "tp": tp, 
        "diff": price_diff, 
        "size": position_size
    }


async def send_status_if_due(coins_checked: int, futures_checked: int):
    STATUS_INTERVAL_HOURS = 4

    last_status_ts = 0
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                last_status_ts = float(f.read().strip())
        except Exception:
            pass

    hours_passed = (time.time() - last_status_ts) / 3600
    if hours_passed < STATUS_INTERVAL_HOURS:
        print(f"  Статус не отправляем (последний был {hours_passed:.1f} ч назад)")
        return

    text = (
        "✅ <b>Проверка завершена успешно</b>\n\n"
        f"📊 Просканировано монет: <b>{coins_checked}</b> (спот)\n"
        f"📈 Проверено фьючерсов: <b>{futures_checked}</b> (Топ-30)\n\n"
        "🎯 <b>Хороших точек входа сейчас нет.</b>\n\n"
        "⏳ Следующая проверка через час.\n"
        "💡 Мы не завышаем риски ради сигнала — ждём идеальных условий по RSI и EMA."
    )

    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML")
        with open(STATUS_FILE, "w") as f:
            f.write(str(time.time()))
        print("  ✅ Статус отправлен в канал")
    except Exception as e:
        print(f"  ❌ Не удалось отправить статус: {e}")


async def check_and_send_signals():
    state = load_state()
    new_state = state.copy()
    signals_sent = 0
    coins_checked = 0
    futures_checked = 0

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="📈 Торговать на бирже", url="https://твоя-реф-ссылка.com"),
                types.InlineKeyboardButton(text="📰 Новости", url="https://твой-новостной-сервис.com")
            ]
        ]
    )

    # ── 1. Спот ──
    symbols = get_top_100_symbols()
    stablecoins = {'USDT', 'USDC', 'DAI', 'BUSD', 'TUSD', 'USDD', 'FDUSD'}
    symbols = [s for s in symbols if s not in stablecoins]

    print(f"[{datetime.now().strftime('%H:%M')}] Проверяем спот для {len(symbols)} монет...")

    for sym in symbols:
        df = fetch_ohlcv(spot_exchange, f'{sym}/USDT')
        if df is None:
            df = fetch_ohlcv(kucoin_exchange, f'{sym}/USDT')
        if df is None or len(df) < 50:
            continue

        coins_checked += 1
        df = calculate_indicators(df)
        signal_data = get_spot_signal(df)

        key = f"{sym}_SPOT"
        old_signal = state.get(key, "HOLD")
        current_signal = signal_data["signal"] if signal_data else "HOLD"

        if current_signal != old_signal and current_signal != "HOLD":
            emoji = "🟢" if current_signal == "BUY" else "🔴"
            action = "Покупаем" if current_signal == "BUY" else "Продаем"
            text = (
                f"{emoji} <b>{current_signal} (SPOT)</b>\n"
                f"Монета: <b>{sym}/USDT</b>\n"
                f"{action} сейчас по цене: <b>{signal_data['entry']:.4f}</b>\n"
                f"🎯 Цель (тейк-профит): <b>{signal_data['tp']:.4f}</b>\n"
                f"🛑 Стоп-лосс: <b>{signal_data['sl']:.4f}</b>\n"
                f"RSI: {df['rsi'].iloc[-1]:.1f}\n"
                f"#спот #{sym.lower()}"
            )
            try:
                await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML", reply_markup=keyboard)
                print(f"  ✅ {sym}: {old_signal} -> {current_signal}")
                signals_sent += 1
            except Exception as e:
                print(f"  ❌ Не удалось отправить сообщение для {sym}: {e}")

        new_state[key] = current_signal
        await asyncio.sleep(0.6)

        # ── 2. Фьючерсы ──
    top_100 = get_top_100_symbols()
    futures_symbols = [s for s in top_100 if s not in stablecoins][:30]

    print(f"[{datetime.now().strftime('%H:%M')}] Проверяем фьючерсы для {len(futures_symbols)} монет...")

    for sym in futures_symbols:
        df = None
        
        # Вариант 1: Пробуем Bybit (он лучше работает с GitHub)
        df = fetch_ohlcv(bybit_futures, f'{sym}/USDT:USDT')
        if df is None:
            df = fetch_ohlcv(bybit_futures, f'1000{sym}/USDT:USDT')
            
        # Вариант 2: Если Bybit не дал, пробуем Binance
        if df is None:
            df = fetch_ohlcv(futures_exchange, f'{sym}/USDT:USDT')
        if df is None:
            df = fetch_ohlcv(futures_exchange, f'1000{sym}/USDT:USDT')
            
        # Вариант 3: Если ничего не вышло, пробуем OKX
        if df is None:
            df = fetch_ohlcv(okx_futures, f'{sym}/USDT:USDT')
            
        # Если данных нет ни с одной биржи — пропускаем
        if df is None or len(df) < 50:
            continue

        futures_checked += 1
        df = calculate_indicators(df)
        signal_data = get_futures_signal(df)

        key = f"{sym}_FUTURES"
        old_signal = state.get(key, "HOLD")
        current_signal = signal_data["signal"] if signal_data else "HOLD"

        if current_signal != old_signal and current_signal != "HOLD":
            direction_emoji = "📈" if current_signal == "LONG" else "📉"
            risk_usd = DEPOSIT * RISK_PERCENT / 100
            text = (
                f"<b>SHARK FUTURES | VIP 🦈🔒</b>\n"
                f"#{sym} {current_signal} {direction_emoji}\n\n"
                f"Плечо: <b>{LEVERAGE}x</b>\n\n"
                f"Вход: <b>{signal_data['entry']:.4f}</b> (MARKET)\n\n"
                f"Тр:\n<b>{signal_data['tp']:.4f}</b>\n\n"
                f"Stop:\n<b>{signal_data['sl']:.4f}</b>\n\n"
                f"Риск высокий!\n\n"
                f"❗️ <b>Примечание</b> ❗️\n\n"
                f"Депо: {DEPOSIT}$\n"
                f"Риск на сделку {RISK_PERCENT}% (это {risk_usd:.0f}$ от {DEPOSIT}$)\n\n"
                f"{signal_data['entry']:.4f} - {signal_data['sl']:.4f} = <b>{signal_data['diff']:.4f}</b>\n\n"
                f"{risk_usd:.0f}$ / {signal_data['diff']:.4f} = <b>{signal_data['size']:.0f} монет</b> понадобится для открытия позиции"
            )
            try:
                await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML", reply_markup=keyboard)
                print(f"  ✅ {sym}: {old_signal} -> {current_signal}")
                signals_sent += 1
            except Exception as e:
                print(f"  ❌ Не удалось отправить сообщение для {sym}: {e}")

        new_state[key] = current_signal
        await asyncio.sleep(0.5)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🤖 Я бот для отправки сигналов.\n"
        "Работаю автоматически на GitHub Actions.\n\n"
        f"Канал: {CHANNEL_ID}"
    )

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    state = load_state()
    text = "📊 <b>Текущие сигналы:</b>\n\n"
    for key, sig in state.items():
        text += f"{key}: {sig}\n"
    await message.answer(text, parse_mode="HTML")


async def main():
    print("🤖 Запуск проверки сигналов (GitHub Actions режим).")
    print(f"📢 Канал: {CHANNEL_ID}")
    
    await check_and_send_signals()

if __name__ == "__main__":
    asyncio.run(main())