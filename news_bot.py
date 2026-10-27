import asyncio
import feedparser
import os
import time
import re
import json
import requests
from dotenv import load_dotenv
from aiogram import Bot
import trafilatura

load_dotenv()

# ── Настройки ──
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("NEWS_CHANNEL_ID")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = Bot(token=BOT_TOKEN)

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://www.theblock.co/rss.xml",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
]

SENT_NEWS_FILE = "sent_news.txt"

# ── Словарь: биржа → реферальная ссылка ──
EXCHANGES = {
    "OKX": "https://okx.com/join/QUZOCF6B",
    "Bybit": "https://www.bybit.com/invite?ref=GXBQDK",
    "Bitunix": "https://www.bitunix.top/u-link/referral/invitee?t_act=1&inviteCode=9asbmf",
    "BingX": "https://bingx.com/ru/activity/octsuperx?ref=FAQORB&ch=octsuperx",
    "WEEX": "https://weex.com/register?vipCode=5zzvr",
    "Walt": "https://telegram.me/walt/start?startapp=ref-3-5_WRCGJ5Cww",
    "Whitebird": "https://whitebird.io/signup?refid=vO7F7ENqLK",
    "KuCoin": "https://www.kucoin.com/r/rf/K4NQ2AMP",
    "CoinW": "https://www.coinw.com/ru_RU/register?r=2691250",
    "Bynex": "https://bynex.io/exchange/ru?token=rt1293804&utm_source=reflink",
    "Dzengi": "https://dzengi.com/trading/signup?c=s23g8mcm&pid=referral&src=gasgas",
}


def load_sent_news():
    if os.path.exists(SENT_NEWS_FILE):
        with open(SENT_NEWS_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()


def save_sent_news(news_set):
    with open(SENT_NEWS_FILE, "w", encoding="utf-8") as f:
        for link in news_set:
            f.write(f"{link}\n")


def get_full_article_text(url: str) -> str:
    """Скачивает страницу и извлекает основной текст статьи с повторными попытками."""
    for attempt in range(2):
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=False,
                    favor_recall=True
                )
                if text and len(text) > 100:
                    return text
            print(f"  Попытка {attempt + 1} не удалась для {url}")
            time.sleep(2)
        except Exception as e:
            print(f"  Ошибка извлечения (попытка {attempt + 1}): {e}")
    return ""


def translate_text_llm(text: str, max_retries: int = 2) -> str:
    """Переводит текст на русский с помощью LLM через OpenRouter."""
    if not text or len(text.strip()) < 10:
        return text

    # Обрезаем текст, чтобы не тратить лишние токены (для новости хватит 1500 символов)
    text = text[:1500]

    prompt = (
        "Переведи следующий текст на русский язык. "
        "Сохрани все факты, цифры и имена собственные. "
        "Перевод должен быть естественным и грамотным. "
        "Верни только перевод, без пояснений.\n\n"
        f"Текст:\n{text}"
    )

    for attempt in range(max_retries):
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": "qwen/qwen-2.5-72b-instruct",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                }),
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            translated_text = result["choices"][0]["message"]["content"]

            # Очищаем возможные лишние кавычки или пояснения от модели
            translated_text = translated_text.strip().strip('"').strip("'")

            if translated_text and len(translated_text) > 5:
                return translated_text

        except Exception as e:
            print(f"  Ошибка перевода через LLM (попытка {attempt + 1}): {e}")
            time.sleep(3)

    return text  # Если все попытки не удались — возвращаем оригинал


def find_exchange_in_text(text: str):
    if not text:
        return None, None
    text_upper = text.upper()
    for name, url in EXCHANGES.items():
        pattern = r'\b' + re.escape(name.upper()) + r'\b'
        if re.search(pattern, text_upper):
            return name, url
    return None, None


async def check_news():
    sent_news = load_sent_news()
    new_news_found = False
    print(f"[{time.strftime('%H:%M')}] Проверяем новости...")

    for feed_url in RSS_FEEDS:
        print(f"  Читаем ленту: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                print(f"  ⚠️ Лента пуста или недоступна: {feed_url}")
                continue
            print(f"  Найдено {len(feed.entries)} записей")

            for entry in feed.entries[:3]:
                if entry.link not in sent_news:
                    print(f"    Обработка: {entry.title[:50]}...")

                    full_text = get_full_article_text(entry.link)
                    if not full_text:
                        print(f"    ❌ Не удалось извлечь текст, пропускаем")
                        continue

                    # Переводим заголовок и текст через LLM
                    translated_title = translate_text_llm(entry.title)
                    time.sleep(1)
                    translated_text = translate_text_llm(full_text)

                    if translated_text:
                        if len(translated_text) > 3500:
                            translated_text = translated_text[:3500] + "..."

                        combined_text = translated_title + " " + translated_text
                        exchange_name, ref_link = find_exchange_in_text(combined_text)

                        message_text = f"📰 <b>{translated_title}</b>\n\n{translated_text}\n\n"
                        message_text += f"🔗 <a href='{entry.link}'>Источник</a>"

                        if exchange_name:
                            message_text += (
                                f"\n\n━━━━━━━━━━━━━━━\n"
                                f"💡 <b>Кстати!</b> Эту монету можно купить на бирже <b>{exchange_name}</b>.\n"
                                f"🎁 По моей ссылке — бонус при регистрации:\n"
                                f"👉 <a href='{ref_link}'>Зарегистрироваться на {exchange_name}</a>"
                            )
                            print(f"    💰 Найдено упоминание {exchange_name}")

                        try:
                            await bot.send_message(
                                chat_id=CHANNEL_ID,
                                text=message_text,
                                parse_mode="HTML",
                                disable_web_page_preview=True
                            )
                            sent_news.add(entry.link)
                            new_news_found = True
                            print(f"    ✅ Отправлено")
                            await asyncio.sleep(3)
                        except Exception as e:
                            print(f"    ❌ Ошибка отправки в Telegram: {e}")
                    else:
                        print(f"    ❌ Не удалось перевести текст")
        except Exception as e:
            print(f"  ❌ Ошибка при чтении {feed_url}: {e}")

    if new_news_found:
        save_sent_news(sent_news)
        print("✅ Новые новости отправлены.")
    else:
        print("Новых новостей нет.")


async def main():
    print("🤖 Запуск бота-агрегатора новостей (перевод через LLM).")
    await check_news()


if __name__ == "__main__":
    asyncio.run(main())