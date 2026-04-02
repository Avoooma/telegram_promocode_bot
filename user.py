import os
import re
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup # ОСЬ ЦЕЙ РЯДОК ВИПРАВЛЯЄ ПОМИЛКУ

import database as db
from keyboards import main_menu, cancel_kb

router = Router()

STEAM_TRADE_RE = re.compile(
    r"https://steamcommunity\.com/tradeoffer/new/\?partner=\d+&token=[\w-]+"
)

# --- СТАТИ (FSM) ---
class PromoState(StatesGroup):
    waiting_code = State()

class TradeState(StatesGroup):
    waiting_link = State()

class RequestState(StatesGroup):
    waiting_amount = State() # Вибір ціни (50, 150, 300)
    waiting_item = State()   # Назва скіна

# --- КОМАНДИ ---

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = db.get_or_create_user(message.from_user.id, message.from_user.username or "Анонім")
    await message.answer(
        f"👋 Привіт, <b>{message.from_user.first_name}</b>!\n\n"
        f"💰 Твій баланс: <b>{user['coins']} монет</b>",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@router.message(F.text == "🎟 Промокод")
async def promo_start(message: Message, state: FSMContext):
    await state.set_state(PromoState.waiting_code)
    await message.answer("🎟 Введи промокод:", reply_markup=cancel_kb())

@router.message(PromoState.waiting_code)
async def promo_enter(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return

    code = message.text.strip()
    user = db.get_user_by_telegram_id(message.from_user.id)
    promo = db.get_promocode(code)

    if not promo:
        await message.answer("❌ Промокод не знайдено.")
        return

    if promo["uses_left"] <= 0:
        await message.answer("❌ Промокод вичерпано.")
        return

    if db.is_promo_used_by_user(user["id"], promo["id"]):
        await message.answer("❌ Ти вже використовував цей код.")
        return

    new_balance = db.use_promocode(user["id"], promo)
    await message.answer(f"✅ Активовано! +{promo['reward']} монет.\nБаланс: {new_balance}", reply_markup=main_menu())
    await state.clear()

# --- ЗАЯВКА НА СКІН (ВИБІР ЦІНИ) ---

@router.message(F.text == "📦 Заявка на скін")
async def request_start(message: Message, state: FSMContext):
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user.get("trade_link"):
        await message.answer("⚠️ Спочатку вкажи свій 🔗 Trade URL!")
        return
    
    # Клавіатура з вибором суми
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="50 монет"), KeyboardButton(text="150 монет")],
            [KeyboardButton(text="300 монет")],
            [KeyboardButton(text="❌ Скасувати")]
        ],
        resize_keyboard=True
    )
    
    await state.set_state(RequestState.waiting_amount)
    await message.answer("💰 Обери вартість скіна:", reply_markup=kb)

@router.message(RequestState.waiting_amount)
async def request_amount(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return

    # Витягуємо число з тексту "50 монет"
    try:
        amount = int(message.text.split()[0])
    except:
        await message.answer("Будь ласка, обери суму на кнопках.")
        return

    user = db.get_user_by_telegram_id(message.from_user.id)
    if user['coins'] < amount:
        await message.answer(f"❌ Недостатньо монет! Баланс: {user['coins']}")
        await state.clear()
        await message.answer("Повернення...", reply_markup=main_menu())
        return

    await state.update_data(cost=amount)
    await state.set_state(RequestState.waiting_item)
    await message.answer(f"✅ Обрано суму: {amount}\n📦 Тепер напиши назву скіна:", reply_markup=cancel_kb())

@router.message(RequestState.waiting_item)
async def request_final(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return

    data = await state.get_data()
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    db.create_request(user["id"], message.text, data["cost"])
    await state.clear()
    await message.answer("✅ Заявку створено! Очікуй підтвердження адміна.", reply_markup=main_menu())

# --- TRADE URL ---
@router.message(F.text == "🔗 Trade URL")
async def trade_start(message: Message, state: FSMContext):
    await state.set_state(TradeState.waiting_link)
    await message.answer("🔗 Введи свій Steam Trade URL:", reply_markup=cancel_kb())

@router.message(TradeState.waiting_link)
async def trade_save(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return

    if not STEAM_TRADE_RE.match(message.text):
        await message.answer("❌ Невірний формат посилання!")
        return

    user = db.get_user_by_telegram_id(message.from_user.id)
    db.set_trade_link(user["id"], message.text)
    await state.clear()
    await message.answer("✅ Trade URL збережено!", reply_markup=main_menu())
