import os, random, telebot
from telebot import types
from dotenv import load_dotenv
from database import Database
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
try:
    import requests
    _old = requests.Session.merge_environment_settings
    def _new(self, url, proxies, stream, verify, cert):
        s = _old(self, url, proxies, stream, verify, cert)
        s['verify'] = False
        return s
    requests.Session.merge_environment_settings = _new
except Exception: pass

load_dotenv(os.path.expanduser('~/.env'))
BOT_TOKEN = os.getenv('BOT_TOKEN')
MASTERS_GROUP_ID = int(os.getenv('MASTERS_GROUP_ID'))
ADMIN_ID = int(os.getenv('ADMIN_ID'))
if not BOT_TOKEN or not MASTERS_GROUP_ID or not ADMIN_ID:
    print('Ошибка: проверьте .env!'); exit()

bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

CATEGORIES = {
    'repair': {'name': '🔧 Ремонт', 'sub': ['Сантехника', 'Электрика', 'Плитка', 'Малярка', 'Сборка мебели', 'Мелкий ремонт']},
    'tech': {'name': '💻 Техника', 'sub': ['Компьютеры', 'Телефоны', 'Бытовая техника', 'ТВ/Аудио', 'Настройка ПО']},
    'auto': {'name': '🚗 Авто', 'sub': ['Помощь с авто', 'Перевозки', 'Погрузка', 'Прикуривание', 'Совместные поездки']},
    'home_services': {'name': '🏠 Бытовые', 'sub': ['Уборка', 'Выпечка', 'Поход в магазин', 'Шитьё']},
    'consult': {'name': '📚 Консультации', 'sub': ['Юрист', 'Бухгалтер', 'Репетитор', 'Тренер', 'Помощь с детьми']},
    'it': {'name': '💡 IT', 'sub': ['Сайты', 'Боты', 'Настройка ПК', 'Wi-Fi/сети']},
    'pets': {'name': '🌿 Животные', 'sub': ['Выгул', 'Передержка', 'Груминг', 'Полив']},
    'other': {'name': '❓ Другое', 'sub': []}
}
STATUS_EMOJI = {'new': '🆕', 'accepted': '✅', 'in_progress': '⚙️', 'done': '✔️', 'cancelled': '❌', 'archived': '📦'}
SPAM_WORDS = ['заработок', 'крипто', 'инвестиции', 'казино', 'бесплатно', 'акция']
captcha_answers = {}
user_states = {}

def safe_edit(call, text, markup=None):
    try: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception as e:
        if 'not modified' not in str(e): print('Edit err:', e)

def get_main_menu():
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton('🆘 Мне нужна помощь', callback_data='need_help'))
    m.add(types.InlineKeyboardButton('🛠️ Я могу помочь', callback_data='master_settings'))
    m.add(types.InlineKeyboardButton('📋 Мои заявки', callback_data='my_requests_menu'))
    m.add(types.InlineKeyboardButton('ℹ️ Инфо', callback_data='info'))
    return m

def get_master_settings_menu(user):
    m = types.InlineKeyboardMarkup(row_width=1)
    if user and user['role'] == 'master':
        m.add(types.InlineKeyboardButton('⚙️ Изменить категории', callback_data='edit_cats'))
        m.add(types.InlineKeyboardButton('🚫 Отписаться от мастеров', callback_data='unsubscribe_master'))
    else:
        m.add(types.InlineKeyboardButton('🚀 Стать мастером', callback_data='edit_cats'))
    m.add(types.InlineKeyboardButton('🆘 Мне нужна помощь', callback_data='need_help'))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='home'))
    return m

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user = db.get_user(message.from_user.id)
    if user and user.get('is_verified'):
        bot.send_message(message.chat.id, 'С возвращением!', reply_markup=get_main_menu())
        return
    a, b = random.randint(1, 10), random.randint(1, 10)
    correct = a + b
    opts = sorted([correct - 1, correct, correct + 1], key=lambda x: random.random())
    captcha_answers[message.from_user.id] = {'correct': correct, 'attempts': 0}
    m = types.InlineKeyboardMarkup()
    for o in opts: m.add(types.InlineKeyboardButton(str(o), callback_data='captcha_' + str(o)))
    bot.send_message(message.chat.id, 'Привет! Подтверди, что ты не бот.\n\nСколько будет ' + str(a) + ' + ' + str(b) + '?', reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data.startswith('captcha_'))
