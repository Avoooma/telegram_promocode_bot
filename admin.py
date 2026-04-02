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
    await message.answer("👑 Админ панель", reply_markup=admin_menu())

# --- Создание промокода ---
@router.message(F.text == "➕ Промокод")
async def promo_step_1(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminPromoState.waiting_code)
    await message.answer("🎟 Введите текст промокоду (например: GIFT2024):", reply_markup=cancel_kb())

@router.message(AdminPromoState.waiting_code)
async def promo_step_2(message: Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Отменено.", reply_markup=admin_menu())
        return
    await state.update_data(code=message.text.upper())
    await state.set_state(AdminPromoState.waiting_reward)
    await message.answer("💰 Сколько монет будет давать промокод?")

@router.message(AdminPromoState.waiting_reward)
async def promo_step_3(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число!")
        return
    await state.update_data(reward=int(message.text))
    await state.set_state(AdminPromoState.waiting_uses)
    await message.answer("🔢 Сколько людей может активировать?")

@router.message(AdminPromoState.waiting_uses)
async def promo_step_final(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число!")
        return
    data = await state.get_data()
    success = db.create_promocode(data['code'], data['reward'], int(message.text))
    await state.clear()
    if success:
        await message.answer(f"✅ Промокод {data['code']} створено!", reply_markup=admin_menu())
    else:
        await message.answer("❌ Ошибка при создании.", reply_markup=admin_menu())

# --- РОБОТА ИЗ ЗАЯВКАМИ (АДМИН) + ИСТОРИЯ ---
@router.message(F.text == "📥 Заявки")
async def show_admin_requests(message: Message):
    if not is_admin(message.from_user.id): return
    
    reqs = db.get_pending_requests()
    if not reqs:
        await message.answer("✅ Новых заявок на скины нету.")
        return

    await message.answer(f"📥 <b>Активные заявки ({len(reqs)}):</b>", parse_mode="HTML")
    
    for r in reqs:
        user_data = r.get('users', {})
        u_db_id = user_data.get('id')
        username = user_data.get('username', 'Unknown')
        trade = user_data.get('trade_link', 'Не указано')
        
        # ПОЛУЧАЕМ ИСТОРИЮ ТРАНЗАКЦИЙ (останні 3)
        history = db.get_user_transactions(u_db_id, limit=3)
        if history:
            h_list = []
            for h in history:
                h_date = h['date'][:10] if h.get('date') else ""
                h_list.append(f"• {h['type']}: {h['amount']}💰 ({h_date})")
            history_text = "\n".join(h_list)
        else:
            history_text = "История заявок пустая."

        text = (
            f"📦 <b>Заявка №{r['id']}</b>\n"
            f"👤 Юзер: @{username}\n"
            f"💰 Сума: <b>{r['cost']} монет</b>\n"
            f"🔗 Трейд: <code>{trade}</code>\n\n"
            f"📊 <b>Последняя история монет:</b>\n{history_text}"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Прийнять", callback_data=f"approve_{r['id']}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{r['id']}")
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
        status_text = "✅ ПОДТВЕРДЖЕНО" if action == "approve" else "❌ ОТКЛОНЕНО"
        current_text = callback.message.text
        await callback.message.edit_text(current_text + f"\n\n<b>Рішення: {status_text}</b>", parse_mode="HTML")
        await callback.answer(f"Заявку №{req_id} обновлено")
    else:
        await callback.answer("Ошибка обновления статуса")

# --- УДАЛЕНИЕ И СПИСОК ПРОМОКОДОВ ---
@router.message(F.text == "📋 Всё промокоди")
async def list_promos(message: Message):
    if not is_admin(message.from_user.id): return
    promos = db.list_all_promocodes()
    if not promos:
        await message.answer("📭 Список промокодов пустой(привет даня).")
        return

    await message.answer("📋 <b>Активные промокоды:</b>", parse_mode="HTML")
    
    for p in promos:
        text = f"🎟 <code>{p['code']}</code>\n💰 Награда: {p['reward']}\n🔢 Осталось: {p['uses_left']} штук."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_promo_{p['id']}")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("del_promo_"))
async def process_del_promo(callback: CallbackQuery):
    if not is_admin(callback.from_user.id): return
    
    promo_id = int(callback.data.split("_")[2])
    if db.delete_promocode(promo_id):
        await callback.answer("✅ Удалено")
        await callback.message.delete()
    else:
        await callback.answer("❌ Ошибка Удаления")

# --- Другие кнопки ---
@router.message(F.text == "👤 Пользователь")
async def list_users(message: Message):
    if not is_admin(message.from_user.id): return
    
    users = db.get_top_users(30)
    if not users:
        await message.answer("📭 Пользователей пока нету.")
        return

    text = "👤 <b>Пользователи (Топ-30):</b>\n\n"
    for u in users:
        # Додаємо обробку, якщо раптом username порожній
        uname = f"@{u['username']}" if u.get('username') and u['username'] != "None" else "Anon"
        text += f"<code>{u['telegram_id']}</code> | {uname} | {u.get('coins', 0)}💰\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "🔙 Выйти из админ панели")
async def exit_admin(message: Message):
    await message.answer("Вы вернулися в главное меню.", reply_markup=main_menu())
