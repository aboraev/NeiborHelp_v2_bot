import os
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError
from dotenv import load_dotenv
from database import Database

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MASTERS_GROUP_ID = int(os.getenv("MASTERS_GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()

class NeedHelpStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_text = State()
    waiting_for_timing = State()
    waiting_for_custom_time = State()
    waiting_for_contact = State()

class CanHelpStates(StatesGroup):
    waiting_for_categories = State()

class MasterCancelStates(StatesGroup):
    waiting_for_comment = State()

CATEGORIES = {
    "lawyer": "⚖️ Юрист",
    "accountant": "📊 Бухгалтер",
    "courier": "🚚 Курьер / Перевозка",
    "baking": "🥐 Выпечка",
    "plumbing": "🚿 Сантехника",
    "electrical": "⚡ Электрика",
    "large_appliance": "🧺 Ремонт крупной техники",
    "small_appliance": "🔌 Ремонт мелкой техники",
    "pc_repair": "💻 Ремонт ПК",
    "tv_repair": "📺 Ремонт ТВ",
    "renovation": "🏠 Ремонт квартиры",
    "carpentry": "🪚 Столярные работы",
    "auto": "🚗 Авто",
    "smart_home": "🤖 Умный дом",
    "dev": "🌐 Сайты / Боты / ПО"
}

STATUS_EMOJI = {
    "new": "🟡 Новая",
    "accepted": "🔵 Принята",
    "in_progress": "🟢 В работе",
    "done": "✅ Выполнена",
    "cancelled": "🔴 Отменена"
}

SPAM_WORDS = ["заработок", "крипто", "инвестиции", "казино", "бесплатно", "акция", "скидка", "перейди по ссылке", "заработай", "доход"]
captcha_answers = {}

def generate_captcha():
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    correct = a + b
    options = [correct - 1, correct, correct + 1]
    random.shuffle(options)
    return f"Сколько будет {a} + {b}?", correct, options

def get_customer_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать новую заявку", callback_data="need_help")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_requests")],
        [InlineKeyboardButton(text="ℹ️ Как это работает", callback_data="info")]
    ])

def get_master_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton(text="🤝 Изменить категории", callback_data="can_help")],
        [InlineKeyboardButton(text="ℹ️ Как это работает", callback_data="info")]
    ])

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Мне нужна помощь", callback_data="need_help")],
        [InlineKeyboardButton(text="🤝 Я могу помочь", callback_data="can_help")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_requests")],
        [InlineKeyboardButton(text="ℹ️ Как это работает", callback_data="info")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in captcha_answers and captcha_answers[user_id] == "passed":
        await show_main_menu(message)
        return
    question, correct, options = generate_captcha()
    captcha_answers[user_id] = {"correct": correct, "attempts": 0}
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(opt), callback_data=f"captcha_{opt}") for opt in options]
    ])
    await message.answer(f"👋 Привет! Чтобы защитить чат от спама, подтверди, что ты не бот.\n\n{question}", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("captcha_"))
async def process_captcha(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    answer = int(callback.data.split("_")[1])
    if user_id not in captcha_answers:
        await callback.message.answer("Капча устарела, начните заново /start")
        return
    correct = captcha_answers[user_id]["correct"]
    if answer == correct:
        captcha_answers[user_id] = "passed"
        await callback.message.delete()
        await show_main_menu(callback.message)
    else:
        captcha_answers[user_id]["attempts"] += 1
        if captcha_answers[user_id]["attempts"] >= 3:
            await callback.message.answer("❌ Слишком много попыток. Попробуйте позже.")
            captcha_answers.pop(user_id, None)
        else:
            question, correct, options = generate_captcha()
            captcha_answers[user_id]["correct"] = correct
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=str(opt), callback_data=f"captcha_{opt}") for opt in options]
            ])
            await callback.message.edit_text(f"Неверно. Попробуйте ещё раз:\n\n{question}", reply_markup=keyboard)

async def show_main_menu(message: types.Message, text="Что хотите сделать?"):
    await message.answer(text, reply_markup=get_main_menu())

