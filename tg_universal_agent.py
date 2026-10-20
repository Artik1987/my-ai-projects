# tg_universal_agent.py — универсальный AI-агент в Telegram
import asyncio
import io
import logging
import os
import uuid
from contextvars import ContextVar
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from ddgs import DDGS
from pypdf import PdfReader
import chromadb
from chromadb.utils import embedding_functions

load_dotenv()
logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()

llm = ChatOpenAI(
    model="openrouter/free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0,
)

chroma_client = chromadb.PersistentClient(path="./chroma_tg_agent")
ru_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)
collection = chroma_client.get_or_create_collection(
    name="tg_agent_knowledge",
    embedding_function=ru_ef
)

current_user_id: ContextVar[int] = ContextVar("current_user_id", default=0)


@tool
def calculator(expression: str) -> str:
    """Считает математическое выражение, например '25 * 4'."""
    try:
        return f"Результат: {eval(expression)}"
    except Exception as e:
        return f"Ошибка: {e}"


@tool
def get_current_time() -> str:
    """Возвращает текущее время и дату."""
    return datetime.now().strftime("%H:%M:%S, %d.%m.%Y")


@tool
def web_search(query: str) -> str:
    """Ищет информацию в интернете через DuckDuckGo."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return "Ничего не найдено."
            return "\n\n".join([f"{r['title']}\n{r['body']}" for r in results])
    except Exception as e:
        return f"Ошибка поиска: {e}"


@tool
def search_documents(question: str) -> str:
    """Ищет ответ на вопрос в загруженных пользователем PDF-документах."""
    user_id = current_user_id.get()
    try:
        results = collection.query(
            query_texts=[question],
            n_results=3,
            where={"user_id": str(user_id)}
        )
        if not results["documents"] or not results["documents"][0]:
            return "В ваших документах нет информации по этому вопросу."
        return "\n\n---\n\n".join(results["documents"][0])
    except Exception as e:
        return f"Ошибка поиска в документах: {e}"


tools = [calculator, get_current_time, web_search, search_documents]

SYSTEM_PROMPT = (
    "Ты — умный AI-ассистент в Telegram. "
    "У тебя есть инструменты: calculator, get_current_time, web_search, search_documents.\n\n"
    "КРИТИЧЕСКИ ВАЖНО:\n"
    "1. Если вопрос по документу (PDF, вклад, договор, файл) — ОБЯЗАН вызвать search_documents.\n"
    "2. Если пользователь говорит 'из документа', 'в документе', 'по вкладу' — вызывай search_documents.\n"
    "3. Если search_documents вернул 'нет информации' — только тогда скажи, что в документах этого нет.\n"
    "4. Отвечай по-русски, кратко."
)

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
)

user_histories = {}


def get_history(user_id: int) -> list:
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]


def split_into_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_history(message.from_user.id)
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        f"Я универсальный AI-агент. Умею:\n"
        f"• 🧮 Считать\n"
        f"• 🌐 Искать в интернете\n"
        f"• 📄 Отвечать по PDF-документам\n"
        f"• 🧠 Помнить контекст разговора\n\n"
        f"📎 Отправь мне PDF — и задавай вопросы по нему.\n\n"
        f"Команды:\n"
        f"/start — это сообщение\n"
        f"/clear — очистить память\n"
        f"/stats — сколько фрагментов документов у тебя в базе"
    )


@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    user_histories[message.from_user.id] = []
    await message.answer("🧹 Память очищена. Начинаем с чистого листа.")


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = str(message.from_user.id)
    try:
        results = collection.get(where={"user_id": user_id})
        count = len(results["ids"]) if results["ids"] else 0
        await message.answer(f"📊 У вас загружено фрагментов документов: {count}")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}")


@dp.message(F.document)
async def handle_document(message: types.Message):
    document = message.document

    if not document.file_name.lower().endswith('.pdf'):
        await message.answer("⚠️ Пожалуйста, отправьте файл в формате PDF.")
        return

    await message.answer("⏳ Читаю PDF и добавляю в базу знаний...")

    try:
        file = await bot.get_file(document.file_id)
        file_bytes = await bot.download_file(file.file_path)

        reader = PdfReader(io.BytesIO(file_bytes.read()))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        if not text.strip():
            await message.answer("⚠️ В этом PDF нет текста (возможно, это картинки).")
            return

        chunks = split_into_chunks(text)
        ids = [str(uuid.uuid4()) for _ in chunks]

        collection.add(
            documents=chunks,
            ids=ids,
            metadatas=[
                {"user_id": str(message.from_user.id), "source": document.file_name}
                for _ in chunks
            ]
        )

        count = len(chunks)
        if count % 10 == 1 and count % 100 != 11:
            word = "фрагмент"
        elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
            word = "фрагмента"
        else:
            word = "фрагментов"

        await message.answer(
            f"✅ Готово! Добавлено {count} {word} из файла «{document.file_name}».\n"
            f"Теперь можете задавать вопросы по этому документу."
        )

    except Exception as e:
        logging.error(f"Ошибка при чтении PDF: {e}")
        await message.answer(f"⚠️ Ошибка при чтении файла: {e}")


@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    history = get_history(user_id)
    current_user_id.set(user_id)

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    history.append(HumanMessage(content=message.text))

    # Принудительный поиск в документах по ключевым словам
    keywords = ["документ", "pdf", "вклад", "договор", "файл", "из документа", "по вкладу", "по договору"]
    user_docs = collection.get(where={"user_id": str(user_id)})
    user_has_docs = len(user_docs["ids"]) > 0 if user_docs["ids"] else False

    if user_has_docs and any(kw in message.text.lower() for kw in keywords):
        try:
            doc_context = search_documents.invoke({"question": message.text})
            if doc_context and "нет информации" not in doc_context:
                history.insert(-1, SystemMessage(
                    content=f"Информация из документов пользователя:\n{doc_context}\n\n"
                            f"Используй эту информацию для ответа на вопрос."
                ))
        except Exception as e:
            logging.warning(f"Ошибка поиска в документах: {e}")

    try:
        response = agent.invoke({"messages": history})
        ai_answer = response["messages"][-1].content

        if not ai_answer:
            history.pop()
            await message.answer("🤔 Не смог ответить. Попробуй переформулировать.")
            return

        history.append(AIMessage(content=ai_answer))

        if len(ai_answer) > 4000:
            ai_answer = ai_answer[:4000] + "\n\n... (ответ обрезан)"

        await message.answer(ai_answer)

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        history.pop()
        await message.answer(f"⚠️ Ошибка: {e}")


async def main():
    print("🤖 Универсальный AI-агент запущен в Telegram.")
    print(f"📚 Всего фрагментов в базе: {collection.count()}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())