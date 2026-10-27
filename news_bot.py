import asyncio
import feedparser
import os
import time
import re
from dotenv import load_dotenv
from aiogram import Bot
import trafilatura
from deep_translator import GoogleTranslator

load_dotenv()
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
CHANNEL_ID = os.getenv("NEWS_CHANNEL_ID")

RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://www.theblock.co/rss.xml",
]

SENT_NEWS_FILE = "sent_news.txt"

# ── Словарь: биржа → твоя реферальная ссылка ──
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
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            return text if text else ""
    except Exception as e:
        print(f"Ошибка извлечения текста из {url}: {e}")
    return ""


def translate_text(text: str) -> str:
    """Переводит текст на русский язык с защитой от rate-limit."""
    if not text:
        return ""
    try:
        max_len = 4000
        chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)]
        translated_chunks = []
        for chunk in chunks:
            translated_chunks.append(GoogleTranslator(source='auto', target='ru').translate(chunk))
            time.sleep(1)  # Пауза 1 секунда между запросами
        return " ".join(translated_chunks)
    except Exception as e:
        print(f"  Ошибка перевода: {e}")
        return text


def find_exchange_in_text(text: str):
    """
    Ищет в тексте упоминание любой из бирж.
    Возвращает (название_биржи, ссылка) или (None, None).
    """
    if not text:
        return None, None
    
    text_upper = text.upper()
    
    for name, url in EXCHANGES.items():
        # Ищем название биржи как отдельное слово (не часть другого слова)
        # Например, "OKX" не должен находиться внутри "BOKXY"
        pattern = r'\b' + re.escape(name.upper()) + r'\b'
        if re.search(pattern, text_upper):
            return name, url
    
    return None, None


async def check_news():
    sent_news = load_sent_news()
    new_news_found = False
    print(f"[{time.strftime('%H:%M')}] Проверяем новости...")

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                if entry.link not in sent_news:
                    print(f"  Обработка: {entry.title}")
                    
                    full_text = get_full_article_text(entry.link)
                    translated_title = translate_text(entry.title)
                    translated_text = translate_text(full_text)

                    if translated_text:
                        if len(translated_text) > 3500:
                            translated_text = translated_text[:3500] + "..."
                        
                        # ── Ищем упоминание биржи в тексте и заголовке ──
                        combined_text = translated_title + " " + translated_text
                        exchange_name, ref_link = find_exchange_in_text(combined_text)
                        
                        # ── Формируем сообщение ──
                        message_text = f"📰 <b>{translated_title}</b>\n\n{translated_text}\n\n"
                        message_text += f"🔗 <a href='{entry.link}'>Источник</a>"
                        
                        # ── Если нашли биржу — добавляем реф-ссылку ──
                        if exchange_name:
                            message_text += (
                                f"\n\n━━━━━━━━━━━━━━━\n"
                                f"💡 <b>Кстати!</b> Эту монету можно купить на бирже <b>{exchange_name}</b>.\n"
                                f"🎁 По моей ссылке — бонус при регистрации:\n"
                                f"👉 <a href='{ref_link}'>Зарегистрироваться на {exchange_name}</a>"
                            )
                            print(f"  💰 Найдено упоминание {exchange_name} — добавляем реф-ссылку")
                        
                        try:
                            await bot.send_message(
                                chat_id=CHANNEL_ID, 
                                text=message_text, 
                                parse_mode="HTML", 
                                disable_web_page_preview=True
                            )
                            sent_news.add(entry.link)
                            new_news_found = True
                            await asyncio.sleep(2)
                        except Exception as e:
                            print(f"  Ошибка отправки в Telegram: {e}")
                    else:
                        print(f"  Не удалось извлечь текст, пропускаем: {entry.link}")
        except Exception as e:
            print(f"Ошибка при чтении {feed_url}: {e}")

    if new_news_found:
        save_sent_news(sent_news)
        print("✅ Новые новости отправлены.")
    else:
        print("Новых новостей нет.")


async def main():
    print("🤖 Запуск бота-агрегатора новостей (с реф-ссылками).")
    await check_news()


if __name__ == "__main__":
    asyncio.run(main())