@dp.callback_query(F.data == "info")
async def show_info(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "👋 <b>Привет, сосед!</b>\n\n"
        "Это бот взаимопомощи нашего дома. Мы просто связываем тех, кому нужна помощь, с теми, кто может её оказать.\n\n"
        "🤝 <b>Никаких комиссий</b>, скрытых платежей или посредников. Вы договариваетесь об условиях и цене напрямую.\n\n"
        "🛡️ <b>Безопасно:</b> ваши контакты передаются мастеру только после того, как он согласится помочь."
    )
    await callback.message.edit_text(text, reply_markup=get_customer_menu(), parse_mode="HTML")

@dp.message(Command("my"))
async def cmd_my_requests(message: types.Message):
    await show_my_requests(message, message.from_user.id)

@dp.callback_query(F.data == "my_requests")
async def callback_my_requests(callback: types.CallbackQuery):
    await callback.answer()
    await show_my_requests(callback.message, callback.from_user.id)

async def show_my_requests(message: types.Message, user_id: int):
    requests = db.get_requests_by_user(user_id)
    if not requests:
        await message.answer("📭 У вас пока нет заявок.", reply_markup=get_customer_menu())
        return
    lines = ["📋 <b>Ваши заявки:</b>\n"]
    for req in requests:
        req_id, text, category, status, executor, created_at = req
        status_emoji = STATUS_EMOJI.get(status, "❓ Неизвестно")
        cat_name = CATEGORIES.get(category, category)
        executor_info = f" | Исполнитель: @{executor}" if executor else ""
        lines.append(f"• №{req_id} {status_emoji}\n  📂 {cat_name}\n  📝 {text[:60]}{'...' if len(text) > 60 else ''}{executor_info}\n")
    result_text = "\n".join(lines)
    await message.answer(result_text, reply_markup=get_customer_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "need_help")
