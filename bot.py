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
MASTERS_GROUP_ID_STR = os.getenv("MASTERS_GROUP_ID")
ADMIN_ID_STR = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise ValueError("❌ Переменная BOT_TOKEN не задана!")
if not MASTERS_GROUP_ID_STR:
    raise ValueError("❌ Переменная MASTERS_GROUP_ID не задана!")
if not ADMIN_ID_STR:
    raise ValueError("❌ Переменная ADMIN_ID не задана!")

MASTERS_GROUP_ID = int(MASTERS_GROUP_ID_STR)
ADMIN_ID = int(ADMIN_ID_STR)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()

# ========== ДВУХУРОВНЕВАЯ СТРУКТУРА КАТЕГОРИЙ ==========

MAIN_CATEGORIES = {
    "repair": {
        "name": "🏠 Ремонт и строительство",
        "subs": {
            "plumbing": "🚿 Сантехника",
            "electrical": "⚡ Электрика",
            "painting": "🎨 Малярка и обои",
            "tiling": "🔲 Плитка и полы",
            "small_repair": "🔨 Мелкий ремонт"
        }
    },
    "tech": {
        "name": "🔧 Техника и электроника",
        "subs": {
            "computers": "💻 Компьютеры и ноутбуки",
            "phones": "📱 Телефоны и планшеты",
            "large_appliance": "🧺 Крупная бытовая техника",
            "small_appliance": "🔌 Мелкая бытовая техника",
            "tv_audio": "📺 ТВ и аудио"
        }
    },
    "auto": {
        "name": "🚗 Авто и транспорт",
        "subs": {
            "car_help": "🚙 Помощь с авто",
            "delivery": "🚚 Перевозки и доставка",
            "loading": "📦 Погрузка/разгрузка"
        }
    },
    "home_services": {
        "name": "🍳 Бытовые услуги",
        "subs": {
            "cleaning": "🧹 Уборка квартир",
            "baking": "🥐 Выпечка и готовка",
            "laundry": "👕 Стирка и глажка",
            "shopping": "🛒 Поход в магазин/аптеку"
        }
    },
    "consult": {
        "name": "📚 Консультации и обучение",
        "subs": {
            "lawyer": "⚖️ Юридические консультации",
            "accountant": "📊 Бухгалтерия и налоги",
            "tutor": "🎓 Репетиторство",
            "career": "💼 Карьерные консультации"
        }
    },
    "it": {
        "name": "💻 IT и цифровые услуги",
        "subs": {
            "websites": "🌐 Сайты и лендинги",
            "bots": "🤖 Боты и автоматизация",
            "phone_setup": "📱 Настройка смартфонов",
            "pc_setup": "🖥️ Настройка компьютеров и ПО",
            "wifi_smart_home": "📡 Настройка Wi-Fi и умного дома"
        }
    },
    "pets": {
        "name": "🐾 Животные и растения",
        "subs": {
            "dog_walking": "🐕 Выгул собак",
            "pet_sitting": "🐱 Передержка животных",
            "plants": "🌱 Полив растений",
            "pet_grooming": "✂️ Стрижка животных"
        }
    },
    "other": {
        "name": "❓ Другое",
        "subs": {
            "other": "❓ Другое"
        }
    }
}

# Плоский словарь для быстрого поиска
ALL_SUBS = {}
for main_key, main_data in MAIN_CATEGORIES.items():
    for sub_key, sub_name in main_data["subs"].items():
        ALL_SUBS[sub_key] = sub_name

# ========== СОСТОЯНИЯ ==========

class NeedHelpStates(StatesGroup):
    waiting_for_main = State()
    waiting_for_sub = State()
    waiting_for_text = State()
    waiting_for_timing = State()
    waiting_for_custom_time = State()
    waiting_for_contact = State()

class CanHelpStates(StatesGroup):
    waiting_for_main = State()
    waiting_for_subs = State()

class MasterCancelStates(StatesGroup):
    waiting_for_comment = State()

STATUS_EMOJI = {
    "new": "🟡 Новая",
    "accepted": "🔵 Принята",
    "in_progress": "🟢 В работе",
    "done": "✅ Выполнена",
    "cancelled": "🔴 Отменена"
}

SPAM_WORDS = ["заработок", "крипто", "инвестиции", "казино", "бесплатно", "акция", "скидка", "перейди по ссылке", "заработай", "доход"]
captcha_answers = {}

# ========== МЕНЮ ==========

def get_customer_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать новую заявку", callback_data="need_help")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_requests")],
        [InlineKeyboardButton(text="ℹ️ Как это работает", callback_data="info")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])

def get_master_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton(text="🤝 Изменить категории", callback_data="can_help")],
        [InlineKeyboardButton(text="ℹ️ Как это работает", callback_data="info")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Мне нужна помощь", callback_data="need_help")],
        [InlineKeyboardButton(text="🤝 Я могу помочь", callback_data="can_help")],
        [InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_requests")],
        [InlineKeyboardButton(text="ℹ️ Как это работает", callback_data="info")]
    ])

# ========== КАПЧА И СТАРТ ==========

def generate_captcha():
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    correct = a + b
    options = [correct - 1, correct, correct + 1]
    random.shuffle(options)
    return f"Сколько будет {a} + {b}?", correct, options

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

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.delete()
    await show_main_menu(callback.message, "Что хотите сделать?")

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

