from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


# ─── Головне меню користувача ───────────────────────────────────────────────

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🎟 Промокод")],
            [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="🔗 Trade URL")],
            [KeyboardButton(text="📦 Заявка на скін"), KeyboardButton(text="📋 Мої заявки")],
            [KeyboardButton(text="❓ Допомога")],
        ],
        resize_keyboard=True
    )


# ─── Адмін-меню ─────────────────────────────────────────────────────────────

def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Промокод"), KeyboardButton(text="📋 Всі промокоди")],
            [KeyboardButton(text="📥 Заявки"), KeyboardButton(text="👤 Користувач")],
            [KeyboardButton(text="🗑 Видалити промокод")],
            [KeyboardButton(text="🔙 Вийти з адмін-панелі")],
        ],
        resize_keyboard=True
    )


# ─── Кнопки для заявки ──────────────────────────────────────────────────────

def request_actions(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Підтвердити", callback_data=f"approve_{request_id}"),
            InlineKeyboardButton(text="❌ Відхилити",   callback_data=f"reject_{request_id}"),
        ]
    ])


# ─── Скасування (FSM) ───────────────────────────────────────────────────────

def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Скасувати")]],
        resize_keyboard=True
    )
