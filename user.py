# ... твої імпорти ...

class RequestState(StatesGroup):
    waiting_amount = State() # Новий етап вибору суми
    waiting_item = State()

@router.message(F.text == "📦 Заявка на скін")
async def request_start(message: Message, state: FSMContext):
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user.get("trade_link"):
        await message.answer("⚠️ Спочатку прив'яжи Trade URL!")
        return
    
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    kb.button(text="50 монет")
    kb.button(text="150 монет")
    kb.button(text="300 монет")
    kb.button(text="❌ Скасувати")
    kb.adjust(3, 1)
    
    await state.set_state(RequestState.waiting_amount)
    await message.answer("💰 Обери суму, на яку хочеш скін:", reply_markup=kb.as_markup(resize_keyboard=True))

@router.message(RequestState.waiting_amount)
async def request_amount_selected(message: Message, state: FSMContext):
    if "монет" not in message.text:
        await message.answer("Будь ласка, обери суму на кнопках.")
        return
    
    amount = int(message.text.split()[0])
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if user['coins'] < amount:
        await message.answer(f"❌ Недостатньо монет! У тебе лише {user['coins']}.")
        await state.clear()
        return

    await state.update_data(cost=amount)
    await state.set_state(RequestState.waiting_item)
    await message.answer("📦 Тепер напиши назву скіна, який хочеш:", reply_markup=cancel_kb())
