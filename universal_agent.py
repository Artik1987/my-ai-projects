# universal_agent.py — универсальный агент с памятью, PDF и инструментами
import os
import io
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from ddgs import DDGS
from pypdf import PdfReader
import chromadb
from chromadb.utils import embedding_functions

load_dotenv()

# ── 1. Настройка ChromaDB для PDF ──
chroma_client = chromadb.PersistentClient(path="./chroma_agent_db")
ru_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)
collection = chroma_client.get_or_create_collection(
    name="agent_knowledge",
    embedding_function=ru_ef
)

# ── 2. LLM ──
llm = ChatOpenAI(
    model="openrouter/free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0,
)

# ── 3. Инструменты ──
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
def add_pdf_to_knowledge(pdf_path: str) -> str:
    """Читает PDF-файл и добавляет его содержимое в базу знаний агента. 
    Вход: путь к PDF-файлу на компьютере."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        if not text.strip():
            return "В PDF нет текста."
        
        # Разбиваем на чанки
        chunks = [text[i:i+500] for i in range(0, len(text), 450)]
        import uuid
        ids = [str(uuid.uuid4()) for _ in chunks]
        collection.add(documents=chunks, ids=ids)
        
        count = len(chunks)
        if count % 10 == 1 and count % 100 != 11:
            word = "фрагмент"
        elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
            word = "фрагмента"
        else:
            word = "фрагментов"
            
        return f"Добавлено {count} {word} из PDF в базу знаний."
    except Exception as e:
        return f"Ошибка: {e}"

@tool
def ask_from_pdf(question: str) -> str:
    """Отвечает на вопрос, используя информацию из загруженных PDF-документов."""
    try:
        results = collection.query(query_texts=[question], n_results=3)
        if not results["documents"] or not results["documents"][0]:
            return "В базе знаний нет информации по этому вопросу."
        context = "\n\n".join(results["documents"][0])
        return f"Найдено в документах:\n{context}"
    except Exception as e:
        return f"Ошибка: {e}"

tools = [calculator, get_current_time, web_search, add_pdf_to_knowledge, ask_from_pdf]

# ── 4. Агент ──
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=(
        "Ты — универсальный AI-помощник. Ты можешь: "
        "1. Считать (calculator). "
        "2. Узнавать время (get_current_time). "
        "3. Искать в интернете (web_search). "
        "4. Загружать PDF-файлы в базу знаний (add_pdf_to_knowledge). "
        "5. Отвечать на вопросы по загруженным PDF (ask_from_pdf). "
        "Если пользователь просит загрузить PDF, уточни путь к файлу."
    )
)

# ── 5. Запуск с памятью ──
if __name__ == "__main__":
    print("🤖 Универсальный агент готов. Пиши задачи (например: 'Загрузи PDF: C:\\documents\\file.pdf' или 'Сколько будет 2+2?')")
    print("   Для выхода напиши 'выход'.\n")
    
    # История диалога (память)
    chat_history = []
    
    while True:
        query = input("Ты: ")
        if query.lower() in ("выход", "exit", "quit"):
            print("Пока! 👋")
            break
        
        # Добавляем вопрос в историю
        chat_history.append(HumanMessage(content=query))
        
        # Отправляем агенту всю историю (он видит контекст)
        response = agent.invoke({"messages": chat_history})
        
        # Достаём финальный ответ
        final_answer = response["messages"][-1].content
        
        # Добавляем ответ агента в историю
        chat_history.append(AIMessage(content=final_answer))
        
        # Выводим процесс (кратко)
        print("\n--- Процесс ---")
        for msg in response["messages"]:
            if msg.type == "ai" and msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"🧠 Использую: {tc['name']} ({tc['args']})")
            elif msg.type == "tool":
                print(f"🛠 Результат: {msg.content[:150]}...") # обрезаем для краткости
        print(f"\n🤖 Агент: {final_answer}\n")
        print("----------------\n")