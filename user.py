import os
import re
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import main_menu, cancel_kb

router = Router()
STEAM_TRADE_RE = re.compile(r"https://steamcommunity\.com/tradeoffer/new/\?partner=\d+&token=[\w-]+")

# Всё станы в одному класе
class UserStates(StatesGroup):
    waiting_promo = State()
    waiting_trade = State()
    waiting_amount = State() # Финальная заявка

@router.message(CommandStart())
async def start(message: Message):
    db.get_or_create_user(message.from_user.id, message.from_user.username or "Anon")
    await message.answer("👋 Привет!", reply_markup=main_menu())

# --- ТОП И БАЛАНС ---
@router.message(F.text == "💰 Баланс")
async def bal(message: Message):
    u = db.get_user_by_telegram_id(message.from_user.id)
    await message.answer(f"💰 Твой баланс: {u['coins']} монет")

@router.message(F.text == "🏆 Топ")
async def top(message: Message):
    users = db.get_top_users(10)
    text = "🏆 <b>Топ 10 игроков:</b>\n\n"
    for i, u in enumerate(users, 1):
        text += f"{i}. @{u['username']} — {u['coins']} 💰\n"
    await message.answer(text, parse_mode="HTML")

# --- МОИ ЗАЯВКИ ---
@router.message(F.text == "📋 Мои заявки")
async def my_reqs(message: Message):
    u = db.get_user_by_telegram_id(message.from_user.id)
    reqs = db.get_user_requests(u['id'])
    if not reqs:
        await message.answer("У тебя ещё нету заявок.")
        return
    text = "📋 <b>Твои заявки:</b>\n"
    for r in reqs:
        status = "⏳" if r['status'] == 'pending' else "✅" if r['status'] == 'approved' else "❌"
        text += f"{status} {r['item_name']} ({r['cost']}💰)\n"
    await message.answer(text, parse_mode="HTML")

# --- ПРОМОКОД ---
@router.message(F.text == "🎟 Промокод")
async def promo_act(message: Message, state: FSMContext):
    await state.set_state(UserStates.waiting_promo)
    await message.answer("Введите промокод:", reply_markup=cancel_kb())

@router.message(UserStates.waiting_promo)
async def promo_process(message: Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Меню", reply_markup=main_menu())
        return
    
    u = db.get_user_by_telegram_id(message.from_user.id)
    p = db.get_promocode(message.text)
    
    if not p or p['uses_left'] <= 0 or db.is_promo_used_by_user(u['id'], p['id']):
        await message.answer("❌ Не верный, использованый или не существующий код.")
    else:
        new_bal = db.use_promocode(u['id'], p)
        await message.answer(f"✅ +{p['reward']} монет! Баланс: {new_bal}")
    await state.clear()
    await message.answer("Главное меню", reply_markup=main_menu())

# --- TRADE URL ---
@router.message(F.text == "🔗 Trade URL")
async def trade_set(message: Message, state: FSMContext):
    await state.set_state(UserStates.waiting_trade)
    await message.answer("Отправь свою трейд ссылку:", reply_markup=cancel_kb())

@router.message(UserStates.waiting_trade)
async def trade_process(message: Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Отменено", reply_markup=main_menu())
        return

    if STEAM_TRADE_RE.match(message.text):
        u = db.get_user_by_telegram_id(message.from_user.id)
        db.set_trade_link(u['id'], message.text)
        await message.answer("✅ Ссылку сохранено!")
        await state.clear()
        await message.answer("Главное меню", reply_markup=main_menu())
    else:
        await message.answer("❌ Не верный формат. Попробуй ещё раз.")

# --- ЗАЯВКА НА СКИН ---
@router.message(F.text == "📦 Заявка на скин")
async def request_start(message: Message, state: FSMContext):
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user or not user.get("trade_link"):
        await message.answer("⚠️ Сначала нажми кнопку 🔗 Trade URL и укажи трейд ссылку!")
        return
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="50 монет"), KeyboardButton(text="150 монет")],
            [KeyboardButton(text="300 монет")],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True
    )
    await state.set_state(UserStates.waiting_amount)
    await message.answer("💰 Выбери сумму скина (монеты будут списаны сразу):", reply_markup=kb)

@router.message(UserStates.waiting_amount)
async def request_final(message: Message, state: FSMContext):
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer("Отменено", reply_markup=main_menu())
        return

    # Получаем число из текста
    try:
        amount = int(message.text.split()[0])
        user = db.get_user_by_telegram_id(message.from_user.id)
        
        if user['coins'] < amount:
            await message.answer(f"❌ Не достаточно монет! Твой баланс: {user['coins']}")
            await state.clear()
            await message.answer("Главное меню", reply_markup=main_menu())
            return

        # Названик скина
        item_name = f"Скін за {amount} монет"
        
        # делаем заявку
        db.create_request(user["id"], item_name, amount)
        
        await state.clear()
        await message.answer(
            f"✅ Заявку на <b>{item_name}</b> принято!\n"
            f"💰 Списано {amount} монет. Ожидай одобрения админа.", 
            reply_markup=main_menu(), 
            parse_mode="HTML"
        )
    except:
        await message.answer("Пожалуйста, выбери сумму кнопкой!")
