import os
import random
import telebot
from telebot import types
from dotenv import load_dotenv
from database import Database

load_dotenv('/data/data/com.termux/files/home/.env')

BOT_TOKEN = os.getenv('BOT_TOKEN')
MASTERS_GROUP_ID_STR = os.getenv('MASTERS_GROUP_ID')
ADMIN_ID_STR = os.getenv('ADMIN_ID')

if not BOT_TOKEN or not MASTERS_GROUP_ID_STR or not ADMIN_ID_STR:
    print('Ошибка: проверьте переменные в .env!')
    exit()

MASTERS_GROUP_ID = int(MASTERS_GROUP_ID_STR)
ADMIN_ID = int(ADMIN_ID_STR)

bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

CATEGORIES = {
    'repair': 'Ремонт (сантехника, электрика, малярка, плитка)',
    'tech': 'Техника (компьютеры, телефоны, бытовая техника, ТВ)',
    'auto': 'Авто и транспорт (помощь с авто, перевозки, погрузка)',
    'home_services': 'Бытовые услуги (уборка, выпечка, стирка, магазин)',
    'consult': 'Консультации (юрист, бухгалтер, репетитор, карьера)',
    'it': 'IT услуги (сайты, боты, настройка ПК, Wi-Fi)',
    'pets': 'Животные и растения (выгул, передержка, полив)',
    'other': 'Другое'
}

STATUS_EMOJI = {
    'new': 'Новая',
    'accepted': 'Принята',
    'in_progress': 'В работе',
    'done': 'Выполнена',
    'cancelled': 'Отменена'
}

SPAM_WORDS = ['заработок', 'крипто', 'инвестиции', 'казино', 'бесплатно', 'акция', 'скидка', 'заработай', 'доход']
captcha_answers = {}
user_states = {}

def get_customer_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton('Создать заявку', callback_data='need_help'),
        types.InlineKeyboardButton('Мои заявки', callback_data='my_requests'),
        types.InlineKeyboardButton('Как это работает', callback_data='info')
    )
    return markup

def get_master_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton('Мои заказы', callback_data='my_orders'),
        types.InlineKeyboardButton('Изменить категории', callback_data='can_help'),
        types.InlineKeyboardButton('Как это работает', callback_data='info')
    )
    return markup

def get_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton('Мне нужна помощь', callback_data='need_help'),
        types.InlineKeyboardButton('Я могу помочь', callback_data='can_help'),
        types.InlineKeyboardButton('Мои заявки', callback_data='my_requests'),
        types.InlineKeyboardButton('Как это работает', callback_data='info')
    )
    return markup

def generate_captcha():
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    correct = a + b
    options = [correct - 1, correct, correct + 1]
    random.shuffle(options)
    question = 'Сколько будет ' + str(a) + ' + ' + str(b) + '?'
    return question, correct, options
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    question, correct, options = generate_captcha()
    captcha_answers[user_id] = {'correct': correct, 'attempts': 0}
    markup = types.InlineKeyboardMarkup()
    for opt in options:
        markup.add(types.InlineKeyboardButton(text=str(opt), callback_data='captcha_' + str(opt)))
    text = 'Привет! Подтверди, что ты не бот.\n\n' + question
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('captcha_'))
def process_captcha(call):
    user_id = call.from_user.id
    answer = int(call.data.split('_')[1])
    if user_id not in captcha_answers:
        bot.send_message(call.message.chat.id, 'Капча устарела, напишите /start')
        return
    correct = captcha_answers[user_id]['correct']
    if answer == correct:
        captcha_answers[user_id] = 'passed'
        bot.edit_message_text('Капча пройдена!', call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, 'Что хотите сделать?', reply_markup=get_main_menu())
    else:
        captcha_answers[user_id]['attempts'] += 1
        if captcha_answers[user_id]['attempts'] >= 3:
            bot.send_message(call.message.chat.id, 'Слишком много попыток. Попробуйте позже.')
            captcha_answers.pop(user_id, None)
        else:
            q, c, opts = generate_captcha()
            captcha_answers[user_id]['correct'] = c
            markup = types.InlineKeyboardMarkup()
            for o in opts:
                markup.add(types.InlineKeyboardButton(text=str(o), callback_data='captcha_' + str(o)))
            text = 'Неверно. Ещё раз:\n\n' + q
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'info')
def show_info(call):
    text = 'Привет, сосед!\n\nЭто бот взаимопомощи нашего дома.\n\nНикаких комиссий. Вы договариваетесь напрямую.'
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_customer_menu())