async def process_need_help(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(NeedHelpStates.waiting_for_category)
    categories_list = list(CATEGORIES.items())
    keyboard_rows = []
    for i in range(0, len(categories_list), 2):
        row = [InlineKeyboardButton(text=categories_list[i][1], callback_data=f"cat_{categories_list[i][0]}")]
        if i + 1 < len(categories_list):
            row.append(InlineKeyboardButton(text=categories_list[i+1][1], callback_data=f"cat_{categories_list[i+1][0]}"))
        keyboard_rows.append(row)
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    await callback.message.edit_text("Выберите категорию помощи:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    category = callback.data.split("_", 1)[1]
    await state.update_data(category=category)
    await state.set_state(NeedHelpStates.waiting_for_text)
    await callback.message.edit_text(f"Опишите задачу кратко (до 300 символов):\n\nКатегория: {CATEGORIES[category]}")

@dp.message(NeedHelpStates.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    text = message.text
    if len(text) > 300:
        await message.answer("⚠️ Сообщение слишком длинное. Сократите до 300 символов.")
        return
    if "http" in text.lower() or any(word in text.lower() for word in SPAM_WORDS):
        await message.answer("⚠️ Сообщение отклонено системой защиты от спама.")
        return
    await state.update_data(text=text)
    await state.set_state(NeedHelpStates.waiting_for_timing)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Срочно", callback_data="time_urgent")],
        [InlineKeyboardButton(text="🗓️ Укажу дату и время", callback_data="time_custom")],
        [InlineKeyboardButton(text="🤝 Обговорю с соседом", callback_data="time_discuss")]
    ])
    await message.answer("⏳ Когда нужно выполнить задачу?", reply_markup=keyboard)

@dp.callback_query(F.data == "time_urgent", NeedHelpStates.waiting_for_timing)
async def process_timing_urgent(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(timing="🔥 Срочно")
    await state.set_state(NeedHelpStates.waiting_for_contact)
    await ask_for_contact(callback.message)

@dp.callback_query(F.data == "time_discuss", NeedHelpStates.waiting_for_timing)
async def process_timing_discuss(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(timing="🤝 Обговорю с соседом")
    await state.set_state(NeedHelpStates.waiting_for_contact)
    await ask_for_contact(callback.message)

@dp.callback_query(F.data == "time_custom", NeedHelpStates.waiting_for_timing)
async def process_timing_custom(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(NeedHelpStates.waiting_for_custom_time)
    await callback.message.edit_text("Напишите удобную дату и время (например: завтра после 18:00 или 15 ноября в 14:00).")

@dp.message(NeedHelpStates.waiting_for_custom_time)
async def process_custom_time(message: types.Message, state: FSMContext):
    timing = message.text
    if len(timing) > 50:
        await message.answer("⚠️ Слишком длинно. Напишите короче, например: 'завтра в 18:00'.")
        return
    await state.update_data(timing=timing)
    await state.set_state(NeedHelpStates.waiting_for_contact)
    await ask_for_contact(message)

async def ask_for_contact(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Поделитесь контактом Telegram, чтобы мастер мог с вами связаться:", reply_markup=keyboard)

@dp.message(NeedHelpStates.waiting_for_contact, F.contact)
async def process_contact(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        category = data.get("category")
        text = data.get("text")
        timing = data.get("timing", "Не указано")
        author_id = message.from_user.id
        author_username = message.from_user.username or message.from_user.first_name
        
        if not category or not text:
            await message.answer("⚠️ Произошла ошибка. Начните заново: /start", reply_markup=types.ReplyKeyboardRemove())
            await state.clear()
            return
        
        request_id = db.save_request(author_id, author_username, text, category)
        
        group_message = f"🆕 Новая заявка №{request_id}\n\n📂 Категория: {CATEGORIES[category]}\n⏳ Срочность: {timing}\n📝 Задача: {text}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять заказ", callback_data=f"accept_{request_id}")],
            [InlineKeyboardButton(text="❌ Пропустить", callback_data=f"skip_{request_id}")]
        ])
        
        try:
            await bot.send_message(MASTERS_GROUP_ID, group_message, reply_markup=keyboard)
        except TelegramAPIError as e:
            print(f"Ошибка отправки в группу: {e}")
            await message.answer("⚠️ Не удалось отправить заявку мастерам. Попробуйте позже.", reply_markup=types.ReplyKeyboardRemove())
            await state.clear()
            return
        
        await message.answer(
            f"✅ Заявка №{request_id} передана мастерам.\n\n"
            f"Вы можете отслеживать её статус в разделе «📋 Мои заявки».",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await message.answer("Что хотите сделать дальше?", reply_markup=get_customer_menu())
        await state.clear()
    except Exception as e:
        print(f"Критическая ошибка в process_contact: {e}")
        await message.answer("⚠️ Произошла ошибка. Начните заново: /start", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

@dp.callback_query(F.data.startswith("accept_"))
async def process_accept(callback: types.CallbackQuery):
    await callback.answer()
    request_id = int(callback.data.split("_")[1])
    master_id = callback.from_user.id
    master_username = callback.from_user.username or callback.from_user.first_name
    
    request = db.get_request(request_id)
    if not request or request[5] != "new":
        await callback.message.answer("Этот заказ уже принят", show_alert=True)
        return
    
    db.update_request_status(request_id, "accepted", master_id, master_username)
    author_username = request[2]
    
    await callback.message.edit_text(
        f"✅ Заказ №{request_id} принят мастером @{master_username}\n\n📂 Категория: {CATEGORIES[request[4]]}\n📝 Задача: {request[3]}",
        reply_markup=None
    )
    
    try:
        await bot.send_message(
            master_id,
            f"📞 Вы приняли заказ №{request_id}.\n\n"
            f"📂 Категория: {CATEGORIES[request[4]]}\n"
            f"📝 Задача: {request[3]}\n\n"
            f"👤 Контакт заказчика: @{author_username}\n\n"
            f"Свяжитесь с ним для обсуждения деталей.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🟢 В работе", callback_data=f"progress_{request_id}")],
                [InlineKeyboardButton(text="🔴 Отказаться после диалога", callback_data=f"cancel_after_{request_id}")]
            ])
        )
    except TelegramAPIError:
        pass
    
    try:
        await bot.send_message(request[1], f"🔔 Мастер откликнулся на вашу заявку №{request_id}. Ожидайте сообщения от него.")
    except:
        pass

