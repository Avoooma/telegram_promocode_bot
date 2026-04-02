import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Импортируем файлы
import user
import admin

async def main():
    token = os.getenv("BOT_TOKEN")
    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())

    # Регестрация роутеров из файлов user.py та admin.py
    dp.include_router(admin.router)
    dp.include_router(user.router)

    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
