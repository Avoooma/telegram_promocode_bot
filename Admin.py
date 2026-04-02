from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import admin_menu, main_menu, cancel_kb, request_actions
from config import ADMIN_IDS

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─── FSM States ─────────────────────────────────────────────────────────────

class AdminPromoState(StatesGroup):
    waiting_code   = State()
    waiting_reward = State()
    waiting_uses   = State()


class AdminDeletePromoState(StatesGroup):
    waiting_code = State()


class AdminUserState(StatesGroup):
    waiting_tg_id = State()
    waiting_delta  = State()


# ─── /admin ──────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Немає доступу.")
        return
    await message.answer("👑 Ласкаво просимо до адмін-панелі!", reply_markup=admin_menu())


@router.message(F.text == "🔙 Вийти з адмін-панелі")
async def exit_admin(message: Message):
    await message.answer("Повернулись до головного меню.", reply_markup=main_menu())


# ─── Створити промокод ───────────────────────────────────────────────────────

@router.message(F.text == "➕ Промокод")
async def add_promo_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminPromoState.waiting_code)
    await message.answer("🔤 Введи назву промокоду:", reply_markup=cancel_kb())


@router.message(AdminPromoState.waiting_code)
async def add_promo_code(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=admin_menu())
        return
    await state.update_data(code=message.text.strip().upper())
    await state.set_state(AdminPromoState.waiting_reward)
    await message.answer("💰 Скільки монет дає цей промокод?")


@router.message(AdminPromoState.waiting_reward)
async def add_promo_reward(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=admin_menu())
        return
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("❌ Введи ціле позитивне число.")
        return
    await state.update_data(reward=int(message.text))
    await state.set_state(AdminPromoState.waiting_uses)
    await message.answer("🔢 Скільки разів можна використати?")


@router.message(AdminPromoState.waiting_uses)
async def add_promo_uses(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=admin_menu())
        return
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("❌ Введи ціле позитивне число.")
        return

    data = await state.get_data()
    created = db.create_promocode(data["code"], data["reward"], int(message.text))
    await state.clear()

    if created:
        await message.answer(
            f"✅ Промокод <b>{data['code']}</b> створено!\n"
            f"💰 Нагорода: {data['reward']} монет\n"
            f"🔢 Використань: {message.text}",
            parse_mode="HTML",
            reply_markup=admin_menu()
        )
    else:
        await message.answer("❌ Промокод з такою назвою вже існує.", reply_markup=admin_menu())


# ─── Список промокодів ───────────────────────────────────────────────────────

@router.message(F.text == "📋 Всі промокоди")
async def list_promos(message: Message):
    if not is_admin(message.from_user.id):
        return
    promos = db.list_promocodes()
    if not promos:
        await message.answer("Промокодів немає.")
        return

    lines = ["📋 <b>Всі промокоди:</b>\n"]
    for p in promos:
        lines.append(
            f"🎟 <code>{p['code']}</code> — {p['reward']} монет, залишилось: {p['uses_left']}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


# ─── Видалити промокод ───────────────────────────────────────────────────────

@router.message(F.text == "🗑 Видалити промокод")
async def delete_promo_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminDeletePromoState.waiting_code)
    await message.answer("Введи назву промокоду для видалення:", reply_markup=cancel_kb())


@router.message(AdminDeletePromoState.waiting_code)
async def delete_promo_confirm(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=admin_menu())
        return
    deleted = db.delete_promocode(message.text.strip().upper())
    await state.clear()
    if deleted:
        await message.answer(f"✅ Промокод <b>{message.text.upper()}</b> видалено.", parse_mode="HTML", reply_markup=admin_menu())
    else:
        await message.answer("❌ Промокод не знайдено.", reply_markup=admin_menu())


# ─── Заявки ──────────────────────────────────────────────────────────────────

@router.message(F.text == "📥 Заявки")
async def show_requests(message: Message):
    if not is_admin(message.from_user.id):
        return
    reqs = db.get_pending_requests()
    if not reqs:
        await message.answer("✅ Нових заявок немає.")
        return

    for r in reqs:
        user_data = r.get("users", {})
        text = (
            f"📥 <b>Заявка #{r['id']}</b>\n"
            f"👤 @{user_data.get('username', '—')} (TG: <code>{user_data.get('telegram_id', '—')}</code>)\n"
            f"🎮 Скін: <b>{r['item_name']}</b>\n"
            f"💰 Вартість: <b>{r['cost']} монет</b>\n"
            f"🔗 Trade URL: <code>{user_data.get('trade_link', 'не вказано')}</code>"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=request_actions(r["id"]))


