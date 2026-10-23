# crypto_signal_bot.py — бот для отправки сигналов в канал
import asyncio
import json
import os
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

STATE_FILE = "signals_state.json"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_top_100_symbols():
    """Возвращает список тикеров топ-100 монет по капитализации."""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": 1}
    try:
        r = requests.get(url, params=params, timeout=10)
        return [c["symbol"].upper() for c in r.json()]
    except Exception as e:
        print(f"Ошибка CoinGecko: {e}")
        return ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOGE", "DOT", "LINK",
                "TRX", "MATIC", "SHIB", "LTC", "BCH", "UNI", "ATOM", "XLM", "ETC", "FIL"]


def fetch_ohlcv(exchange, symbol, timeframe='1h', limit=100):
    """Загружает свечи с биржи."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception:
        return None


def calculate_indicators(df):
    """Добавляет RSI и EMA в DataFrame."""
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema20'] = ta.ema(df['close'], length=20)
    df['ema50'] = ta.ema(df['close'], length=50)
    return df


def get_spot_signal(df):
    """Генерирует спотовый сигнал с уровнями TP и SL на основе ATR."""
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
    """Генерирует фьючерсный сигнал с уровнями TP и SL."""
    last = df.iloc[-1]
    if pd.isna(last['rsi']) or pd.isna(last['ema20']) or pd.isna(last['ema50']):
        return None
    price = last['close']
    if last['rsi'] < 40 and last['ema20'] > last['ema50'] and price > last['ema20']:
        return {"signal": "LONG", "entry": price, "sl": price * 0.98, "tp": price * 1.04}
    elif last['rsi'] > 60 and last['ema20'] < last['ema50'] and price < last['ema20']:
        return {"signal": "SHORT", "entry": price, "sl": price * 1.02, "tp": price * 0.96}
    return None


async def check_and_send_signals():
    """Главная функция проверки и отправки сигналов."""
    state = load_state()
    new_state = state.copy()

    # Создаём клавиатуру с реферальными ссылками (используем types.)
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="📈 Торговать на бирже", url="https://твоя-реф-ссылка.com"),
                types.InlineKeyboardButton(text="📰 Новости", url="https://твой-новостной-сервис.com")
            ]
        ]
    )

    # ── 1. Спот сигналы (топ-100 монет) ──
    symbols = get_top_100_symbols()
    stablecoins = {'USDT', 'USDC', 'DAI', 'BUSD', 'TUSD', 'USDD', 'FDUSD'}
    symbols = [s for s in symbols if s not in stablecoins]

    print(f"[{datetime.now().strftime('%H:%M')}] Проверяем спот для {len(symbols)} монет...")

    for sym in symbols:
        df = fetch_ohlcv(spot_exchange, f'{sym}/USDT')
        if df is None or len(df) < 50:
            continue

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
            except Exception as e:
                print(f"  ❌ Не удалось отправить сообщение для {sym}: {e}")

        new_state[key] = current_signal
        await asyncio.sleep(0.6)

    # ── 2. Фьючерсные сигналы (BTC, ETH) ──
    print(f"[{datetime.now().strftime('%H:%M')}] Проверяем фьючерсы для BTC, ETH...")

    for sym in ["BTC", "ETH"]:
        df = fetch_ohlcv(futures_exchange, f'{sym}/USDT:USDT')
        if df is None or len(df) < 50:
            continue

        df = calculate_indicators(df)
        signal_data = get_futures_signal(df)

        key = f"{sym}_FUTURES"
        old_signal = state.get(key, "HOLD")
        current_signal = signal_data["signal"] if signal_data else "HOLD"

        if current_signal != old_signal and current_signal != "HOLD":
            emoji = "📈" if current_signal == "LONG" else "📉"
            action = "Открываем LONG" if current_signal == "LONG" else "Открываем SHORT"
            text = (
                f"{emoji} <b>{current_signal} (FUTURES)</b>\n"
                f"Монета: <b>{sym}/USDT</b>\n"
                f"{action} по цене: <b>{signal_data['entry']:.2f}</b>\n"
                f"🎯 Цель (тейк-профит): <b>{signal_data['tp']:.2f}</b>\n"
                f"🛑 Стоп-лосс: <b>{signal_data['sl']:.2f}</b>\n"
                f"RSI: {df['rsi'].iloc[-1]:.1f}\n"
                f"#фьючерс #{sym.lower()}"
            )
            try:
                await bot.send_message(chat_id=CHANNEL_ID, text=text, parse_mode="HTML", reply_markup=keyboard)
                print(f"  ✅ {sym}: {old_signal} -> {current_signal}")
            except Exception as e:
                print(f"  ❌ Не удалось отправить сообщение для {sym}: {e}")

        new_state[key] = current_signal
        await asyncio.sleep(1)

    save_state(new_state)
    print(f"[{datetime.now().strftime('%H:%M')}] Проверка завершена.")


# ── Команды для управления ботом (в личке бота) ──
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
    
    # Запускаем проверку один раз
    await check_and_send_signals()

if __name__ == "__main__":
    asyncio.run(main())