@bot.message_handler(commands=['my'])
def cmd_my(message):
    show_my_requests(message, message.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data == 'my_requests')
def cb_my_requests(call):
    show_my_requests(call.message, call.from_user.id)

def show_my_requests(message, user_id):
    requests = db.get_requests_by_user(user_id)
    if not requests:
        bot.send_message(message.chat.id, 'У вас пока нет заявок.', reply_markup=get_customer_menu())
        return
    lines = ['Ваши заявки:\n']
    for req in requests:
        req_id = req[0]
        text = req[1]
        category = req[2]
        status = req[3]
        executor = req[4]
        status_emoji = STATUS_EMOJI.get(status, '?')
        cat_name = CATEGORIES.get(category, category)
        exec_info = ' | @' + str(executor) if executor else ''
        if len(text) > 50:
            short_text = text[:50] + '...'
        else:
            short_text = text
        lines.append('N' + str(req_id) + ' ' + status_emoji)
        lines.append('  ' + cat_name)
        lines.append('  ' + short_text + exec_info)
        lines.append('')
    result = '\n'.join(lines)
    bot.send_message(message.chat.id, result, reply_markup=get_customer_menu())
@bot.callback_query_handler(func=lambda call: call.data == 'need_help')
def process_need_help(call):
    user_states[call.from_user.id] = {'state': 'waiting_for_category'}
    markup = types.InlineKeyboardMarkup()
    for key, name in CATEGORIES.items():
        markup.add(types.InlineKeyboardButton(text=name, callback_data='cat_' + key))
    bot.edit_message_text('Выберите категорию:', call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
def process_category(call):
    user_id = call.from_user.id
    if user_states.get(user_id, {}).get('state') != 'waiting_for_category':
        return
    category = call.data.split('_', 1)[1]
    user_states[user_id] = {'state': 'waiting_for_text', 'category': category}
    cat_name = CATEGORIES.get(category, category)
    text = 'Опишите задачу (до 300 символов):\n\nКатегория: ' + cat_name
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('state') == 'waiting_for_text')
def process_text(message):
    text = message.text
    if len(text) > 300:
        bot.send_message(message.chat.id, 'Слишком длинно. Сократите до 300 символов.')
        return
    if 'http' in text.lower():
        bot.send_message(message.chat.id, 'Сообщение отклонено (ссылки запрещены).')
        return
    for word in SPAM_WORDS:
        if word in text.lower():
            bot.send_message(message.chat.id, 'Сообщение отклонено (похоже на спам).')
            return
    user_states[message.from_user.id]['text'] = text
    user_states[message.from_user.id]['state'] = 'waiting_for_timing'
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton('Срочно', callback_data='time_urgent'),
        types.InlineKeyboardButton('Укажу дату и время', callback_data='time_custom'),
        types.InlineKeyboardButton('Обговорю с соседом', callback_data='time_discuss')
    )
    bot.send_message(message.chat.id, 'Когда нужно выполнить задачу?', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['time_urgent', 'time_discuss', 'time_custom'])
def process_timing(call):
    user_id = call.from_user.id
    if user_states.get(user_id, {}).get('state') != 'waiting_for_timing':
        return
    if call.data == 'time_urgent':
        user_states[user_id]['timing'] = 'Срочно'
        user_states[user_id]['state'] = 'waiting_for_contact'
        ask_for_contact(call.message)
    elif call.data == 'time_discuss':
        user_states[user_id]['timing'] = 'Обговорю с соседом'
        user_states[user_id]['state'] = 'waiting_for_contact'
        ask_for_contact(call.message)
    else:
        user_states[user_id]['state'] = 'waiting_for_custom_time'
        bot.edit_message_text('Напишите дату и время (например: завтра в 18:00):', call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('state') == 'waiting_for_custom_time')
def process_custom_time(message):
    timing = message.text
    if len(timing) > 50:
        bot.send_message(message.chat.id, 'Слишком длинно. Напишите короче.')
        return
    user_states[message.from_user.id]['timing'] = timing
    user_states[message.from_user.id]['state'] = 'waiting_for_contact'
    ask_for_contact(message)

