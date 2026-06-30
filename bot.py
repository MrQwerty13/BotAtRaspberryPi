import asyncio
import json
import os

import aiohttp
from aiohttp_socks import ProxyConnector

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession

# ================= CONFIG =================

TOKEN = "8597322482:AAFFq5D2MSmIlo_gBBrVaDVXK8ddpezYmXU"
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1"

DATA_DIR = "users"
MAX_HISTORY = 20

# SOCKS5 (Telegram)
connector = ProxyConnector.from_url("socks5://127.0.0.1:1080")
session = AiohttpSession(connector=connector)

bot = Bot(TOKEN, session=session)
dp = Dispatcher()

os.makedirs(DATA_DIR, exist_ok=True)

# ================= STORAGE =================

def path(user_id: int):
    return f"{DATA_DIR}/{user_id}.json"


def load(user_id: int):
    p = path(user_id)

    if not os.path.exists(p):
        return {"messages": [], "notes": []}

    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"messages": [], "notes": []}


def save(user_id: int, data: dict):
    with open(path(user_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ================= START =================

@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    load(user_id)  # просто инициализация файла
    save(user_id, load(user_id))

    await message.answer("Бот запущен. Память активирована.")


# ================= HELP =================

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "/ai <text>\n"
        "/note <text>\n"
        "/notes\n"
        "/d_note <id>\n"
    )


# ================= NOTES =================

@dp.message(Command("note"))
async def note(message: Message):
    user_id = message.from_user.id
    text = message.text.removeprefix("/note").strip()

    if not text:
        return await message.answer("Введите текст заметки")

    data = load(user_id)
    data["notes"].append(text)
    save(user_id, data)

    await message.answer("Сохранено")


@dp.message(Command("notes"))
async def notes(message: Message):
    user_id = message.from_user.id
    data = load(user_id)

    if not data["notes"]:
        return await message.answer("Заметок нет")

    text = "\n".join(f"{i+1}. {n}" for i, n in enumerate(data["notes"]))
    await message.answer(text)


@dp.message(Command("d_note"))
async def delete_note(message: Message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2:
        return await message.answer("Используй: /d_note 1")

    try:
        idx = int(args[1]) - 1
    except ValueError:
        return await message.answer("Неверный индекс")

    data = load(user_id)

    if idx < 0 or idx >= len(data["notes"]):
        return await message.answer("Нет такой заметки")

    removed = data["notes"].pop(idx)
    save(user_id, data)

    await message.answer(f"Удалено: {removed}")


# ================= AI (OLLAMA) =================

@dp.message(Command("ai"))
async def ai(message: Message):
    user_id = message.from_user.id
    prompt = message.text.removeprefix("/ai").strip()

    if not prompt:
        return await message.answer("Используй: /ai вопрос")

    data = load(user_id)

    # ограничиваем память
    data["messages"] = data["messages"][-MAX_HISTORY:]

    data["messages"].append({
        "role": "user",
        "content": prompt
    })

    payload = {
        "model": MODEL,
        "messages": data["messages"],
        "stream": False
    }

    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(OLLAMA_URL, json=payload, timeout=60) as r:
                result = await r.json()

        answer = result.get("message", {}).get("content", "Нет ответа")

        data["messages"].append({
            "role": "assistant",
            "content": answer
        })

        save(user_id, data)

        await message.answer(answer)

    except Exception as e:
        await message.answer(f"Ollama error: {e}")


# ================= FALLBACK =================

@dp.message()
async def fallback(message: Message):
    if not message.text or message.text.startswith("/"):
        return

    await message.answer("Используй /ai для общения с ИИ")


# ================= RUN =================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())