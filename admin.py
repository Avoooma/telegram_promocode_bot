import os
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import admin_menu, main_menu, cancel_kb

ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
router = Router()

class AdminPromoState(StatesGroup):
    waiting_code = State()
    waiting_reward = State()
    waiting_uses = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer("👑 Адмін-панель", reply_markup=admin_menu())

# --- СТВОРЕННЯ ПРОМОКОДУ ---
@router.message(F.text == "➕ Промокод")
async def promo_step_1(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminPromoState.waiting_code)
    await message.answer("🎟 Введіть текст промокоду (наприклад: GIFT2024):", reply_markup=cancel_kb())

@router.message(AdminPromoState.waiting_code)
async def promo_step_2(message: Message, state: FSMContext):
    await state.update_data(code=message.text.upper())
    await state.set_state(AdminPromoState.waiting_reward)
    await message.answer("💰 Скільки монет даватиме цей код?")

@router.message(AdminPromoState.waiting_reward)
async def promo_step_3(message: Message, state: FSMContext):
    await state.update_data(reward=int(message.text))
    await state.set_state(AdminPromoState.waiting_uses)
    await message.answer("🔢 Скільки людей можуть його активувати?")

@router.message(AdminPromoState.waiting_uses)
async def promo_step_final(message: Message, state: FSMContext):
    data = await state.get_data()
    success = db.create_promocode(data['code'], data['reward'], int(message.text))
    await state.clear()
    if success:
        await message.answer(f"✅ Промокод {data['code']} створено!", reply_markup=admin_menu())
    else:
        await message.answer("❌ Помилка при створенні.", reply_markup=admin_menu())

# --- ІНШІ КНОПКИ ---
@router.message(F.text == "📋 Всі промокоди")
async def list_promos(message: Message):
    if not is_admin(message.from_user.id): return
    promos = db.list_all_promocodes()
    text = "🎟 <b>Промокоди:</b>\n\n" + "\n".join([f"<code>{p['code']}</code> | {p['reward']}💰 | {p['uses_left']}шт" for p in promos]) if promos else "Пусто"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "👤 Користувач")
async def list_users(message: Message):
    if not is_admin(message.from_user.id): return
    users = db.get_top_users(30)
    text = "👤 <b>Юзери:</b>\n" + "\n".join([f"<code>{u['telegram_id']}</code> | @{u['username']} | {u['coins']}💰" for u in users])
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "🔙 Вийти з адмін-панелі")
async def exit_admin(message: Message):
    await message.answer("Головне меню", reply_markup=main_menu())