def ask_for_contact(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton('Поделиться контактом', request_contact=True))
    bot.send_message(message.chat.id, 'Поделитесь контактом Telegram:', reply_markup=markup)
@bot.message_handler(content_types=['contact'])
def process_contact(message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {})
    if state.get('state') != 'waiting_for_contact':
        return
    category = state.get('category')
    text = state.get('text')
    timing = state.get('timing', 'Не указано')
    if not category or not text:
        bot.send_message(message.chat.id, 'Ошибка. Напишите /start')
        user_states.pop(user_id, None)
        return
    request_id = db.save_request(user_id, message.from_user.username or message.from_user.first_name, text, category)
    cat_name = CATEGORIES.get(category, category)
    group_msg = 'Новая заявка N' + str(request_id) + '\n\nКатегория: ' + cat_name + '\nСрочность: ' + timing + '\nЗадача: ' + text
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton('Принять', callback_data='accept_' + str(request_id)),
        types.InlineKeyboardButton('Пропустить', callback_data='skip_' + str(request_id))
    )
    try:
        bot.send_message(MASTERS_GROUP_ID, group_msg, reply_markup=markup)
    except Exception as e:
        print('Ошибка отправки в группу: ' + str(e))
        bot.send_message(message.chat.id, 'Не удалось отправить заявку. Попробуйте позже.')
        user_states.pop(user_id, None)
        return
    bot.send_message(message.chat.id, 'Заявка N' + str(request_id) + ' передана мастерам.', reply_markup=types.ReplyKeyboardRemove())
    bot.send_message(message.chat.id, 'Что дальше?', reply_markup=get_customer_menu())
    user_states.pop(user_id, None)

@bot.callback_query_handler(func=lambda call: call.data == 'can_help')
def process_can_help(call):
    user_states[call.from_user.id] = {'state': 'waiting_for_categories', 'selected_categories': []}
    update_categories_keyboard(call.message, [])

def update_categories_keyboard(message, selected):
    markup = types.InlineKeyboardMarkup()
    cats = list(CATEGORIES.items())
    for i in range(0, len(cats), 2):
        row = []
        for j in range(2):
            idx = i + j
            if idx < len(cats):
                key, name = cats[idx]
                if key in selected:
                    label = 'X ' + name
                else:
                    label = 'O ' + name
                row.append(types.InlineKeyboardButton(text=label, callback_data='toggle_' + key))
        if row:
            markup.add(*row)
    markup.add(types.InlineKeyboardButton('Готово', callback_data='finish_selection'))
    if selected:
        markup.add(types.InlineKeyboardButton('Сбросить', callback_data='reset_selection'))
    names = [CATEGORIES.get(c, c) for c in selected]
    selected_text = ', '.join(names) if names else 'ничего'
    text = 'Выберите категории:\n\nВыбрано: ' + selected_text
    try:
        bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_category(call):
    user_id = call.from_user.id
    state = user_states.get(user_id, {})
    if state.get('state') != 'waiting_for_categories':
        return
    cat = call.data.replace('toggle_', '')
    selected = state.get('selected_categories', [])
    if cat in selected:
        selected.remove(cat)
    else:
        selected.append(cat)
    user_states[user_id]['selected_categories'] = selected
    update_categories_keyboard(call.message, selected)

@bot.callback_query_handler(func=lambda call: call.data == 'reset_selection')
def reset_selection(call):
    user_id = call.from_user.id
    if user_states.get(user_id, {}).get('state') != 'waiting_for_categories':
        return
    user_states[user_id]['selected_categories'] = []
    update_categories_keyboard(call.message, [])

@bot.callback_query_handler(func=lambda call: call.data == 'finish_selection')
def finish_selection(call):
    user_id = call.from_user.id
    state = user_states.get(user_id, {})
    if state.get('state') != 'waiting_for_categories':
        return
    selected = state.get('selected_categories', [])
    if not selected:
        bot.send_message(call.message.chat.id, 'Выберите хотя бы одну категорию!')
        return
    username = call.from_user.username or call.from_user.first_name
    db.save_user(user_id, username, 'master', selected)
    invite = os.getenv('GROUP_INVITE_LINK')
    names = [CATEGORIES.get(c, c) for c in selected]
    selected_text = ', '.join(names)
    if invite:
        msg = 'Вы зарегистрированы как мастер!\n\nКатегории: ' + selected_text + '\n\nВступите в группу:\n' + invite
    else:
        msg = 'Вы зарегистрированы как мастер!\n\nКатегории: ' + selected_text + '\n\nСсылка не настроена.'
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=get_master_menu())
    user_states.pop(user_id, None)