def process_captcha(call):
    uid = call.from_user.id
    if uid not in captcha_answers:
        bot.answer_callback_query(call.id, 'Капча устарела, /start'); return
    ans = int(call.data.split('_')[1])
    if ans == captcha_answers[uid]['correct']:
        db.verify_user(uid)
        if not db.get_user(uid): db.save_user(uid, call.from_user.username or call.from_user.first_name, 'customer', [])
        safe_edit(call, '✅ Капча пройдена!')
        bot.send_message(call.message.chat.id, 'Добро пожаловать!', reply_markup=get_main_menu())
        del captcha_answers[uid]
    else:
        captcha_answers[uid]['attempts'] += 1
        if captcha_answers[uid]['attempts'] >= 3:
            bot.send_message(call.message.chat.id, 'Много ошибок, попробуйте позже'); del captcha_answers[uid]
        else: bot.send_message(call.message.chat.id, 'Неверно, ещё раз')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'home')
def process_home(call):
    user_states.pop(call.from_user.id, None)
    bot.send_message(call.message.chat.id, '.', reply_markup=types.ReplyKeyboardRemove())
    safe_edit(call, '🏠 Главная', get_main_menu())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'info')
def show_info(call):
    t = '🏘️ Сервис взаимопомощи соседей.\n\n1️⃣ Создайте заявку\n2️⃣ Мастера увидят её в группе\n3️⃣ Первый откликнувшийся получает ваш контакт\n4️⃣ Оцените работу после выполнения\n\n⚠️ Максимум 3 активные заявки.'
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='home'))
    safe_edit(call, t, m)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'need_help')
def need_help(call):
    user_states[call.from_user.id] = {'state': 'waiting_for_category'}
    m = types.InlineKeyboardMarkup(row_width=1)
    for k, v in CATEGORIES.items(): m.add(types.InlineKeyboardButton(v['name'], callback_data='cat_' + k))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='home'))
    safe_edit(call, '📝 Выберите категорию:', m)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('cat_'))
def pick_cat(call):
    uid = call.from_user.id
    if user_states.get(uid, {}).get('state') != 'waiting_for_category':
        bot.answer_callback_query(call.id); return
    cat = call.data.split('_', 1)[1]
    subs = CATEGORIES[cat]['sub']
    if not subs:
        user_states[uid] = {'state': 'waiting_for_text', 'category': cat, 'subcategory': 'Другое'}
        safe_edit(call, '📝 Опишите задачу (до 300 символов):\nКатегория: ' + CATEGORIES[cat]['name'])
    else:
        user_states[uid] = {'state': 'waiting_for_subcategory', 'category': cat}
        m = types.InlineKeyboardMarkup(row_width=1)
        for s in subs: m.add(types.InlineKeyboardButton(s, callback_data='sub_' + cat + '_' + s))
        m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='need_help'))
        safe_edit(call, '📝 ' + CATEGORIES[cat]['name'] + '\nВыберите подкатегорию:', m)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('sub_'))
def pick_sub(call):
    uid = call.from_user.id
    if user_states.get(uid, {}).get('state') != 'waiting_for_subcategory':
        bot.answer_callback_query(call.id); return
    parts = call.data.split('_', 2)
    user_states[uid] = {'state': 'waiting_for_text', 'category': parts[1], 'subcategory': parts[2]}
    safe_edit(call, '📝 Опишите задачу (до 300 символов):\n' + CATEGORIES[parts[1]]['name'] + ' - ' + parts[2])
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('state') == 'waiting_for_text')
def get_text(message):
    if len(message.text) > 300:
        bot.send_message(message.chat.id, '⚠️ Максимум 300 символов.'); return
    if 'http' in message.text.lower() or any(w in message.text.lower() for w in SPAM_WORDS):
        bot.send_message(message.chat.id, '❌ Ссылки и спам запрещены.'); return
    user_states[message.from_user.id].update({'text': message.text, 'state': 'waiting_for_timing'})
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton('⚡ Срочно', callback_data='time_urgent'))
    m.add(types.InlineKeyboardButton('📅 Укажу время', callback_data='time_custom'))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_text'))
    bot.send_message(message.chat.id, '⏰ Когда нужно выполнить?', reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == 'back_to_text')
def back_to_text(call):
    user_states[call.from_user.id]['state'] = 'waiting_for_text'
    bot.send_message(call.message.chat.id, '✏️ Напишите новый текст задачи:')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data in ['time_urgent', 'time_custom'])
