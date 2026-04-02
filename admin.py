import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=admin_menu())
        return
    await state.update_data(code=message.text.upper())
    await state.set_state(AdminPromoState.waiting_reward)
    await message.answer("💰 Скільки монет даватиме цей код?")

@router.message(AdminPromoState.waiting_reward)
async def promo_step_3(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Будь ласка, введіть число!")
        return
    await state.update_data(reward=int(message.text))
    await state.set_state(AdminPromoState.waiting_uses)
    await message.answer("🔢 Скільки людей можуть його активувати?")

@router.message(AdminPromoState.waiting_uses)
async def promo_step_final(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Будь ласка, введіть число!")
        return
    data = await state.get_data()
    success = db.create_promocode(data['code'], data['reward'], int(message.text))
    await state.clear()
    if success:
        await message.answer(f"✅ Промокод {data['code']} створено!", reply_markup=admin_menu())
    else:
        await message.answer("❌ Помилка при створенні.", reply_markup=admin_menu())

# --- РОБОТА ІЗ ЗАЯВКАМИ (АДМІН) + ІСТОРІЯ ---
@router.message(F.text == "📥 Заявки")
async def show_admin_requests(message: Message):
    if not is_admin(message.from_user.id): return
    
    reqs = db.get_pending_requests()
    if not reqs:
        await message.answer("✅ Нових заявок на скіни немає.")
        return

    await message.answer(f"📥 <b>Активні заявки ({len(reqs)}):</b>", parse_mode="HTML")
    
    for r in reqs:
        user_data = r.get('users', {})
        u_db_id = user_data.get('id')
        username = user_data.get('username', 'Unknown')
        trade = user_data.get('trade_link', 'Не вказано')
        
        # ОТРИМУЄМО ІСТОРІЮ ТРАНЗАКЦІЙ (останні 3)
        history = db.get_user_transactions(u_db_id, limit=3)
        if history:
            h_list = []
            for h in history:
                # Форматуємо дату (якщо вона є)
                h_date = h['date'][:10] if h.get('date') else ""
                h_list.append(f"• {h['type']}: {h['amount']}💰 ({h_date})")
            history_text = "\n".join(h_list)
        else:
            history_text = "Історія транзакцій порожня."

        text = (
            f"📦 <b>Заявка №{r['id']}</b>\n"
            f"👤 Юзер: @{username}\n"
            f"💰 Сума: <b>{r['cost']} монет</b>\n"
            f"🔗 Трейд: <code>{trade}</code>\n\n"
            f"📊 <b>Остання історія монет:</b>\n{history_text}"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Прийняти", callback_data=f"approve_{r['id']}"),
                InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject_{r['id']}")
            ]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("approve_") | F.data.startswith("reject_"))
async def handle_request_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    data_parts = callback.data.split("_")
    action = data_parts[0]
    req_id = int(data_parts[1])
    
    new_status = "approved" if action == "approve" else "rejected"
    
    res = db.supabase.table("requests").update({"status": new_status}).eq("id", req_id).execute()
    
    if res.data:
        status_text = "✅ ПІДТВЕРДЖЕНО" if action == "approve" else "❌ ВІДХИЛЕНО"
        # Отримуємо старий текст і додаємо статус
        current_text = callback.message.text
        await callback.message.edit_text(current_text + f"\n\n<b>Рішення: {status_text}</b>", parse_mode="HTML")
        await callback.answer(f"Заявку №{req_id} оновлено")
    else:
        await callback.answer("Помилка оновлення статусу")

# --- ВИДАЛЕННЯ ТА СПИСОК ПРОМОКОДІВ ---
@router.message(F.text == "📋 Всі промокоди")
async def list_promos(message: Message):
    if not is_admin(message.from_user.id): return
    promos = db.list_all_promocodes()
    if not promos:
        await message.answer("📭 Список промокодів порожній.")
        return

    await message.answer("📋 <b>Активні промокоди:</b>", parse_mode="HTML")
    
    for p in promos:
        text = f"🎟 <code>{p['code']}</code>\n💰 Нагорода: {p['reward']}\n🔢 Залишилось: {p['uses_left']} шт."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"del_promo_{p['id']}")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("del_promo_"))
async def process_del_promo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    promo_id = int(callback.data.split("_")[2])
    if db.delete_promocode(promo_id):
        await callback.answer("✅ Видалено")
        await callback.message.delete()
    else:
        await callback.answer("❌ Помилка видалення")

# --- ІНШІ КНОПКИ ---
@router.message(F.text == "👤 Користувач")
async def list_users(message: Message):
    if not is_admin(message.from_user.id): return
    users = db.get_top_users(30)
    text = "👤 <b>Юзери (Топ-30):</b>\n\n"
    for u in users:
        text += f"<code>{u['telegram_id']}</code> | @{u['username']} | {u['coins']}💰\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "🔙 Вийти з адмін-панелі")
async def exit_admin(message: Message):
    await message.answer("Ви повернулися до головного меню.", reply_markup=main_menu())
