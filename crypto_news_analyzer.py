import os
import time
import requests
import feedparser
from dotenv import load_dotenv

load_dotenv()

# ── 1. Настройки ──
# Токен CryptoPanic (добавь его в .env как CRYPTOPANIC_TOKEN)
CRYPTOPANIC_TOKEN = os.getenv("CRYPTOPANIC_TOKEN")

# Список RSS-лент для быстрого доступа к заголовкам
RSS_FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "The Block": "https://www.theblock.co/rss"
}

# Интересующие нас монеты (для фильтрации новостей)
COINS = ["BTC", "ETH", "SOL", "ADA", "AVAX", "XRP", "BNB", "DOT", "LINK", "HBAR"]

def get_cryptocurrency_cv_news():
    """Получает новости с бесплатного API cryptocurrency.cv."""
    url = "https://cryptocurrency.cv/api/news"
    params = {"limit": 20}  # Можно запросить до 20 новостей
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        news_items = []
        # Структура ответа может отличаться, проверяем наличие поля 'articles'
        for post in data.get("articles", []):
            title = post.get("title", "")
            # Фильтруем по нашим монетам в заголовке
            if any(coin in title.upper() for coin in COINS):
                news_items.append({
                    "source": "cryptocurrency.cv",
                    "title": title,
                    "url": post.get("url", ""),
                    "published": post.get("published_at", "N/A")
                })
        return news_items
    except Exception as e:
        print(f"Ошибка cryptocurrency.cv: {e}")
        return []

def get_rss_news():
    """Собирает заголовки из RSS-лент."""
    rss_news = []
    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]: # Берем 5 последних новостей с каждого источника
                title = entry.title
                # Простой фильтр: ищем упоминание монет в заголовке
                if any(coin in title.upper() for coin in COINS):
                    rss_news.append({
                        "source": source_name,
                        "title": title,
                        "url": entry.link,
                        "published": entry.get("published", "N/A")
                    })
        except Exception as e:
            print(f"Ошибка RSS {source_name}: {e}")
    return rss_news

if __name__ == "__main__":
    print("📰 Собираем новости...")
    cp_news = get_cryptocurrency_cv_news()
    rss_news = get_rss_news()

    print(f"\n--- CryptoPanic (с голосами) ---")
    for item in cp_news:
        print(f"[{item['published']}] {item['title']} | Голоса: {item['votes']}")

    print(f"\n--- RSS (заголовки) ---")
    for item in rss_news:
        print(f"[{item['source']}] {item['title']}")

    print("\n✅ Сбор новостей завершен.")