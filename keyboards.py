from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🎟 Промокод")],
            [KeyboardButton(text="📦 Заявка на скин"), KeyboardButton(text="🔗 Trade URL")],
            [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="📋 Мои заявки")]
        ],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Промокод"), KeyboardButton(text="📋 Всё промокоды")],
            [KeyboardButton(text="📥 Заявки"), KeyboardButton(text="👤 Пользователи")],
            [KeyboardButton(text="🔙 Выйти из админ панели")]
        ],
        resize_keyboard=True
    )

def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True
    )

def request_actions(request_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{request_id}")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"reject_{request_id}")]
        ]
    )
