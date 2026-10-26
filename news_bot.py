import asyncio
import feedparser
import os
import time
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
    """Скачивает страницу и извлекает основной текст статьи."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            # Извлекаем текст, убирая навигацию и рекламу
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            return text if text else ""
    except Exception as e:
        print(f"Ошибка извлечения текста из {url}: {e}")
    return ""

def translate_text(text: str) -> str:
    """Переводит текст на русский язык."""
    if not text:
        return ""
    try:
        # GoogleTranslator имеет ограничение на длину, разбиваем на части по 4000 символов
        max_len = 4000
        chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)]
        translated_chunks = [GoogleTranslator(source='auto', target='ru').translate(chunk) for chunk in chunks]
        return " ".join(translated_chunks)
    except Exception as e:
        print(f"Ошибка перевода: {e}")
        return text # Возвращаем оригинал, если перевод не удался

async def check_news():
    sent_news = load_sent_news()
    new_news_found = False
    print(f"[{time.strftime('%H:%M')}] Проверяем новости...")

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]: # Берем 3 последние новости с каждого источника
                if entry.link not in sent_news:
                    print(f"  Обработка: {entry.title}")
                    # 1. Извлекаем полный текст
                    full_text = get_full_article_text(entry.link)
                    # 2. Переводим заголовок и текст
                    translated_title = translate_text(entry.title)
                    translated_text = translate_text(full_text)

                    if translated_text:
                        # Ограничиваем длину сообщения (лимит Telegram — 4096 символов)
                        if len(translated_text) > 3500:
                            translated_text = translated_text[:3500] + "..."
                        
                        message_text = f"📰 **{translated_title}**\n\n{translated_text}\n\n[Источник]({entry.link})"
                        
                        try:
                            await bot.send_message(chat_id=CHANNEL_ID, text=message_text, parse_mode="Markdown", disable_web_page_preview=True)
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
        print("✅ Новые переведенные новости отправлены.")
    else:
        print("Новых новостей нет.")

async def main():
    print("🤖 Запуск бота-агрегатора новостей (с переводом).")
    await check_news()

if __name__ == "__main__":
    asyncio.run(main())