# ─── Approve / Reject callbacks ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("approve_"))
async def approve_request(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Немає доступу.", show_alert=True)
        return

    request_id = int(callback.data.split("_")[1])
    req = db.get_request_by_id(request_id)

    if not req:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    if req["status"] != "pending":
        await callback.answer("Заявку вже оброблено.", show_alert=True)
        return

    user_data = req["users"]
    if user_data["coins"] < req["cost"]:
        await callback.answer("❌ У користувача недостатньо монет!", show_alert=True)
        return

    # Списуємо монети
    db.update_coins(req["user_id"], -req["cost"])
    db.add_transaction(req["user_id"], "spend", req["cost"], f"Заявка #{req['id']}: {req['item_name']}")
    db.update_request_status(request_id, "approved")

    # Повідомляємо користувача
    try:
        await bot.send_message(
            user_data["telegram_id"],
            f"✅ Твою заявку #{req['id']} підтверджено!\n"
            f"🎮 Скін: <b>{req['item_name']}</b>\n"
            f"💸 Списано: <b>{req['cost']} монет</b>\n\n"
            "Адмін надішле скін на твій Trade URL.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>ПІДТВЕРДЖЕНО</b>",
        parse_mode="HTML"
    )
    await callback.answer("Заявку підтверджено!")


@router.callback_query(F.data.startswith("reject_"))
async def reject_request(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Немає доступу.", show_alert=True)
        return

    request_id = int(callback.data.split("_")[1])
    req = db.get_request_by_id(request_id)

    if not req:
        await callback.answer("Заявку не знайдено.", show_alert=True)
        return

    if req["status"] != "pending":
        await callback.answer("Заявку вже оброблено.", show_alert=True)
        return

    db.update_request_status(request_id, "rejected")

    try:
        await bot.send_message(
            req["users"]["telegram_id"],
            f"❌ Твою заявку #{req['id']} відхилено.\n"
            f"🎮 Скін: <b>{req['item_name']}</b>\n\n"
            "Звернись до підтримки для уточнення.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>ВІДХИЛЕНО</b>",
        parse_mode="HTML"
    )
    await callback.answer("Заявку відхилено!")


# ─── Керування балансом користувача ─────────────────────────────────────────

@router.message(F.text == "👤 Користувач")
async def user_manage_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdminUserState.waiting_tg_id)
    await message.answer(
        "Введи Telegram ID користувача:",
        reply_markup=cancel_kb()
    )


@router.message(AdminUserState.waiting_tg_id)
async def user_manage_id(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=admin_menu())
        return

    if not message.text.lstrip("-").isdigit():
        await message.answer("❌ Введи числовий Telegram ID.")
        return

    tg_id = int(message.text)
    user = db.get_user_by_telegram_id(tg_id)
    if not user:
        await message.answer("❌ Користувача не знайдено.", reply_markup=admin_menu())
        await state.clear()
        return

    await state.update_data(target_user_id=user["id"], tg_id=tg_id)
    await message.answer(
        f"👤 @{user['username']} | 💰 Баланс: {user['coins']} монет\n\n"
        "Введи суму монет для зміни (наприклад <b>+100</b> або <b>-50</b>):",
        parse_mode="HTML"
    )
    await state.set_state(AdminUserState.waiting_delta)


@router.message(AdminUserState.waiting_delta)
async def user_manage_delta(message: Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=admin_menu())
        return

    text = message.text.strip()
    try:
        delta = int(text)
    except ValueError:
        await message.answer("❌ Введи число зі знаком, наприклад +100 або -50.")
        return

    data = await state.get_data()
    new_balance = db.update_coins(data["target_user_id"], delta)
    db.add_transaction(
        data["target_user_id"],
        "earn" if delta > 0 else "spend",
        abs(delta),
        f"Ручна зміна адміністратором"
    )

    await state.clear()
    sign = "+" if delta > 0 else ""
    await message.answer(
        f"✅ Баланс змінено на <b>{sign}{delta} монет</b>.\n"
        f"💰 Новий баланс: <b>{new_balance} монет</b>",
        parse_mode="HTML",
        reply_markup=admin_menu()
    )