@dp.callback_query(F.data.startswith("skip_"))
async def process_skip(callback: types.CallbackQuery):
    await callback.answer()
    request_id = int(callback.data.split("_")[1])
    master_username = callback.from_user.username or callback.from_user.first_name
    current_text = callback.message.text
    if "Пропущено:" in current_text:
        new_text = current_text + f", @{master_username}"
    else:
        new_text = current_text + f"\n\n❌ Пропущено: @{master_username}"
    try:
        await callback.message.edit_text(new_text, reply_markup=callback.message.reply_markup)
    except TelegramAPIError:
        pass

@dp.callback_query(F.data.startswith("progress_"))
async def process_progress(callback: types.CallbackQuery):
    await callback.answer()
    request_id = int(callback.data.split("_")[1])
    master_id = callback.from_user.id
    
    db.update_request_status(request_id, "in_progress", master_id)
    request = db.get_request(request_id)
    
    try:
        await bot.send_message(request[1], f"🔧 Мастер приступил к выполнению вашего заказа №{request_id}.")
    except:
        pass
    
    await callback.message.edit_text(
        f"🟢 Заказ №{request_id} в работе.\n\n"
        f"Когда закончите — нажмите «✅ Выполнено».",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{request_id}")],
            [InlineKeyboardButton(text="🔴 Отказаться", callback_data=f"cancel_after_{request_id}")]
        ])
    )

@dp.callback_query(F.data.startswith("cancel_after_"))
async def process_cancel_after(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    request_id = int(callback.data.split("_")[1])
    
    request = db.get_request(request_id)
    if not request or request[6] != callback.from_user.id:
        await callback.message.answer("Вы не принимали этот заказ", show_alert=True)
        return
    
    await state.set_state(MasterCancelStates.waiting_for_comment)
    await state.update_data(cancel_request_id=request_id)
    
    await callback.message.edit_text(
        f"Вы хотите отказаться от заказа №{request_id}.\n\n"
        f"Напишите причину отказа (или просто 'Отмена'):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Не отказываться", callback_data=f"cancel_cancel_{request_id}")]
        ])
    )

@dp.callback_query(F.data.startswith("cancel_cancel_"))
async def cancel_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    request_id = int(callback.data.split("_")[2])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 В работе", callback_data=f"progress_{request_id}")],
        [InlineKeyboardButton(text="🔴 Отказаться после диалога", callback_data=f"cancel_after_{request_id}")]
    ])
    
    request = db.get_request(request_id)
    await callback.message.edit_text(
        f"📞 Вы приняли заказ №{request_id}.\n\n"
        f"📂 Категория: {CATEGORIES[request[4]]}\n"
        f"📝 Задача: {request[3]}\n\n"
        f"👤 Контакт заказчика: @{request[2]}",
        reply_markup=keyboard
    )

@dp.message(MasterCancelStates.waiting_for_comment)
async def process_cancel_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    request_id = data.get("cancel_request_id")
    comment = message.text
    
    request = db.get_request(request_id)
    if not request:
        await message.answer("Заявка не найдена")
        await state.clear()
        return
    
    master_username = message.from_user.username or message.from_user.first_name
    db.update_request_status(request_id, "new", None, None)
    
    group_message = f"🔄 Заявка №{request_id} снова доступна\n\n" \
                    f"📂 Категория: {CATEGORIES[request[4]]}\n" \
                    f"📝 Задача: {request[3]}\n\n" \
                    f"❌ Отказ после диалога от @{master_username}\n" \
                    f"💬 Комментарий: {comment}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять заказ", callback_data=f"accept_{request_id}")],
        [InlineKeyboardButton(text="❌ Пропустить", callback_data=f"skip_{request_id}")]
    ])
    
    try:
        await bot.send_message(MASTERS_GROUP_ID, group_message, reply_markup=keyboard)
    except TelegramAPIError:
        await message.answer("⚠️ Не удалось опубликовать заявку снова")
        await state.clear()
        return
    
    await message.answer("✅ Заявка снова доступна для других мастеров", reply_markup=get_master_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("done_"))