@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_'))
def process_accept(call):
    request_id = int(call.data.split('_')[1])
    master_id = call.from_user.id
    master_username = call.from_user.username or call.from_user.first_name
    request = db.get_request(request_id)
    if not request or request[5] != 'new':
        bot.send_message(call.message.chat.id, 'Этот заказ уже принят')
        return
    db.update_request_status(request_id, 'accepted', master_id, master_username)
    author_username = request[2]
    cat_name = CATEGORIES.get(request[4], request[4])
    new_text = 'Заказ N' + str(request_id) + ' принят @' + master_username + '\n\nКатегория: ' + cat_name + '\nЗадача: ' + request[3]
    bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, reply_markup=None)
    msg_to_master = 'Вы приняли заказ N' + str(request_id) + '.\n\nКатегория: ' + cat_name + '\nЗадача: ' + request[3] + '\n\nКонтакт заказчика: @' + author_username + '\n\nСвяжитесь с ним.'
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton('В работе', callback_data='progress_' + str(request_id)),
        types.InlineKeyboardButton('Отказаться', callback_data='cancel_after_' + str(request_id)),
        types.InlineKeyboardButton('Мои заказы', callback_data='my_orders')
    )
    try:
        bot.send_message(master_id, msg_to_master, reply_markup=markup)
    except Exception:
        pass
    try:
        bot.send_message(request[1], 'Мастер откликнулся на заявку N' + str(request_id) + '.')
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('skip_'))
def process_skip(call):
    request_id = int(call.data.split('_')[1])
    master_username = call.from_user.username or call.from_user.first_name
    current_text = call.message.text
    if 'Пропущено:' in current_text:
        new_text = current_text + ', @' + master_username
    else:
        new_text = current_text + '\n\nПропущено: @' + master_username
    try:
        bot.edit_message_text(new_text, call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('progress_'))
def process_progress(call):
    request_id = int(call.data.split('_')[1])
    master_id = call.from_user.id
    db.update_request_status(request_id, 'in_progress', master_id)
    request = db.get_request(request_id)
    try:
        bot.send_message(request[1], 'Мастер начал работу по заявке N' + str(request_id) + '.')
    except Exception:
        pass
    text = 'Заказ N' + str(request_id) + ' в работе.\n\nНажмите Выполнено когда закончите.'
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton('Выполнено', callback_data='done_' + str(request_id)),
        types.InlineKeyboardButton('Отказаться', callback_data='cancel_after_' + str(request_id))
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_after_'))
def process_cancel_after(call):
    request_id = int(call.data.split('_')[1])
    request = db.get_request(request_id)
    if not request or request[6] != call.from_user.id:
        bot.send_message(call.message.chat.id, 'Вы не принимали этот заказ')
        return
    user_states[call.from_user.id] = {'state': 'waiting_for_comment', 'cancel_request_id': request_id}
    text = 'Отказ от заказа N' + str(request_id) + '.\n\nНапишите причину (или Отмена):'
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Не отказываться', callback_data='cancel_cancel_' + str(request_id)))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_cancel_'))
def cancel_cancel(call):
    user_id = call.from_user.id
    user_states.pop(user_id, None)
    request_id = int(call.data.split('_')[2])
    request = db.get_request(request_id)
    cat_name = CATEGORIES.get(request[4], request[4])
    text = 'Заказ N' + str(request_id) + '.\n\nКатегория: ' + cat_name + '\nЗадача: ' + request[3] + '\n\nКонтакт: @' + request[2]
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton('В работе', callback_data='progress_' + str(request_id)),
        types.InlineKeyboardButton('Отказаться', callback_data='cancel_after_' + str(request_id))
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('state') == 'waiting_for_comment')
def process_cancel_comment(message):
    user_id = message.from_user.id
    state = user_states.get(user_id, {})
    request_id = state.get('cancel_request_id')
    comment = message.text
    request = db.get_request(request_id)
    if not request:
        bot.send_message(message.chat.id, 'Заявка не найдена')
        user_state