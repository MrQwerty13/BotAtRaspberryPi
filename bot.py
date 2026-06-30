from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import asyncio
import json
import os
import aiohttp

TOKEN = "8597322482:AAFFq5D2MSmIlo_gBBrVaDVXK8ddpezYmXU"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "tinyllama"

DATA_DIR = "users"

bot = Bot(TOKEN)
dp = Dispatcher()


# ---------- utils ----------

def get_user_file(user_id: int):
    return f"{DATA_DIR}/{user_id}.json"


def load_user(user_id: int):
    path = get_user_file(user_id)

    if not os.path.exists(path):
        return {"messages": [], "notes": []}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_user(user_id: int, data: dict):
    path = get_user_file(user_id)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ---------- start ----------

@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id

    data = load_user(user_id)
    save_user(user_id, data)

    await message.answer("Бот запущен. Контекст создан.")


# ---------- help ----------

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "/start\n"
        "/help\n"
        "/note <text>\n"
        "/notes\n"
        "/d_note <id>\n"
        "/ai <prompt>"
    )


# ---------- notes ----------

@dp.message(Command("note"))
async def note(message: Message):
    user_id = message.from_user.id
    text = message.text.removeprefix("/note").strip()

    if not text:
        return await message.answer("Введите заметку")

    data = load_user(user_id)
    data["notes"].append(text)
    save_user(user_id, data)

    await message.answer("Сохранено")


@dp.message(Command("notes"))
async def notes(message: Message):
    user_id = message.from_user.id
    data = load_user(user_id)

    notes = data.get("notes", [])

    if not notes:
        return await message.answer("Пусто")

    text = "\n".join(f"{i+1}. {n}" for i, n in enumerate(notes))
    await message.answer(text)


@dp.message(Command("d_note"))
async def delete_note(message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2:
        return await message.answer("Используй /d_note 1")

    try:
        idx = int(args[1]) - 1
    except ValueError:
        return await message.answer("Неверный номер")

    data = load_user(user_id)

    if idx < 0 or idx >= len(data["notes"]):
        return await message.answer("Нет такой заметки")

    removed = data["notes"].pop(idx)
    save_user(user_id, data)

    await message.answer(f"Удалено: {removed}")


# ---------- AI (OLLAMA + MEMORY) ----------

@dp.message(Command("ai"))
async def ai(message: Message):
    user_id = message.from_user.id
    prompt = message.text.removeprefix("/ai").strip()

    if not prompt:
        return await message.answer("Напиши: /ai вопрос")

    data = load_user(user_id)

    # добавляем сообщение пользователя
    data["messages"].append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL,
        "messages": data["messages"],
        "stream": False
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OLLAMA_URL, json=payload) as resp:
                result = await resp.json()

        answer = result["message"]["content"]

        # сохраняем ответ ассистента
        data["messages"].append({"role": "assistant", "content": answer})
        save_user(user_id, data)

        await message.answer(answer)

    except Exception as e:
        await message.answer(f"Ollama error: {e}")


# ---------- fallback ----------

@dp.message()
async def fallback(message: Message):
    if message.text.startswith("/"):
        return

    await message.answer("Используй /ai для общения с ИИ")


# ---------- run ----------

async def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())