# ========== ЗАЯВКИ ПОЛЬЗОВАТЕЛЯ ==========

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
        cat_name = ALL_SUBS.get(category, category)
        executor_info = f" | Исполнитель: @{executor}" if executor else ""
        lines.append(f"• №{req_id} {status_emoji}\n  📂 {cat_name}\n  📝 {text[:60]}{'...' if len(text) > 60 else ''}{executor_info}\n")
    result_text = "\n".join(lines)
    await message.answer(result_text, reply_markup=get_customer_menu(), parse_mode="HTML")

# ========== ЗАКАЗЧИК: СОЗДАНИЕ ЗАЯВКИ (ДВУХУРОВНЕВОЕ) ==========

@dp.callback_query(F.data == "need_help")
async def process_need_help(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(NeedHelpStates.waiting_for_main)
    
    # Основные категории в ОДИН столбец
    keyboard_rows = []
    for main_key, main_data in MAIN_CATEGORIES.items():
        keyboard_rows.append([InlineKeyboardButton(text=main_data["name"], callback_data=f"main_{main_key}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    await callback.message.edit_text("Выберите основное направление:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("main_"), NeedHelpStates.waiting_for_main)
async def process_main_category(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    main_cat_key = callback.data.split("_", 1)[1]
    await state.update_data(main_category=main_cat_key)
    await state.set_state(NeedHelpStates.waiting_for_sub)
    
    # Подкатегории в ОДИН столбец + кнопка Назад
    subcats = MAIN_CATEGORIES[main_cat_key]["subs"]
    keyboard_rows = []
    for sub_key, sub_name in subcats.items():
        keyboard_rows.append([InlineKeyboardButton(text=sub_name, callback_data=f"sub_{sub_key}")])
    
    keyboard_rows.append([InlineKeyboardButton(text="🔙 Назад к основным категориям", callback_data="back_to_main_cats")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    await callback.message.edit_text(f"Уточните категорию:\n\n📂 {MAIN_CATEGORIES[main_cat_key]['name']}", reply_markup=keyboard)

@dp.callback_query(F.data == "back_to_main_cats", NeedHelpStates.waiting_for_sub)
async def back_to_main_cats(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(NeedHelpStates.waiting_for_main)
    
    keyboard_rows = []
    for main_key, main_data in MAIN_CATEGORIES.items():
        keyboard_rows.append([InlineKeyboardButton(text=main_data["name"], callback_data=f"main_{main_key}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    await callback.message.edit_text("Выберите основное направление:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("sub_"), NeedHelpStates.waiting_for_sub)
async def process_subcategory(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    sub_cat_key = callback.data.split("_", 1)[1]
    await state.update_data(category=sub_cat_key)
    await state.set_state(NeedHelpStates.waiting_for_text)
    await callback.message.edit_text(f"Опишите задачу кратко (до 300 символов):\n\nКатегория: {ALL_SUBS[sub_cat_key]}")

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
        
        group_message = f"🆕 Новая заявка №{request_id}\n\n📂 Категория: {ALL_SUBS[category]}\n⏳ Срочность: {timing}\n📝 Задача: {text}"
        
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

# ========== МАСТЕР: РЕГИСТРАЦИЯ (ДВУХУРОВНЕВАЯ) ==========

@dp.callback_query(F.data == "can_help")
async def process_can_help(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CanHelpStates.waiting_for_main)
    await state.update_data(selected_main=[])
    await show_main_selection(callback.message, [])

async def show_main_selection(message: types.Message, selected: list):
    # Основные категории в ОДИН столбец
    keyboard_rows = []
    for main_key, main_data in MAIN_CATEGORIES.items():
        label = f"✅ {main_data['name']}" if main_key in selected else f"⬜ {main_data['name']}"
        keyboard_rows.append([InlineKeyboardButton(text=label, callback_data=f"toggle_main_{main_key}")])
    
    keyboard_rows.append([InlineKeyboardButton(text="➡️ Далее: выбрать подкатегории", callback_data="next_subs")])
    if selected:
        keyboard_rows.append([InlineKeyboardButton(text="❌ Сбросить всё", callback_data="reset_main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    selected_names = ", ".join([MAIN_CATEGORIES[c]["name"] for c in selected]) if selected else "ничего не выбрано"
    text = f"Выберите основные направления (можно несколько):\n\n📌 Выбрано: {selected_names}"
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except TelegramAPIError as e:
        if "message is not modified" not in str(e).lower():
            print(f"Ошибка редактирования: {e}")

@dp.callback_query(F.data.startswith("toggle_main_"), CanHelpStates.waiting_for_main)
async def toggle_main(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    category = callback.data.replace("toggle_main_", "")
    data = await state.get_data()
    selected = data.get("selected_main", [])
    if category in selected:
        selected.remove(category)
    else:
        selected.append(category)
    await state.update_data(selected_main=selected)
    await show_main_selection(callback.message, selected)

@dp.callback_query(F.data == "reset_main", CanHelpStates.waiting_for_main)
async def reset_main(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(selected_main=[])
    await show_main_selection(callback.message, [])

@dp.callback_query(F.data == "next_subs", CanHelpStates.waiting_for
