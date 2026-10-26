import asyncio
import feedparser
import os
import time
from dotenv import load_dotenv
from aiogram import Bot

# Загружаем переменные окружения
load_dotenv()

# Инициализируем бота
bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
CHANNEL_ID = os.getenv("NEWS_CHANNEL_ID")

# Список RSS-лент для мониторинга
RSS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://www.theblock.co/rss.xml",
]

# Файл для хранения уже отправленных новостей, чтобы избежать дублей
SENT_NEWS_FILE = "sent_news.txt"

def load_sent_news():
    if os.path.exists(SENT_NEWS_FILE):
        with open(SENT_NEWS_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()

def save_sent_news(news_set):
    with open(SENT_NEWS_FILE, "w", encoding="utf-8") as f:
        for link in news_set:
            f.write(f"{link}\n")

async def check_news():
    """Проверяет RSS-ленты и отправляет новые новости в канал."""
    sent_news = load_sent_news()
    new_news_found = False

    print(f"[{time.strftime('%H:%M')}] Проверяем новости...")

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]: # Проверяем 5 последних новостей с каждого источника
                if entry.link not in sent_news:
                    # Форматируем сообщение
                    message_text = f"📰 **{entry.title}**\n\n[Читать далее]({entry.link})"
                    
                    # Отправляем в канал
                    await bot.send_message(chat_id=CHANNEL_ID, text=message_text, parse_mode="Markdown", disable_web_page_preview=True)
                    
                    sent_news.add(entry.link)
                    new_news_found = True
                    await asyncio.sleep(2) # Пауза между сообщениями
        except Exception as e:
            print(f"Ошибка при чтении {feed_url}: {e}")

    if new_news_found:
        save_sent_news(sent_news)
        print("✅ Новые новости отправлены.")
    else:
        print("Новых новостей нет.")

async def main():
    print("🤖 Запуск бота-агрегатора новостей (GitHub Actions режим).")
    await check_news()  # Проверяем один раз и выходим

if __name__ == "__main__":
    asyncio.run(main())