def pick_time(call):
    uid = call.from_user.id
    if user_states.get(uid, {}).get('state') != 'waiting_for_timing':
        bot.answer_callback_query(call.id); return
    if call.data == 'time_urgent':
        user_states[uid].update({'timing': '⚡ Срочно', 'state': 'waiting_for_contact'})
        ask_contact(call.message)
    else:
        user_states[uid]['state'] = 'waiting_for_custom_time'
        safe_edit(call, '📅 Напишите дату и время (например: завтра в 18:00):')
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('state') == 'waiting_for_custom_time')
def get_custom_time(message):
    if len(message.text) > 50:
        bot.send_message(message.chat.id, '⚠️ Слишком длинно.'); return
    user_states[message.from_user.id].update({'timing': '📅 ' + message.text, 'state': 'waiting_for_contact'})
    ask_contact(message)

def ask_contact(message):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    m.add(types.KeyboardButton('📱 Поделиться контактом', request_contact=True))
    m.add(types.KeyboardButton('◀️ Назад'))
    bot.send_message(message.chat.id, '📱 Поделитесь контактом для связи с мастером:', reply_markup=m)

@bot.message_handler(func=lambda m: m.text == '◀️ Назад' and user_states.get(m.from_user.id, {}).get('state') == 'waiting_for_contact')
def back_from_contact(message):
    user_states[message.from_user.id]['state'] = 'waiting_for_timing'
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton('⚡ Срочно', callback_data='time_urgent'))
    m.add(types.InlineKeyboardButton('📅 Укажу время', callback_data='time_custom'))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='back_to_text'))
    bot.send_message(message.chat.id, '⏰ Когда нужно выполнить?', reply_markup=types.ReplyKeyboardRemove())
    bot.send_message(message.chat.id, 'Выберите время:', reply_markup=m)

@bot.message_handler(content_types=['contact'])
def get_contact(message):
    uid = message.from_user.id
    state = user_states.get(uid, {})
    if state.get('state') != 'waiting_for_contact': return
    contact = message.contact.phone_number if message.contact else None
    active = sum(1 for r in db.get_requests_by_user(uid) if r['status'] in ['new', 'accepted', 'in_progress'])
    if active >= 3:
        bot.send_message(message.chat.id, '⚠️ У вас уже 3 активные заявки.', reply_markup=types.ReplyKeyboardRemove())
        user_states.pop(uid, None); return
    rid = db.save_request(uid, message.from_user.username or message.from_user.first_name,
                          state['text'], state['category'], state['subcategory'], state.get('timing', 'Не указано'), contact)
    cat_name = CATEGORIES.get(state['category'], {}).get('name', state['category'])
    gm = '🆕 Заявка №' + str(rid) + '\n📂 ' + cat_name + ' (' + state['subcategory'] + ')\n⏰ ' + state.get('timing', 'Не указано') + '\n📝 ' + state['text']
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton('✅ Принять', callback_data='accept_' + str(rid)))
    m.add(types.InlineKeyboardButton('⏭️ Пропустить', callback_data='skip_' + str(rid)))
    try: bot.send_message(MASTERS_GROUP_ID, gm, reply_markup=m)
    except Exception as e: print('Group err:', e)
    bot.send_message(message.chat.id, '✅ Заявка №' + str(rid) + ' передана мастерам!', reply_markup=types.ReplyKeyboardRemove())
    bot.send_message(message.chat.id, 'Что дальше?', reply_markup=get_main_menu())
    user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data == 'my_requests_menu')
def my_req_menu(call):
    db.archive_old_requests()
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton('🟢 Активные', callback_data='my_req_active'))
    m.add(types.InlineKeyboardButton('⚪ Архив', callback_data='my_req_archive'))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='home'))
    safe_edit(call, '📋 Выберите раздел:', m)
    bot.answer_callback_query(call.id)

