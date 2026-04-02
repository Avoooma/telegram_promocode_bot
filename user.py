import os
import re
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import main_menu, cancel_kb

router = Router()

class PromoState(StatesGroup):
    waiting_code = State()

class TradeState(StatesGroup):
    waiting_link = State()

class RequestState(StatesGroup):
    waiting_amount = State()
    waiting_item = State()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = db.get_or_create_user(message.from_user.id, message.from_user.username or "Анонім")
    await message.answer(f"👋 Привіт! Баланс: {user['coins']} монет", reply_markup=main_menu())

# --- Баланс ---
@router.message(F.text == "💰 Баланс")
async def show_balance(message: Message):
    user = db.get_user_by_telegram_id(message.from_user.id)
    await message.answer(f"💰 Твій баланс: <b>{user['coins']} монет</b>", parse_mode="HTML")

# --- Заявка на скін ---
@router.message(F.text == "📦 Заявка на скін")
async def request_start(message: Message, state: FSMContext):
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user.get("trade_link"):
        await message.answer("⚠️ Спочатку прив'яжи 🔗 Trade URL!")
        return
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="50 монет"), KeyboardButton(text="150 монет")],
            [KeyboardButton(text="300 монет")],
            [KeyboardButton(text="❌ Скасувати")]
        ],
        resize_keyboard=True
    )
    await state.set_state(RequestState.waiting_amount)
    await message.answer("💰 Обери суму скіна:", reply_markup=kb)

@router.message(RequestState.waiting_amount)
async def req_amount(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return
    
    try:
        val = int(message.text.split()[0])
        user = db.get_user_by_telegram_id(message.from_user.id)
        if user['coins'] < val:
            await message.answer("❌ Недостатньо монет!")
            await state.clear()
            return
        await state.update_data(cost=val)
        await state.set_state(RequestState.waiting_item)
        await message.answer("📦 Введи назву скіна:", reply_markup=cancel_kb())
    except:
        await message.answer("Обери суму на кнопках!")

@router.message(RequestState.waiting_item)
async def req_item(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return
    data = await state.get_data()
    user = db.get_user_by_telegram_id(message.from_user.id)
    db.create_request(user["id"], message.text, data["cost"])
    await state.clear()
    await message.answer("✅ Заявку надіслано!", reply_markup=main_menu())
