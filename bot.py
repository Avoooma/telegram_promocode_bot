import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import asyncio

# --- BOT_TOKEN читаємо з Environment Variable Railway ---
BOT_TOKEN = os.getenv("BOT_TOKEN").strip()  # обов'язково .strip(), щоб прибрати пробіли

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Кнопки ---
builder = ReplyKeyboardBuilder()
builder.row(KeyboardButton(text="/balance"), KeyboardButton(text="/promocode"))
builder.row(KeyboardButton(text="/top"), KeyboardButton(text="/trade"))
builder.row(KeyboardButton(text="/request"), KeyboardButton(text="/help"))
keyboard = builder.as_markup(resize_keyboard=True)

# --- Команди ---
@dp.message(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привіт, {message.from_user.first_name}! 👋\nЯ бот для промокодів та монет.",
        reply_markup=keyboard
    )

@dp.message(commands=["help"])
async def cmd_help(message: types.Message):
    help_text = (
        "/balance - показати баланс монет\n"
        "/promocode - активувати промокод\n"
        "/top - переглянути топ користувачів\n"
        "/trade - прив'язати свою Steam трейд-ссилку\n"
        "/request - створити заявку на обмін монет на скіни\n"
        "/help - показати це повідомлення"
    )
    await message.answer(help_text, reply_markup=keyboard)

# --- Старт бота ---
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
