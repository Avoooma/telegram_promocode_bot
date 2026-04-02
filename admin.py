import os
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import admin_menu, main_menu, cancel_kb, request_actions

ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

class AdminPromoState(StatesGroup):
    waiting_code = State()
    waiting_reward = State()
    waiting_uses = State()

# --- Користувачі ---
@router.message(F.text == "👤 Користувач")
async def list_users_admin(message: Message):
    if not is_admin(message.from_user.id): return
    users = db.get_top_users(50) # Беремо перші 50
    if not users:
        await message.answer("📭 Список користувачів порожній.")
        return
    
    text = "👤 <b>Список користувачів:</b>\n\n"
    for u in users:
        text += f"ID: <code>{u['telegram_id']}</code> | @{u['username']} | 💰 {u['coins']}\n"
    
    text += "\n<i>Щоб змінити баланс, просто введи ID користувача зі списку:</i>"
    await message.answer(text, parse_mode="HTML")

# --- Промокоди ---
@router.message(F.text == "📋 Всі промокоди")
async def list_promos(message: Message):
    if not is_admin(message.from_user.id): return
    promos = db.list_all_promocodes() # Додай цю функцію в database.py (нижче)
    if not promos:
        await message.answer("📭 Промокодів ще не створено.")
        return
    
    text = "📋 <b>Активні промокоди:</b>\n"
    for p in promos:
        text += f"🎟 <code>{p['code']}</code> | 💰 {p['reward']} | 🔢 Залишилось: {p['uses_left']}\n"
    await message.answer(text, parse_mode="HTML")

# --- Заявки ---
@router.message(F.text == "📥 Заявки")
async def show_requests(message: Message):
    if not is_admin(message.from_user.id): return
    reqs = db.get_pending_requests()
    if not reqs:
        await message.answer("✅ Нових заявок немає. Все чисто!")
        return
    # ... далі твій код виводу заявок ...