def build_requests_view(uid, statuses):
    cust = [r for r in db.get_requests_by_user(uid) if r['status'] in statuses]
    mast = [r for r in db.get_requests_by_master(uid) if r['status'] in statuses]
    lines, m = [], types.InlineKeyboardMarkup(row_width=2)
    if cust:
        lines.append('🔹 ВЫ ЗАКАЗЧИК:')
        for r in cust:
            cn = CATEGORIES.get(r['category'], {}).get('name', r['category'])
            lines.append(STATUS_EMOJI.get(r['status'], '❓') + ' №' + str(r['id']) + ' | ' + cn + ' | ' + r['text'][:30])
            if r['status'] == 'new':
                m.add(types.InlineKeyboardButton('✏️ Редактировать ' + str(r['id']), callback_data='edit_req_' + str(r['id'])),
                      types.InlineKeyboardButton('❌ Отменить ' + str(r['id']), callback_data='cancel_req_' + str(r['id'])))
            elif r['status'] == 'accepted':
                m.add(types.InlineKeyboardButton('❌ Отменить ' + str(r['id']), callback_data='cancel_req_' + str(r['id'])))
    if mast:
        lines.append('\n🔹 ВЫ МАСТЕР:')
        for r in mast:
            cn = CATEGORIES.get(r['category'], {}).get('name', r['category'])
            lines.append(STATUS_EMOJI.get(r['status'], '❓') + ' №' + str(r['id']) + ' | ' + cn + ' | ' + r['text'][:30])
            if r['status'] == 'accepted':
                m.add(types.InlineKeyboardButton('⚙️ В работу ' + str(r['id']), callback_data='progress_' + str(r['id'])),
                      types.InlineKeyboardButton('❌ Отказаться ' + str(r['id']), callback_data='cancel_after_' + str(r['id'])))
            elif r['status'] == 'in_progress':
                m.add(types.InlineKeyboardButton('✔️ Готово ' + str(r['id']), callback_data='confirm_done_' + str(r['id'])),
                      types.InlineKeyboardButton('❌ Отказаться ' + str(r['id']), callback_data='cancel_after_' + str(r['id'])))
    if not lines: return '📭 Пусто', None
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='my_requests_menu'))
    m.add(types.InlineKeyboardButton('🏠 Главная', callback_data='home'))
    return '\n'.join(lines), m

@bot.callback_query_handler(func=lambda c: c.data in ['my_req_active', 'my_req_archive'])
def show_req_list(call):
    st = ['new', 'accepted', 'in_progress'] if call.data == 'my_req_active' else ['done', 'cancelled', 'archived']
    text, m = build_requests_view(call.from_user.id, st)
    safe_edit(call, text, m)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'master_settings')
def master_settings(call):
    safe_edit(call, '🛠️ Я могу помочь', get_master_settings_menu(db.get_user(call.from_user.id)))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'unsubscribe_master')
def unsub_master(call):
    db.unsubscribe_master(call.from_user.id)
    safe_edit(call, '🚫 Вы отписаны от рассылок мастеров.', get_main_menu())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'edit_cats')
def edit_cats(call):
    user = db.get_user(call.from_user.id)
    sel = user.get('categories', []) if user and user['role'] == 'master' else []
    user_states[call.from_user.id] = {'state': 'waiting_for_categories', 'selected': sel}
    update_cats_keyboard(call.message, sel)
    bot.answer_callback_query(call.id)

def update_cats_keyboard(message, selected):
    m = types.InlineKeyboardMarkup(row_width=1)
    for k, v in CATEGORIES.items():
        label = '✅ ' + v['name'] if k in selected else '⭕ ' + v['name']
        m.add(types.InlineKeyboardButton(label, callback_data='toggle_' + k))
    m.add(types.InlineKeyboardButton('✔️ Готово', callback_data='finish_cats'))
    if selected: m.add(types.InlineKeyboardButton('🔄 Сбросить', callback_data='reset_cats'))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='master_settings'))
    names = ', '.join(CATEGORIES[c]['name'] for c in selected) if selected else 'ничего'
    t = '🛠️ Выберите категории:\nВыбрано: ' + names
    try: bot.edit_message_text(t, message.chat.id, message.message_id, reply_markup=m)
    except: bot.send_message(message.chat.id, t, reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data.startswith('toggle_'))
def toggle_cat(call):
    uid = call.from_user.id
    if user_states.get(uid, {}).get('state') != 'waiting_for_categories':
        bot.answer_callback_query(call.id); return
    cat = call.data.split('_', 1)[1]
    sel = user_states[uid]['selected']
    if cat in sel: sel.remove(cat)
    else: sel.append(cat)
    update_cats_keyboard(call.message, sel)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'reset_cats')
