# tg_rag_bot.py — версия 2.0: ChromaDB + PDF
import asyncio
import logging
import os
import io
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader

load_dotenv()
logging.basicConfig(level=logging.INFO)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()

# ═══ 1. Настройка ChromaDB (с сохранением на диск) ═══ # НОВОЕ
# PersistentClient сохраняет базу в папку "chroma_db", чтобы данные не пропадали при перезапуске
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Подключаем русскую модель
ru_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# Создаем или открываем коллекцию
collection = chroma_client.get_or_create_collection(
    name="knowledge_ru",
    embedding_function=ru_ef
)
print(f"📚 База знаний загружена. Документов в базе: {collection.count()}")


# ═══ 2. Функция разбивки текста на чанки ═══
def split_into_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """Разбивает текст на куски с перекрытием (чтобы не терять смысл на стыках)."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


# ═══ 3. Генерация ответа с RAG ═══
def answer_with_rag(question: str) -> str:
    # Ищем в базе 3 самых близких куска
    results = collection.query(
        query_texts=[question],
        n_results=3
    )

    # results["documents"] — это список списков (для каждого запроса свой список)
    relevant = results["documents"][0] if results["documents"] else []

    if not relevant:
        context = "В базе знаний нет информации по этому вопросу."
    else:
        context = "\n\n---\n\n".join(relevant)

    prompt = f"""Ты — ассистент. Отвечай на вопрос ТОЛЬКО на основе контекста ниже.
Если ответа в контексте нет — честно скажи "В базе знаний нет этой информации".
Отвечай кратко, по-русски, дружелюбно.

КОНТЕКСТ:
{context}

ВОПРОС: {question}

ОТВЕТ:"""

    models = [
        "qwen/qwen-2.5-72b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "openrouter/free",
    ]

    for model_name in models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response.choices[0].message.content
            if not answer or "User Safety" in answer:
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
        f"Я RAG-бот 2.0. Я умею отвечать на вопросы по вашим документам.\n\n"
        f"📎 **Как пользоваться:**\n"
        f"1. Отправьте мне PDF-файл или текстовый документ.\n"
        f"2. Задайте вопрос — я найду ответ в документе.\n\n"
        f"Команды:\n"
        f"/start — это сообщение\n"
        f"/stats — сколько документов в базе"
    )


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    count = collection.count()
    await message.answer(f"📊 В базе знаний сейчас {count} фрагментов текста.")


# НОВОЕ: Обработчик PDF-файлов
@dp.message(F.document)
async def handle_document(message: types.Message):
    document = message.document
    
    # Проверяем, что это PDF
    if not document.file_name.lower().endswith('.pdf'):
        await message.answer("⚠️ Пожалуйста, отправьте файл в формате PDF.")
        return

    await message.answer("⏳ Читаю PDF и добавляю в базу знаний. Подождите...")

    try:
        # Скачиваем файл из Telegram
        file = await bot.get_file(document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        
        # Читаем PDF
        reader = PdfReader(io.BytesIO(file_bytes.read()))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        if not text.strip():
            await message.answer("⚠️ В этом PDF нет текста (возможно, это картинки).")
            return

        # Разбиваем на чанки и добавляем в базу
        chunks = split_into_chunks(text)
        
        # Генерируем уникальные ID для каждого куска
        import uuid
        ids = [str(uuid.uuid4()) for _ in chunks]
        
        collection.add(
            documents=chunks,
            ids=ids
        )

        await message.answer(f"✅ Готово! Добавлено {len(chunks)} фрагментов из файла «{document.file_name}».\nТеперь можете задавать вопросы по этому документу.")

    except Exception as e:
        logging.error(f"Ошибка при чтении PDF: {e}")
        await message.answer(f"⚠️ Ошибка при чтении файла: {e}")


# Обработчик текстовых сообщений
@dp.message(F.text)
async def handle_message(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        answer = answer_with_rag(message.text)
        if len(answer) > 4000:
            answer = answer[:4000] + "\n\n... (ответ обрезан)"
        await message.answer(answer)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(f"⚠️ Ошибка: {e}")


async def main():
    print("🤖 RAG-бот 2.0 запущен. Напиши в Telegram: @artem_ai_helper_bot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())