from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from supabase import create_client
import os

# --- Вставляємо токени Supabase і Telegram прямо сюди ---
BOT_TOKEN = "твій_токен_від_BotFather"
SUPABASE_URL = "твій_supabase_url"
SUPABASE_KEY = "твій_anon_key"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Кнопки ---
main_buttons = ReplyKeyboardMarkup(resize_keyboard=True)
main_buttons.add(KeyboardButton("/balance"), KeyboardButton("/promocode"))
main_buttons.add(KeyboardButton("/top"), KeyboardButton("/trade"))
main_buttons.add(KeyboardButton("/request"), KeyboardButton("/help"))

# --- Команди ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    # Додаємо користувача в БД, якщо нового
    user = supabase.table("users").select("*").eq("telegram_id", message.from_user.id).execute()
    if not user.data:
        supabase.table("users").insert({
            "telegram_id": message.from_user.id,
            "username": message.from_user.username,
            "coins": 0,
            "trade_link": ""
        }).execute()
    await message.answer(f"Привіт, {message.from_user.first_name}! 👋\nЯ бот для промокодів та монет.", reply_markup=main_buttons)

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    help_text = (
        "/balance - показати баланс монет\n"
        "/promocode - активувати промокод\n"
        "/top - переглянути топ користувачів\n"
        "/trade - прив'язати свою Steam трейд-ссилку\n"
        "/request - створити заявку на обмін монет на скіни\n"
        "/help - показати це повідомлення"
    )
    await message.answer(help_text, reply_markup=main_buttons)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