def reset_cats(call):
    uid = call.from_user.id
    if user_states.get(uid, {}).get('state') != 'waiting_for_categories':
        bot.answer_callback_query(call.id); return
    user_states[uid]['selected'] = []
    update_cats_keyboard(call.message, [])
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'finish_cats')
def finish_cats(call):
    uid = call.from_user.id
    state = user_states.get(uid, {})
    if state.get('state') != 'waiting_for_categories':
        bot.answer_callback_query(call.id); return
    sel = state.get('selected', [])
    if not sel:
        bot.send_message(call.message.chat.id, '⚠️ Выберите хотя бы одну категорию!')
        bot.answer_callback_query(call.id); return
    db.save_user(uid, call.from_user.username or call.from_user.first_name, 'master', sel)
    safe_edit(call, '✅ Вы зарегистрированы как мастер!', get_main_menu())
    user_states.pop(uid, None)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('accept_'))
def accept_req(call):
    rid = int(call.data.split('_')[1])
    mid = call.from_user.id
    mun = call.from_user.username or call.from_user.first_name
    active = sum(1 for r in db.get_requests_by_master(mid) if r['status'] in ['accepted', 'in_progress'])
    if active >= 3:
        bot.answer_callback_query(call.id, '⚠️ Лимит 3 активных заказа!'); return
    req = db.get_request(rid)
    if not req or req['status'] != 'new':
        bot.answer_callback_query(call.id, 'Уже неактивна'); return
    db.update_request_status(rid, 'accepted', mid, mun)
    try: bot.send_message(req['user_id'], '🔔 Вашу заявку №' + str(rid) + ' принял мастер @' + mun)
    except: pass
    cn = CATEGORIES.get(req['category'], {}).get('name', req['category'])
    msg = '🎉 Вы приняли заказ №' + str(rid) + '!\n📂 ' + cn + '\n📝 ' + req['text'] + '\n⏰ ' + str(req.get('timing', 'Не указано'))
    msg += '\n📞 Контакт: +' + str(req.get('contact', 'не указан'))
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton('⚙️ В работу', callback_data='progress_' + str(rid)))
    m.add(types.InlineKeyboardButton('❌ Отказаться', callback_data='cancel_after_' + str(rid)))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='home'))
    bot.send_message(mid, msg, reply_markup=m)
    try: bot.edit_message_text('✅ Заказ №' + str(rid) + ' принят @' + mun, call.message.chat.id, call.message.message_id, reply_markup=None)
    except: pass
    bot.answer_callback_query(call.id, 'Заказ принят!')

@bot.callback_query_handler(func=lambda c: c.data.startswith('progress_'))
def progress_req(call):
    rid = int(call.data.split('_')[1])
    db.update_request_status(rid, 'in_progress')
    req = db.get_request(rid)
    try: bot.send_message(req['user_id'], '🔔 Мастер приступил к заявке №' + str(rid))
    except: pass
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton('✔️ Готово', callback_data='confirm_done_' + str(rid)))
    m.add(types.InlineKeyboardButton('❌ Отказаться', callback_data='cancel_after_' + str(rid)))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='home'))
    safe_edit(call, '⚙️ Заказ №' + str(rid) + ' в работе.', m)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('confirm_done_'))
def confirm_done(call):
    rid = int(call.data.split('_')[2])
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton('✅ Да, завершить', callback_data='do_done_' + str(rid)))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='progress_' + str(rid)))
    safe_edit(call, '⚠️ Уверены, что работа выполнена?', m)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('do_done_'))
def do_done(call):
    rid = int(call.data.split('_')[2])
    db.update_request_status(rid, 'done')
    req = db.get_request(rid)
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton('⭐ Отлично (5)', callback_data='rate_5_' + str(rid)))
    m.add(types.InlineKeyboardButton('👎 Плохо (1)', callback_data='rate_1_' + str(rid)))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='home'))
    try: bot.send_message(req['user_id'], '🎉 Заказ №' + str(rid) + ' выполнен! Оцените мастера:', reply_markup=m)
    except: pass
    safe_edit(call, '✔️ Заказ №' + str(rid) + ' завершён!', get_main_menu())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('rate_'))
def rate_req(call):
    p = call.data.split('_')
    req = db.get_request(int(p[2]))
    if req and req.get('master_id'): db.update_rating(req['master_id'], int(p[1]))
    safe_edit(call, 'Спасибо за оценку! 🤝', get_main_menu())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('cancel_after_'))
def cancel_after(call):
    rid = int(call.data.split('_')[2])
    user_states[call.from_user.id] = {'state': 'waiting_for_comment', 'rid': rid}
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='progress_' + str(rid)))
    safe_edit(call, '⚠️ Напишите причину отказа:', m)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('state') == 'waiting_for_comment')
