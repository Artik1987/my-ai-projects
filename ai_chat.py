# ai_chat.py — версия 2: с памятью
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from datetime import datetime

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# ── 1. Системный промпт — «характер» бота ──
SYSTEM_PROMPT = (
    "Ты — дружелюбный AI-ассистент. "
    "Отвечай ТОЛЬКО на русском языке, кратко и по делу. "
    "Если тебя спрашивают про крипту, акции или инвестиции — "
    "вежливо откажись, потому что ты не можешь предсказывать будущее."
)

# ── 2. История диалога. Начинается с системного промпта ──
messages = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

# ── 3. Имя файла для сохранения истории ──
HISTORY_FILE = "chat_history.json"


def save_history():
    """Сохраняет messages в файл, чтобы можно было прочитать потом."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


print("🤖 Привет! Я AI-ассистент с памятью.")
print("   Команды: /clear — очистить память, 'выход' — выйти.\n")

while True:
    user_question = input("Твой вопрос: ").strip()

    # Пустой ввод — пропускаем
    if not user_question:
        continue

    # Выход
    if user_question.lower() == "выход":
        save_history()
        print("Пока! История сохранена в chat_history.json 👋")
        break

    # Сброс памяти
    if user_question == "/clear":
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        print("🧹 Память очищена. Начинаем с чистого листа.\n")
        continue

    # ── Добавляем вопрос в историю ──
    messages.append({"role": "user", "content": user_question})

    try:
        # ── Отправляем ВСЮ историю в ИИ ──
        response = client.chat.completions.create(
            model="openrouter/free",
            messages=messages,          # ← теперь тут вся история
        )
        ai_answer = response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Ошибка API: {e}\n")
        # Убираем неудачный вопрос из истории, чтобы не засорять
        messages.pop()
        continue

    # ── Добавляем ответ ИИ в историю ──
    messages.append({"role": "assistant", "content": ai_answer})

    print(f"\n🧠 AI: {ai_answer}\n")