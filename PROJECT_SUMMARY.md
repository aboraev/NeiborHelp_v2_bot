# ВЫЖИМКА: Бот взаимопомощи ЖК "Соседи Помогают"
# Рабочее состояние на 2026-11-13

## ПРАВИЛО ДЛЯ AI
Предлагай правки в код ТОЛЬКО после фразы "теперь правь".
До этого — только диагностика и вопросы.

## СТЕК
Python + pyTelegramBotAPI (telebot) + SQLite. Хостинг: Termux (Android).
Репозиторий: NeiborHelp_v2_bot (branch main).

## ФАЙЛЫ
- bot.py — логика бота (~600 строк)
- database.py — класс Database, обёртка над функциями
- neighbors_bot.db — база данных

## СХЕМА БД (индексы критичны!)
users: 0=id, 1=user_id, 2=username, 3=role, 4=categories(json), 5=rating, 6=rating_count
requests: 0=id, 1=user_id, 2=username, 3=text, 4=category, 5=subcategory, 6=status, 7=master_id, 8=master_username

## КРИТИЧЕСКИЕ РЕШЕНИЯ (НЕ ОТКАТЫВАТЬ)
1. SQLite: соединение создаётся ВНУТРИ каждой функции, check_same_thread=False
2. НЕТ user_states.pop ПЕРЕД проверкой состояния (ломало кнопки)
3. bot.answer_callback_query(call.id) в конце КАЖДОГО callback-обработчика
4. catch_all УДАЛЁН (перехватывал все кнопки)

## НАВИГАЦИЯ
- home -> корневое меню get_main_menu()
- back -> умный возврат на шаг по user_states[state]
- Кнопка "Главное меню" есть везде, кроме самого главного меню
- Зарегистрированный мастер видит: Сменить категории / Отписаться / Назад / Главное меню

## СОСТОЯНИЯ user_states
waiting_for_category, waiting_for_subcategory, waiting_for_text,
waiting_for_time, waiting_for_contact, waiting_for_categories

## СТАТУС
Бот запускается. Навигация, категории, подкатегории, меню мастера работают.
## TODO
Проверить: кнопки времени, ввод контакта, полный цикл заявки, оценки.

## РАЗВЁРТЫВАНИЕ С НУЛЯ
pkg install python git -y
pip install pyTelegramBotAPI
git clone <этот репозиторий>
cd NeiborHelp_v2_bot && cp bot.py database.py ~/
python ~/bot.py