def get_cancel_comment(message):
    uid = message.from_user.id
    rid = user_states[uid]['rid']
    req = db.get_request(rid)
    db.update_request_status(rid, 'new', None, None)
    mun = message.from_user.username or message.from_user.first_name
    cn = CATEGORIES.get(req['category'], {}).get('name', req['category'])
    gm = '🔄 Заявка №' + str(rid) + ' снова доступна!\n📂 ' + cn + '\n📝 ' + req['text'] + '\n⚠️ Отказ от @' + mun + ': ' + message.text
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton('✅ Принять', callback_data='accept_' + str(rid)))
    m.add(types.InlineKeyboardButton('⏭️ Пропустить', callback_data='skip_' + str(rid)))
    try: bot.send_message(MASTERS_GROUP_ID, gm, reply_markup=m)
    except: pass
    try: bot.send_message(req['user_id'], '⚠️ Мастер отказался от заявки №' + str(rid) + '. Она снова в поиске.')
    except: pass
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton('🏠 Главная', callback_data='home'))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='my_req_active'))
    bot.send_message(message.chat.id, '✅ Заявка возвращена в пул.', reply_markup=m)
    user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith('cancel_req_'))
def cancel_req_customer(call):
    rid = int(call.data.split('_')[2])
    req = db.get_request(rid)
    if not req or req['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, 'Не ваша заявка'); return
    if req['status'] not in ['new', 'accepted']:
        bot.answer_callback_query(call.id, 'Нельзя отменить'); return
    user_states[call.from_user.id] = {'state': 'waiting_for_cancel_comment', 'rid': rid}
    safe_edit(call, '⚠️ Напишите причину отмены заявки №' + str(rid) + ':')
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('state') == 'waiting_for_cancel_comment')
def get_cancel_comment_customer(message):
    uid = message.from_user.id
    rid = user_states[uid]['rid']
    req = db.get_request(rid)
    db.update_request_status(rid, 'cancelled', None, None)
    if req.get('master_id'):
        try: bot.send_message(req['master_id'], '⚠️ Заказчик отменил заявку №' + str(rid) + '. Причина: ' + message.text)
        except: pass
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton('🏠 Главная', callback_data='home'))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='my_req_active'))
    bot.send_message(message.chat.id, '❌ Заявка №' + str(rid) + ' отменена.', reply_markup=m)
    user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith('do_cancel_'))
def do_cancel(call):
    rid = int(call.data.split('_')[2])
    req = db.get_request(rid)
    db.update_request_status(rid, 'cancelled', None, None)
    if req.get('master_id'):
        try: bot.send_message(req['master_id'], '⚠️ Заказчик отменил заявку №' + str(rid))
        except: pass
    safe_edit(call, '❌ Заявка №' + str(rid) + ' отменена.', get_main_menu())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('edit_req_'))
def edit_req(call):
    rid = int(call.data.split('_')[2])
    req = db.get_request(rid)
    if not req or req['user_id'] != call.from_user.id:
        bot.answer_callback_query(call.id, 'Не ваша'); return
    if req['status'] != 'new':
        bot.answer_callback_query(call.id, 'Только новые заявки'); return
    user_states[call.from_user.id] = {'state': 'editing_text', 'rid': rid}
    safe_edit(call, '✏️ Новый текст (до 300 символов):')
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('state') == 'editing_text')
def save_edited_text(message):
    uid = message.from_user.id
    rid = user_states[uid]['rid']
    if len(message.text) > 300:
        bot.send_message(message.chat.id, '⚠️ Длинно.'); return
    req = db.get_request(rid)
    db.update_request_text(rid, message.text)
    if req.get('master_id'):
        try: bot.send_message(req['master_id'], '⚠️ Заказчик изменил заявку №' + str(rid) + ':\n' + message.text)
        except: pass
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton('🏠 Главная', callback_data='home'))
    m.add(types.InlineKeyboardButton('◀️ Назад', callback_data='my_req_active'))
    bot.send_message(message.chat.id, '✅ Текст обновлён!', reply_markup=m)
    user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith('skip_'))
def skip_req(call):
    mun = call.from_user.username or call.from_user.first_name
    nt = call.message.text + '\n⏭️ Пропущено: @' + mun
    try: bot.edit_message_text(nt, call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup)
    except: pass
    bot.answer_callback_query(call.id, 'Пропущено')

@bot.callback_query_handler(func=lambda c: True)
def catch_all(call):
    bot.answer_callback_query(call.id, '⚠️ Кнопка неактивна')

print('🚀 Бот запущен!')
bot.infinity_polling()
