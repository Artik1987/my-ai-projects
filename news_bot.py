import asyncio
import feedparser
import os
import time
import re
from dotenv import load_dotenv
from aiogram import Bot
import trafilatura
from deep_translator import GoogleTranslator, MyMemoryTranslator

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("NEWS_CHANNEL_ID")
bot = Bot(token=BOT_TOKEN)

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://www.theblock.co/rss.xml",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
]

SENT_NEWS_FILE = "sent_news.txt"

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


def translate_text(text: str) -> str:
    """Гибридный перевод: Google -> MyMemory. Если оба не сработали — возвращает пустую строку."""
    if not text or len(text.strip()) < 10:
        return text

    text = text[:1500]

    # 1. Google Translate
    try:
        translated = GoogleTranslator(source='auto', target='ru').translate(text)
        if translated and len(translated) > 5:
            return translated
    except Exception as e:
        print(f"  Google Translate не сработал: {e}. Пробуем MyMemory...")

    # 2. MyMemory с правильными кодами
    try:
        translated = MyMemoryTranslator(source='en-US', target='ru-RU').translate(text)
        if translated and len(translated) > 5:
            return translated
    except Exception as e:
        print(f"  MyMemory тоже не сработал: {e}")

    # Если оба не смогли — возвращаем пустую строку, чтобы новость пропустилась
    print("  ❌ Не удалось перевести текст, новость пропускается")
    return ""


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
                print(f"  ⚠️ Лента пуста: {feed_url}")
                continue
            print(f"  Найдено {len(feed.entries)} записей")

            for entry in feed.entries[:3]:
                if entry.link in sent_news:
                    continue

                print(f"    Обработка: {entry.title[:50]}...")
                full_text = get_full_article_text(entry.link)
                if not full_text:
                    print("    ❌ Не удалось извлечь текст, пропускаем")
                    continue

                translated_title = translate_text(entry.title)
                time.sleep(1)
                translated_text = translate_text(full_text)

                # Если перевод не удался — пропускаем новость
                if not translated_text:
                    continue

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
                    print("    ✅ Отправлено")
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"    ❌ Ошибка отправки: {e}")
        except Exception as e:
            print(f"  ❌ Ошибка при чтении {feed_url}: {e}")

    if new_news_found:
        save_sent_news(sent_news)
        print("✅ Новые новости отправлены.")
    else:
        print("Новых новостей нет.")


async def main():
    print("🤖 Запуск бота-агрегатора новостей (гибридный перевод).")
    try:
        await check_news()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())