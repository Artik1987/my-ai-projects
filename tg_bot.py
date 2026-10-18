# tg_bot.py — версия 2: AI-бот с памятью
import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from openai import OpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO)

# ── Клиент для OpenRouter ──
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

# ── Системный промпт — «характер» бота ──
SYSTEM_PROMPT = (
    "Ты — дружелюбный AI-ассистент в Telegram. "
    "Отвечай ТОЛЬКО на русском языке, кратко и по делу. "
    "Если спрашивают про крипту, акции или инвестиции — "
    "вежливо откажись: ты не можешь предсказывать будущее."
)

# ── Память: у каждого пользователя свой список сообщений ──
user_histories = {}

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()


def get_history(user_id: int) -> list:
    """Возвращает историю пользователя. Если её нет — создаёт с системным промптом."""
    if user_id not in user_histories:
        user_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return user_histories[user_id]


# ── /start ──
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_history(message.from_user.id)
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        f"Я AI-ассистент. Спроси что угодно.\n\n"
        f"Команды:\n"
        f"/clear — очистить память\n"
        f"/help — помощь"
    )


# ── /help ──
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Я умею:\n"
        "• Отвечать на вопросы\n"
        "• Помнить наш разговор\n"
        "• Считать, объяснять, переводить\n\n"
        "Команды:\n"
        "/clear — сбросить память\n"
        "/start — поздороваться заново"
    )


# ── /clear ──
@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    user_histories[message.from_user.id] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    await message.answer("🧹 Память очищена. Начинаем с чистого листа.")


# ── Основной обработчик ──
@dp.message()
async def handle_message(message: types.Message):
    if not message.text:
        await message.answer("Я понимаю только текст 🤔")
        return

    user_id = message.from_user.id
    history = get_history(user_id)

    history.append({"role": "user", "content": message.text})

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        response = client.chat.completions.create(
            model="nvidia/nemotron-3-super-120b-a12b:free",
            messages=history,
        )
        ai_answer = response.choices[0].message.content

        if not ai_answer:
            history.pop()
            await message.answer("🤔 ИИ не смог ответить. Попробуй переформулировать.")
            return        # Если модель вернула фильтр безопасности — просим переформулировать
        if "User Safety" in ai_answer or "Response Safety" in ai_answer:
            history.pop()
            await message.answer("🤔 Не могу ответить на это. Попробуй переформулировать вопрос.")
            return

        history.append({"role": "assistant", "content": ai_answer})

        if len(ai_answer) > 4000:
            ai_answer = ai_answer[:4000] + "\n\n... (ответ обрезан)"

        await message.answer(ai_answer)

    except Exception as e:
        history.pop()
        logging.error(f"Ошибка API: {e}")
        await message.answer(f"⚠️ Ошибка: {e}")


async def main():
    print("🤖 AI-бот запущен. Напиши ему в Telegram: @artem_ai_helper_bot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())