async def process_done(callback: types.CallbackQuery):
    await callback.answer()
    request_id = int(callback.data.split("_")[1])
    master_id = callback.from_user.id
    
    db.update_request_status(request_id, "done", master_id)
    request = db.get_request(request_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Отлично", callback_data=f"rate_5_{request_id}"),
            InlineKeyboardButton(text="👎 Плохо", callback_data=f"rate_1_{request_id}")
        ]
    ])
    
    try:
        await bot.send_message(request[1], f"✅ Заказ №{request_id} выполнен!\n\nОцените работу:", reply_markup=keyboard)
    except:
        pass
    
    await callback.message.edit_text(f"✅ Заказ №{request_id} выполнен!", reply_markup=get_master_menu())

@dp.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: types.CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    rating = int(parts[1])
    request_id = int(parts[2])
    
    request = db.get_request(request_id)
    executor_id = request[6]
    
    db.update_rating(executor_id, rating)
    
    await callback.message.edit_text("✅ Спасибо за оценку!", reply_markup=get_customer_menu())

@dp.callback_query(F.data == "can_help")
async def process_can_help(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CanHelpStates.waiting_for_categories)
    await state.update_data(selected_categories=[])
    await update_categories_keyboard(callback.message, [])

async def update_categories_keyboard(message: types.Message, selected: list):
    categories_list = list(CATEGORIES.items())
    keyboard_rows = []
    for i in range(0, len(categories_list), 2):
        row = []
        for j in range(2):
            idx = i + j
            if idx < len(categories_list):
                cat_key, cat_name = categories_list[idx]
                label = f"✅ {cat_name}" if cat_key in selected else f"⬜ {cat_name}"
                row.append(InlineKeyboardButton(text=label, callback_data=f"toggle_{cat_key}"))
        keyboard_rows.append(row)
    keyboard_rows.append([InlineKeyboardButton(text="✅ Готово", callback_data="finish_selection")])
    if selected:
        keyboard_rows.append([InlineKeyboardButton(text="❌ Сбросить всё", callback_data="reset_selection")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    selected_names = ", ".join([CATEGORIES[c] for c in selected]) if selected else "ничего не выбрано"
    text = f"Выберите категории помощи (можно несколько):\n\n📌 Выбрано: {selected_names}"
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except TelegramAPIError as e:
        if "message is not modified" not in str(e).lower():
            print(f"Ошибка редактирования: {e}")

@dp.callback_query(F.data.startswith("toggle_"), CanHelpStates.waiting_for_categories)
async def toggle_category(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    category = callback.data.replace("toggle_", "")
    data = await state.get_data()
    selected = data.get("selected_categories", [])
    if category in selected:
        selected.remove(category)
    else:
        selected.append(category)
    await state.update_data(selected_categories=selected)
    await update_categories_keyboard(callback.message, selected)

@dp.callback_query(F.data == "reset_selection", CanHelpStates.waiting_for_categories)
async def reset_selection(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(selected_categories=[])
    await update_categories_keyboard(callback.message, [])

@dp.callback_query(F.data == "finish_selection", CanHelpStates.waiting_for_categories)
async def finish_selection(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    selected = data.get("selected_categories", [])
    if not selected:
        await callback.message.answer("⚠️ Выберите хотя бы одну категорию!", show_alert=True)
        return
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    db.save_user(user_id, username, "master", selected)
    invite_link = os.getenv("GROUP_INVITE_LINK")
    selected_names = ", ".join([CATEGORIES[c] for c in selected])
    if invite_link:
        await callback.message.edit_text(f"✅ Вы зарегистрированы как мастер!\n\n📌 Категории: {selected_names}\n\n👉 Вступите в группу мастеров:\n{invite_link}", reply_markup=get_master_menu())
    else:
        await callback.message.edit_text(f"✅ Вы зарегистрированы как мастер!\n\n📌 Категории: {selected_names}\n\n⚠️ Ссылка не настроена. Попросите админа добавить вас.", reply_markup=get_master_menu())
    await state.clear()

@dp.callback_query()
async def catch_all(callback: types.CallbackQuery):
    await callback.answer("Кнопка неактивна", show_alert=True)

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
