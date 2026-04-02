import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import main_menu, cancel_kb
from config import ADMIN_IDS

router = Router()

STEAM_TRADE_RE = re.compile(
    r"https://steamcommunity\.com/tradeoffer/new/\?partner=\d+&token=[\w-]+"
)


# ─── FSM States ─────────────────────────────────────────────────────────────

class PromoState(StatesGroup):
    waiting_code = State()


class TradeState(StatesGroup):
    waiting_link = State()


class RequestState(StatesGroup):
    waiting_item = State()
    waiting_cost = State()


# ─── /start ─────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = db.get_or_create_user(message.from_user.id, message.from_user.username or "Невідомий")
    await message.answer(
        f"👋 Привіт, <b>{message.from_user.first_name}</b>!\n\n"
        f"💰 Твій баланс: <b>{user['coins']} монет</b>\n\n"
        "Використовуй меню нижче для навігації.",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


# ─── /help ───────────────────────────────────────────────────────────────────

@router.message(Command("help"))
@router.message(F.text == "❓ Допомога")
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Доступні команди:</b>\n\n"
        "💰 <b>Баланс</b> — поточна кількість монет\n"
        "🎟 <b>Промокод</b> — активувати промокод\n"
        "🏆 <b>Топ</b> — рейтинг гравців\n"
        "🔗 <b>Trade URL</b> — прив'язати Steam Trade URL\n"
        "📦 <b>Заявка на скін</b> — обміняти монети на CS:GO скін\n"
        "📋 <b>Мої заявки</b> — переглянути статус заявок\n"
        "❓ <b>Допомога</b> — це повідомлення",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ─── Баланс ──────────────────────────────────────────────────────────────────

@router.message(F.text == "💰 Баланс")
async def show_balance(message: Message):
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Введи /start для початку.")
        return
    await message.answer(
        f"💰 Твій баланс: <b>{user['coins']} монет</b>",
        parse_mode="HTML"
    )


# ─── Промокод ────────────────────────────────────────────────────────────────

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
        await message.answer("❌ Промокод не знайдено.", reply_markup=main_menu())
        await state.clear()
        return

    if promo["uses_left"] <= 0:
        await message.answer("❌ Цей промокод вже вичерпано.", reply_markup=main_menu())
        await state.clear()
        return

    if db.is_promo_used_by_user(user["id"], promo["id"]):
        await message.answer("❌ Ти вже використовував цей промокод.", reply_markup=main_menu())
        await state.clear()
        return

    new_balance = db.use_promocode(user["id"], promo)
    await message.answer(
        f"✅ Промокод активовано!\n"
        f"➕ Нараховано: <b>{promo['reward']} монет</b>\n"
        f"💰 Баланс: <b>{new_balance} монет</b>",
        parse_mode="HTML",
        reply_markup=main_menu()
    )
    await state.clear()


# ─── Топ ─────────────────────────────────────────────────────────────────────

@router.message(F.text == "🏆 Топ")
async def show_top(message: Message):
    top = db.get_top_users(10)
    if not top:
        await message.answer("Список порожній.")
        return

    lines = ["🏆 <b>Топ гравців:</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = u["username"] or "Анонім"
        lines.append(f"{medal} <b>{name}</b> — {u['coins']} монет")

    await message.answer("\n".join(lines), parse_mode="HTML")


# ─── Trade URL ───────────────────────────────────────────────────────────────

@router.message(F.text == "🔗 Trade URL")
async def trade_start(message: Message, state: FSMContext):
    await state.set_state(TradeState.waiting_link)
    await message.answer(
        "🔗 Введи свій Steam Trade URL:\n"
        "<i>Приклад: https://steamcommunity.com/tradeoffer/new/?partner=...&token=...</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )


@router.message(TradeState.waiting_link)
async def trade_enter(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return

    link = message.text.strip()
    if not STEAM_TRADE_RE.match(link):
        await message.answer(
            "❌ Невалідне посилання. Воно має виглядати так:\n"
            "<code>https://steamcommunity.com/tradeoffer/new/?partner=XXXXX&token=XXXXX</code>",
            parse_mode="HTML"
        )
        return

    user = db.get_user_by_telegram_id(message.from_user.id)
    db.set_trade_link(user["id"], link)
    await state.clear()
    await message.answer("✅ Trade URL збережено!", reply_markup=main_menu())


# ─── Заявка на скін ──────────────────────────────────────────────────────────

@router.message(F.text == "📦 Заявка на скін")
async def request_start(message: Message, state: FSMContext):
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user.get("trade_link"):
        await message.answer(
            "⚠️ Спочатку прив'яжи свій Trade URL через кнопку 🔗 Trade URL.",
            reply_markup=main_menu()
        )
        return
    await state.set_state(RequestState.waiting_item)
    await message.answer("📦 Введи назву CS:GO скіна, який хочеш отримати:", reply_markup=cancel_kb())


@router.message(RequestState.waiting_item)
async def request_item(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return
    await state.update_data(item_name=message.text.strip())
    await state.set_state(RequestState.waiting_cost)
    await message.answer("💰 Скільки монет витратити на цей скін?")


@router.message(RequestState.waiting_cost)
async def request_cost(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return

    if not message.text.isdigit():
        await message.answer("❌ Введи ціле число монет.")
        return

    cost = int(message.text)
    user = db.get_user_by_telegram_id(message.from_user.id)

    if user["coins"] < cost:
        await message.answer(
            f"❌ Недостатньо монет. Твій баланс: <b>{user['coins']}</b>",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
        await state.clear()
        return

    if cost <= 0:
        await message.answer("❌ Ціна має бути більша за 0.")
        return

    data = await state.get_data()
    req = db.create_request(user["id"], data["item_name"], cost)

    await state.clear()
    await message.answer(
        f"✅ Заявку #{req['id']} створено!\n"
        f"🎮 Скін: <b>{data['item_name']}</b>\n"
        f"💰 Вартість: <b>{cost} монет</b>\n\n"
        "⏳ Очікуй підтвердження адміністратора.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ─── Мої заявки ──────────────────────────────────────────────────────────────

@router.message(F.text == "📋 Мої заявки")
async def my_requests(message: Message):
    user = db.get_user_by_telegram_id(message.from_user.id)
    reqs = db.get_user_requests(user["id"])

    if not reqs:
        await message.answer("У тебе ще немає заявок.")
        return

    status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
    lines = ["📋 <b>Твої заявки:</b>\n"]
    for r in reqs:
        emoji = status_emoji.get(r["status"], "❓")
        lines.append(
            f"#{r['id']} {emoji} <b>{r['item_name']}</b> — {r['cost']} монет"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")
