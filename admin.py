import os
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import admin_menu, main_menu, cancel_kb, request_actions

# Отримуємо ID адмінів
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

class AdminPromoState(StatesGroup):
    waiting_code = State()
    waiting_reward = State()
    waiting_uses = State()

# --- Вхід в адмінку ---
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Немає доступу.")
        return
    await message.answer("👑 Ласкаво просимо до адмін-панелі!", reply_markup=admin_menu())

# --- Список користувачів ---
@router.message(F.text == "👤 Користувач")
async def list_users_admin(message: Message):
    if not is_admin(message.from_user.id): return
    users = db.get_top_users(50)
    if not users:
        await message.answer("📭 Список користувачів порожній.")
        return
    
    text = "👤 <b>Список користувачів:</b>\n\n"
    for u in users:
        text += f"ID: <code>{u['telegram_id']}</code> | @{u['username']} | 💰 {u['coins']}\n"
    
    text += "\n<i>Використовуй ID для зміни балансу через базу або майбутні команди.</i>"
    await message.answer(text, parse_mode="HTML")

# --- Всі промокоди ---
@router.message(F.text == "📋 Всі промокоди")
async def list_promos(message: Message):
    if not is_admin(message.from_user.id): return
    promos = db.list_all_promocodes()
    if not promos:
        await message.answer("📭 Промокодів ще немає.")
        return
    
    text = "📋 <b>Список промокодів:</b>\n\n"
    for p in promos:
        text += f"🎟 <code>{p['code']}</code> | 💰 {p['reward']} | 🔢 {p['uses_left']} шт.\n"
    await message.answer(text, parse_mode="HTML")

# --- Заявки ---
@router.message(F.text == "📥 Заявки")
async def show_requests(message: Message):
    if not is_admin(message.from_user.id): return
    reqs = db.get_pending_requests()
    if not reqs:
        await message.answer("✅ Нових заявок немає.")
        return

    for r in reqs:
        u = r.get('users', {})
        text = (
            f"📥 <b>Заявка #{r['id']}</b>\n"
            f"👤 @{u.get('username')} (<code>{u.get('telegram_id')}</code>)\n"
            f"🎮 Скін: {r['item_name']}\n"
            f"💰 Вартість: {r['cost']} монет\n"
            f"🔗 Trade: <code>{u.get('trade_link')}</code>"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=request_actions(r['id']))

@router.message(F.text == "🔙 Вийти з адмін-панелі")
async def exit_admin(message: Message):
    await message.answer("Повернулись до меню.", reply_markup=main_menu())
