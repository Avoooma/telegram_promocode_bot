import os
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# ====================
# Налаштування
# ====================
BOT_TOKEN = os.getenv("BOT_TOKEN").strip()
DATABASE_URL = os.getenv("DATABASE_URL").strip()  # Supabase Postgres URL
ADMIN_IDS = [123456789]  # Telegram ID адміна

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ====================
# Підключення до бази
# ====================
async def create_db_pool():
    return await asyncpg.create_pool(DATABASE_URL)

db_pool = asyncio.get_event_loop().run_until_complete(create_db_pool())

# ====================
# Кнопки користувача
# ====================
builder = ReplyKeyboardBuilder()
builder.row(KeyboardButton("/balance"), KeyboardButton("/promocode"))
builder.row(KeyboardButton("/top"), KeyboardButton("/trade"))
builder.row(KeyboardButton("/request"), KeyboardButton("/help"))
keyboard = builder.as_markup(resize_keyboard=True)

# ====================
# Допоміжні функції
# ====================
async def get_user(user_id, username):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", user_id)
        if not user:
            await conn.execute(
                "INSERT INTO users (telegram_id, username, coins) VALUES ($1, $2, 0)",
                user_id, username
            )
            user = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", user_id)
        return user

async def add_coins(user_id, amount, description=""):
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE users SET coins = coins + $1 WHERE telegram_id = $2", amount, user_id)
        await conn.execute(
            "INSERT INTO transactions (user_id, type, amount, description, date) VALUES ($1, $2, $3, $4, now())",
            user_id, "earn" if amount > 0 else "spend", amount, description
        )

# ====================
# Команди користувача
# ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await get_user(message.from_user.id, message.from_user.username)
    await message.answer(
        f"Привіт, {message.from_user.first_name}! 👋\nЯ бот для промокодів та монет.",
        reply_markup=keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "/balance - показати баланс монет\n"
        "/promocode - активувати промокод та отримати монети\n"
        "/top - переглянути топ користувачів за монетами\n"
        "/trade - прив'язати свою Steam трейд-ссилку\n"
        "/request - створити заявку на обмін монет на скіни\n"
        "/help - показати це повідомлення"
    )
    await message.answer(help_text, reply_markup=keyboard)

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    user = await get_user(message.from_user.id, message.from_user.username)
    await message.answer(f"Ваш баланс: {user['coins']} монет", reply_markup=keyboard)

# ====================
# Активувати промокод
# ====================
@dp.message(Command("promocode"))
async def cmd_promocode(message: types.Message):
    await message.answer("Введіть ваш промокод:")

    @dp.message()  # Наступне повідомлення користувача
    async def get_promocode(msg: types.Message):
        code = msg.text.strip()
        async with db_pool.acquire() as conn:
            promocode = await conn.fetchrow("SELECT * FROM promocodes WHERE code = $1 AND uses_left > 0", code)
            if not promocode:
                await msg.answer("Промокод недійсний або використаний.")
                return
            # Додаємо монети
            await add_coins(msg.from_user.id, promocode['reward'], f"Промокод {code}")
            # Зменшуємо uses_left
            await conn.execute("UPDATE promocodes SET uses_left = uses_left - 1 WHERE id = $1", promocode['id'])
            await msg.answer(f"Ви отримали {promocode['reward']} монет!", reply_markup=keyboard)

# ====================
# Топ користувачів
# ====================
@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    async with db_pool.acquire() as conn:
        top_users = await conn.fetch("SELECT username, coins FROM users ORDER BY coins DESC LIMIT 10")
        text = "Топ користувачів:\n"
        for i, u in enumerate(top_users, start=1):
            text += f"{i}. {u['username']} — {u['coins']} монет\n"
        await message.answer(text, reply_markup=keyboard)

# ====================
# Прив'язка трейд-ссилки
# ====================
@dp.message(Command("trade"))
async def cmd_trade(message: types.Message):
    await message.answer("Введіть ваш Steam trade URL:")

    @dp.message()
    async def get_trade_link(msg: types.Message):
        trade_link = msg.text.strip()
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE users SET trade_link=$1 WHERE telegram_id=$2", trade_link, msg.from_user.id)
        await msg.answer("Ваш Steam trade link збережено.", reply_markup=keyboard)

# ====================
# Заявки на обмін монет
# ====================
@dp.message(Command("request"))
async def cmd_request(message: types.Message):
    await message.answer("Введіть назву скіна та вартість у монетах через пробіл (наприклад: AK-47 500):")

    @dp.message()
    async def get_request(msg: types.Message):
        try:
            name, cost = msg.text.strip().split()
            cost = int(cost)
        except:
            await msg.answer("Помилка формату. Спробуйте ще раз.")
            return
        user = await get_user(msg.from_user.id, msg.from_user.username)
        if user['coins'] < cost:
            await msg.answer("У вас недостатньо монет.")
            return
        async with db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO requests (user_id, item_name, cost, status) VALUES ($1, $2, $3, 'pending')",
                msg.from_user.id, name, cost
            )
        await msg.answer(f"Заявка на обмін {cost} монет на {name} створена та очікує підтвердження.", reply_markup=keyboard)

# ====================
# Старт бота
# ====================
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
