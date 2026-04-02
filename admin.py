import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import admin_menu, main_menu, cancel_kb

# Отримуємо список адмінів
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

# --- РОБОТА З КОРИСТУВАЧАМИ (ВИПРАВЛЕНО) ---
# Обробляємо і "Пользователь", і "Пользователи" про всяк випадок
@router.message(F.text.contains("Пользователь") | F.text.contains("Пользователи"))
async def list_users(message: Message):
    if not is_admin(message.from_user.id): return
    
    users = db.get_top_users(30)
    if not users:
        await message.answer("📭 Пользователей пока нету или ошибка базы.")
        return

    text = "👤 <b>Пользователи (Топ-30):</b>\n\n"
    for u in users:
        # Захист від порожніх імен (якщо username = None)
        raw_name = u.get('username')
        uname = f"@{raw_name}" if raw_name and str(raw_name) != "None" else "Anon"
        coins = u.get('coins', 0)
        t_id = u.get('telegram_id', '???')
        
        text += f"<code>{t_id}</code> | {uname} | {coins}💰\n"
    
    await message.answer(text, parse_mode="HTML")

# --- СПИСОК ПРОМОКОДІВ (ВИПРАВЛЕНО) ---
# Обробляємо і "Всё промокоды", і "Все промокоды"
@router.message(F.text.contains("промокод"))
async def list_promos(message: Message):
    if not is_admin(message.from_user.id): return
    
    # Якщо це натискання на "➕ Промокод", ігноруємо цей обробник (для цього є інший нижче)
    if "➕" in message.text: return

    promos = db.list_all_promocodes()
    if not promos:
        await message.answer("📭 Список промокодов пустой(привет даня).")
        return

    await message.answer("📋 <b>Активные промокоды:</b>", parse_mode="HTML")
    
    for p in promos:
        text = f"🎟 <code>{p['code']}</code>\n💰 Награда: {p['reward']}\n🔢 Осталось: {p['uses_left']} шт."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_promo_{p['id']}")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

# --- СТВОРЕННЯ ПРОМОКОДУ ---
@router.message(F.text == "➕ Промокод")
async def promo_step_1(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await state.set_state(AdminPromoState.waiting_code)
    await message.answer("🎟 Введите текст промокода:", reply_markup=cancel_kb())

# --- РЕШТА КОДУ (ЗАЯВКИ ТА ІНШЕ) ---
@router.message(F.text == "📥 Заявки")
async def show_admin_requests(message: Message):
    if not is_admin(message.from_user.id): return
    reqs = db.get_pending_requests()
    if not reqs:
        await message.answer("✅ Новых заявок на скины нету.")
        return
    
    for r in reqs:
        user_data = r.get('users', {})
        u_db_id = user_data.get('id')
        username = user_data.get('username', 'Unknown')
        trade = user_data.get('trade_link', 'Не указано')
        history = db.get_user_transactions(u_db_id, limit=3)
        
        history_text = "\n".join([f"• {h['type']}: {h['amount']}💰" for h in history]) if history else "История пустая."
        
        text = (f"📦 <b>Заявка №{r['id']}</b>\n👤 Юзер: @{username}\n💰 Сума: {r['cost']}\n"
                f"🔗 Трейд: <code>{trade}</code>\n\n📊 <b>История:</b>\n{history_text}")
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{r['id']}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{r['id']}")]
        ])
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

# Обробник видалення промокоду
@router.callback_query(F.data.startswith("del_promo_"))
async def process_del_promo(callback: CallbackQuery):
    promo_id = int(callback.data.split("_")[2])
    if db.delete_promocode(promo_id):
        await callback.answer("✅ Удалено")
        await callback.message.delete()

@router.message(F.text == "🔙 Выйти из админ панели")
async def exit_admin(message: Message):
    await message.answer("Вы вернулися в главное меню.", reply_markup=main_menu())
