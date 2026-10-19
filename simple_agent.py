# simple_agent.py — AI-агент с поиском и заметками
import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import tool
from duckduckgo_search import DDGS  # Для поиска в интернете

load_dotenv()

# ── 1. Создаём LLM через OpenRouter ──
llm = ChatOpenAI(
    model="openrouter/free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0,
)

# ── 2. Инструменты ──
@tool
def calculator(expression: str) -> str:
    """Считает математическое выражение, например '25 * 4'."""
    try:
        result = eval(expression)
        return f"Результат: {result}"
    except Exception as e:
        return f"Ошибка: {e}"

@tool
def get_current_time() -> str:
    """Возвращает текущее время и дату."""
    now = datetime.now()
    return now.strftime("%H:%M:%S, %d.%m.%Y")

@tool
def web_search(query: str) -> str:
    """Ищет информацию в интернете через DuckDuckGo. Возвращает топ-3 результата с краткими описаниями."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return "Ничего не найдено."
            output = []
            for r in results:
                output.append(f"Заголовок: {r['title']}\nСсылка: {r['href']}\nОписание: {r['body']}")
            return "\n\n".join(output)
    except Exception as e:
        return f"Ошибка поиска: {e}"

@tool
def save_note(note: str) -> str:
    """Сохраняет заметку в файл notes.txt. Вход: текст заметки."""
    try:
        with open("notes.txt", "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {note}\n")
        return "Заметка сохранена в notes.txt"
    except Exception as e:
        return f"Ошибка сохранения: {e}"

# Список всех инструментов
tools = [calculator, get_current_time, web_search, save_note]

# ── 3. Создаём агента ──
agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=(
        "Ты — умный ассистент. Ты можешь использовать инструменты для ответа на вопросы. "
        "Если вопрос требует математики — используй calculator. "
        "Если нужны свежие данные — используй web_search. "
        "Если нужно сохранить важную информацию — используй save_note. "
        "Для простых вопросов инструменты не нужны."
    )
)

# ── 4. Запуск ──
if __name__ == "__main__":
    print("🤖 Агент готов. Задай вопрос (например: 'Сколько будет 25 умножить на 4?', 'Какая погода в Минске?', 'Сохрани заметку: купить хлеб')")
    while True:
        query = input("\nТы: ")
        if query.lower() in ("выход", "exit", "quit"):
            break
        
        response = agent.invoke({"messages": [("user", query)]})
        
        # Красивый вывод шагов
        print("\n--- Процесс размышления ---")
        for msg in response["messages"]:
            if msg.type == "human":
                continue
            elif msg.type == "ai" and msg.tool_calls:
                tool_name = msg.tool_calls[0]['name']
                tool_args = msg.tool_calls[0]['args']
                print(f"🧠 Агент думает: Нужно использовать '{tool_name}' с аргументами {tool_args}")
            elif msg.type == "tool":
                print(f"🛠 Инструмент ответил: {msg.content}")
            elif msg.type == "ai" and msg.content:
                print(f"🤖 Агент: {msg.content}")
        print("---------------------------")