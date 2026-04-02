from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🎟 Промокод")],
            [KeyboardButton(text="📦 Заявка на скін"), KeyboardButton(text="🔗 Trade URL")],
            [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="📋 Мої заявки")]
        ],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Промокод"), KeyboardButton(text="📋 Всі промокоди")],
            [KeyboardButton(text="📥 Заявки"), KeyboardButton(text="👤 Користувач")],
            [KeyboardButton(text="🔙 Вийти з адмін-панелі")]
        ],
        resize_keyboard=True
    )

def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Скасувати")]],
        resize_keyboard=True
    )

def request_actions(request_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Підтвердити", callback_data=f"approve_{request_id}")],
            [InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject_{request_id}")]
        ]
    )
