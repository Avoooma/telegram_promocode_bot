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
    await message.answer("👑 Адмін панель", reply_markup=admin_menu())

# --- СТВОРЕННЯ ПРОМОКОДУ ---
@router.message(F.text == "➕ Промокод")
async def promo_step_1(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminPromoState.waiting_code)
    await message.answer("🎟 Введіть текст промокоду:", reply_markup=cancel_kb())

@router.message(AdminPromoState.waiting_code)
async def promo_step_2(message: Message, state: FSMContext):
    if message.text in ["❌ Скасувати", "❌ Отменить"]:
        await state.clear()
        await message.answer("Скасовано.", reply_markup=admin_menu())
        return
    await state.update_data(code=message.text.upper().strip())
    await state.set_state(AdminPromoState.waiting_reward)
    await message.answer("💰 Скільки монет даватиме код?")

@router.message(AdminPromoState.waiting_reward)
async def promo_step_3(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введіть число!")
        return
    await state.update_data(reward=int(message.text))
    await state.set_state(AdminPromoState.waiting_uses)
    await message.answer("🔢 Скільки використань?")

@router.message(AdminPromoState.waiting_uses)
async def promo_step_final(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введіть число!")
        return
    
    data = await state.get_data()
    success = db.create_promocode(data['code'], data['reward'], int(message.text))
    
    await state.clear()
    if success:
        await message.answer(f"✅ Промокод <code>{data['code']}</code> створено!", parse_mode="HTML", reply_markup=admin_menu())
    else:
        await message.answer("❌ Помилка! Можливо такий код вже існує.", reply_markup=admin_menu())

# --- ЗАЯВКИ: ПРИЙНЯТИ / ВІДХИЛИТИ ---
@router.message(F.text == "📥 Заявки")
async def show_admin_requests(message: Message):
    if not is_admin(message.from_user.id): return
    
    reqs = db.get_pending_requests()
    if not reqs:
        await message.answer("✅ Нових заявок немає.")
        return

    for r in reqs:
        user_data = r.get('users', {})
        u_db_id = user_data.get('id')
        username = user_data.get('username', 'Unknown')
        trade = user_data.get('trade_link', 'Не вказано')
        
        history = db.get_user_transactions(u_db_id, limit=3)
        history_text = "\n".join([f"• {h['type']}: {h['amount']}💰" for h in history]) if history else "Порожньо"

        text = (
            f"📦 <b>Заявка №{r['id']}</b>\n"
            f"👤 Юзер: @{username}\n"
            f"💰 Сума: {r['cost']} монет\n"
            f"🔗 Трейд: <code>{trade}</code>\n\n"
            f"📊 <b>Історія:</b>\n{history_text}"
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
    
    parts = callback.data.split("_")
    action = parts[0]
    req_id = int(parts[1])
    
    new_status = "approved" if action == "approve" else "rejected"
    res = db.supabase.table("requests").update({"status": new_status}).eq("id", req_id).execute()
    
    if res.data:
        status_msg = "✅ ПРИЙНЯТО" if action == "approve" else "❌ ВІДХИЛЕНО"
        await callback.message.edit_text(callback.message.text + f"\n\n<b>Рішення: {status_msg}</b>", parse_mode="HTML")
        await callback.answer("Статус оновлено")
    else:
        await callback.answer("Помилка бази даних")

# --- РОБОТА З ПРОМОКОДАМИ (СПИСОК ТА ВИДАЛЕННЯ) ---
@router.message(F.text.contains("промокод"))
async def list_promos(message: Message):
    if not is_admin(message.from_user.id): return
    if "➕" in message.text: return 
    
    promos = db.list_all_promocodes()
    if not promos:
        await message.answer("📭 Промокодів немає.")
        return

    await message.answer("📋 <b>Список промокодів:</b>", parse_mode="HTML")
    for p in promos:
        text = f"🎟 <code>{p['code']}</code> | {p['reward']}💰\n🔢 Залишилось: {p['uses_left']}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"del_promo_{p['id']}")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("del_promo_"))
async def process_del_promo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    promo_id = int(callback.data.split("_")[2])
    if db.delete_promocode(promo_id):
        await callback.answer("✅ Промокод видалено")
        await callback.message.delete()
    else:
        await callback.answer("❌ Помилка видалення")

# --- КОРИСТУВАЧІ ---
@router.message(F.text.contains("Пользовател"))
async def list_users(message: Message):
    if not is_admin(message.from_user.id): return
    users = db.get_top_users(30)
    text = "👤 <b>Топ-30 юзерів:</b>\n\n"
    for u in users:
        name = f"@{u['username']}" if u.get('username') else "Anon"
        text += f"<code>{u['telegram_id']}</code> | {name} | {u.get('coins', 0)}💰\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.contains("Вийти") | F.text.contains("меню") | F.text.contains("админ панел"))
async def exit_admin(message: Message):
    await message.answer("Ви вийшли з адмін-панелі. Головне меню:", reply_markup=main_menu())
