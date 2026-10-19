# tg_rag_bot.py — RAG-бот по документам
import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()
logging.basicConfig(level=logging.INFO)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()

# ═══ 1. Загрузка и разбивка документа ═══
def load_document(path="knowledge.txt") -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def split_into_chunks(text: str, chunk_size: int = 400) -> list:
    """Разбивает текст по абзацам, группирует в куски ~400 символов."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) < chunk_size:
            current += p + "\n\n"
        else:
            if current:
                chunks.append(current.strip())
            current = p + "\n\n"
    if current:
        chunks.append(current.strip())
    return chunks


# ═══ 2. Строим индекс (один раз при запуске) ═══
document = load_document()
chunks = split_into_chunks(document)
vectorizer = TfidfVectorizer()
tfidf_matrix = vectorizer.fit_transform(chunks)
print(f"📚 Загружено чанков: {len(chunks)}")


def retrieve(query: str, top_k: int = 3) -> list:
    """Находит top_k самых релевантных чанков для вопроса."""
    query_vec = vectorizer.transform([query])
    similarities = cosine_similarity(query_vec, tfidf_matrix)[0]
    top_indices = similarities.argsort()[-top_k:][::-1]
    # Отбрасываем нулевые совпадения
    return [chunks[i] for i in top_indices if similarities[i] > 0]


# ═══ 3. Генерация ответа с RAG ═══
def answer_with_rag(question: str) -> str:
    relevant = retrieve(question)

    if not relevant:
        context = "В базе знаний нет информации по этому вопросу."
    else:
        context = "\n\n---\n\n".join(relevant)

    prompt = f"""Ты — ассистент интернет-магазина "Техномир".
Отвечай на вопрос ТОЛЬКО на основе контекста ниже.
Если ответа в контексте нет — честно скажи "В базе знаний нет этой информации".
Отвечай кратко, по-русски, дружелюбно.

КОНТЕКСТ:
{context}

ВОПРОС: {question}

ОТВЕТ:"""

    models = [
        "qwen/qwen-2.5-72b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "mistralai/mistral-small-3.2-24b-instruct:free",
        "openrouter/free",
    ]

    for model_name in models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response.choices[0].message.content
            if not answer:
                continue
            if "User Safety" in answer or "Response Safety" in answer:
                continue
            return answer
        except Exception as e:
            logging.warning(f"Модель {model_name} не сработала: {e}")
            continue

    return "🤔 Не смог получить ответ. Попробуй переформулировать вопрос."


# ═══ 4. Хендлеры Telegram ═══
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        f"Я RAG-бот интернет-магазина «Техномир».\n"
        f"Задай вопрос — найду ответ в базе знаний.\n\n"
        f"Примеры вопросов:\n"
        f"• Сколько стоит доставка?\n"
        f"• Какая гарантия на iPhone?\n"
        f"• Можно ли вернуть товар?"
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Я отвечаю на вопросы по базе знаний магазина:\n"
        "• Доставка\n"
        "• Оплата\n"
        "• Гарантия\n"
        "• Возврат\n"
        "• Скидки\n"
        "• Контакты\n\n"
        "Просто напиши вопрос."
    )


@dp.message()
async def handle_message(message: types.Message):
    if not message.text:
        await message.answer("Я понимаю только текст 🤔")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        answer = answer_with_rag(message.text)
        if not answer:
            await message.answer("🤔 Не смог сформировать ответ. Переформулируй вопрос.")
            return
        if len(answer) > 4000:
            answer = answer[:4000] + "\n\n... (ответ обрезан)"
        await message.answer(answer)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"⚠️ Ошибка: {e}")


async def main():
    print("🤖 RAG-бот запущен. Напиши в Telegram: @artem_ai_helper_bot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())