import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import sqlite3 as sq
from answers import true_answers

token = "TELEGRAM_BOT_API"
bot = telebot.TeleBot(token)
ADMIN_ID = [] # Telegram ID
user_answers = {}

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data

    try:
        if data.startswith("class_"):
            class_name = data.split("_")[1]
            bot.delete_message(chat_id=user_id, message_id=message_id)
            with get_db_connection() as con:
                cur = con.cursor()
                cur.execute("UPDATE users_data SET class = ? WHERE id = ?", (class_name, user_id))
                con.commit()
                msg = bot.send_message(call.message.chat.id, f"Ваш класс: {class_name}\nТеперь укажите вашего учителя")
                request_teacher(msg)
    except:
        print("Ошибка при обработке класса")

    try:
        if data.startswith("teacher_"):
            teacher_name = data.split("_")[1]
            bot.delete_message(chat_id=user_id, message_id=message_id)
            with get_db_connection() as con:
                cur = con.cursor()
                cur.execute("UPDATE users_data SET teacher = ? WHERE id = ?", (teacher_name, user_id))
                con.commit()
                bot.send_message(user_id, "Регистрация завершена!")
                show_main_menu(user_id)
    except:
        print("Ошибка при обработке учителя")

    try:
        if data == "profile":
            markup = InlineKeyboardMarkup()
            menu = InlineKeyboardButton(text="Назад в меню", callback_data='main_menu')
            markup.add(menu)

            with get_db_connection() as con:
                cur = con.cursor()
                cur.execute("SELECT fio, class, teacher FROM users_data WHERE id = ?", (user_id,))
                user = cur.fetchone()

                if user:
                    fio, class_name, teacher = user
                    profile_text = f"Ваш профиль:\n\nФИО: {fio}\nКласс: {class_name}\nУчитель: {teacher}"
                    bot.edit_message_text(chat_id=user_id, message_id=message_id, text=profile_text, reply_markup=markup)

                else:
                    bot.edit_message_text(chat_id=user_id, message_id=message_id, text="Вы не зарегистрированы\nПройти регистрацию: /start")
    except:
        print("Ошибка при обработке профиля")

    try:
        if data == "main_menu":
            markup = InlineKeyboardMarkup()
            answers = InlineKeyboardButton(text="Отправить ответы", callback_data='answers')
            profile = InlineKeyboardButton(text="Профиль", callback_data='profile')
            markup.add(answers, profile)
            bot.edit_message_text(chat_id=user_id, message_id=message_id, text="Главное меню", reply_markup=markup)
    except:
        print("Ошибка при обработке главного меню")

    try:
        if data.startswith("edit_"):
            question_index = int(call.data.split("_")[1]) - 1
            send_edit_answer_menu(user_id, question_index, message_id)
    except:
        print("Ошибка при обработке изменения ответа")

    try:
        if data.startswith("update_"):
            data = call.data.split("_")
            question_index = int(data[1])
            new_answer = data[2]

            true_answers[question_index + 1] = new_answer
            bot.answer_callback_query(call.id, f"Правильный ответ для вопроса {question_index + 1} изменён на: {new_answer}")

            bot.delete_message(user_id, message_id)
            edit_correct_answers(call.message)
    except:
        print("Ошибка при обработке обновлении ответа")

    try:
        if data == "menu_m":
            show_main_menu(user_id)
    except:
        print("Ошибка при отправлении главного меню после отправки ответов")

    try:
        if data == "cancel":
            send_answer_menu(user_id, message_id)
    except: None

    try:
        if data.startswith("question_"):
            question_index = int(data.split("_")[1]) - 1
            send_answers_menu(user_id, question_index, message_id)
    except: None

    try:
        if data.startswith("answer_"):
            _, question_index, answer = data.split("_")
            question_index = int(question_index)
            user_answers[user_id][question_index] = answer

            bot.answer_callback_query(call.id, f"Вы выбрали: {answer}")
            send_answer_menu(user_id, message_id)
    except: None

    try:
        if data == "send_answers":
            score = 0
            markup = InlineKeyboardMarkup()
            button = InlineKeyboardButton(text="Меню", callback_data='menu_m')
            markup.add(button)
            with get_db_connection() as con:
                cur = con.cursor()
                cur.execute("SELECT fio, class, teacher FROM users_data WHERE id = ?", (user_id,))
                user = cur.fetchone()

                if user:
                    fio, class_name, teacher = user
            result = []
            for i, answer in enumerate(user_answers[user_id]):
                correct_answer = true_answers.get(i + 1, None)
                if correct_answer:
                    if answer == correct_answer:
                        result.append(f"{i + 1}) {answer} ✅")
                        score += 1
                    else:
                        result.append(f"{i + 1}) {answer} ❌ {correct_answer}")
                else:
                    result.append(f"{i + 1}) {answer} - нет правильного ответа")
            for admin_id in ADMIN_ID:
                bot.send_message(admin_id, f"От: {fio}\nКласс: {class_name}\nУчитель: {teacher}\n\n" + "\n".join(result) + f"\n\nПравильно: {score}")
            bot.edit_message_text("Мы проверили ваши ответы, вот результат:\n\n" + '\n'.join(result) + f"\n\nПравильно: {score}", chat_id=user_id, message_id=message_id, reply_markup=markup)
            user_answers[user_id] = [" "] * 35
    except: None

    try:
        if data == "answers":
            send_answer_menu(user_id, message_id)
    except: None

def get_db_connection():
    return sq.connect("dates.db", check_same_thread=False)

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    users_id = message.chat.id
    user_answers[users_id] = [" "] * 35
    username = message.from_user.username or "NULL"

    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("SELECT fio, class, teacher FROM users_data WHERE id = ?", (user_id,))
        user = cur.fetchone()

        if not user:
            cur.execute("INSERT INTO users_data (id, username) VALUES (?, ?)", (user_id, username))
            con.commit()
            msg = bot.send_message(message.chat.id, "Добро пожаловать! Давайте зарегистрируемся.")
            request_fio(msg)

        else:
            show_main_menu(user_id)

@bot.message_handler(commands=['edit_answers'])
def edit_correct_answers(message):
    user_id = message.chat.id
    if user_id not in ADMIN_ID:
        return

    markup = InlineKeyboardMarkup()
    buttons = []
    for i in range(1, 36):
        buttons.append(
            InlineKeyboardButton(text=f"{i}) {true_answers.get(i, 'Не задан')}", callback_data=f"edit_{i}"))
    for i in range(0, len(buttons), 4):
        markup.row(*buttons[i:i + 4])
    markup.add(InlineKeyboardButton("Назад", callback_data="main_menu2"))

    bot.send_message(user_id, "Выберите вопрос для редактирования правильного ответа:", reply_markup=markup)

@bot.message_handler(commands=['add'])
def add_admin(message):
    if message.chat.id not in ADMIN_ID:
        return
    try:
        new_admin_id = int(message.text.split(" ")[1])

        if new_admin_id not in ADMIN_ID:
            ADMIN_ID.append(new_admin_id)
            bot.reply_to(message, f"Администратор с ID {new_admin_id} добавлен.")
        else:
            bot.reply_to(message, f"Администратор с ID {new_admin_id} уже существует.")
    except (IndexError, ValueError):
        bot.reply_to(message, "Пожалуйста, укажите ID администратора после команды /add.")

def request_fio(message):
    msg = bot.send_message(message.chat.id, "Введите ваше ФИО:")
    bot.register_next_step_handler(msg, save_fio, msg)

def save_fio(message, prev_message):
    fio = message.text.strip()
    user_id = message.from_user.id
    bot.delete_message(message.chat.id, prev_message.id)
    bot.delete_message(message.chat.id, message.id)

    with get_db_connection() as con:
        cur = con.cursor()
        cur.execute("UPDATE users_data SET fio = ? WHERE id = ?", (fio, user_id))
        con.commit()
        msg = bot.send_message(message.chat.id, "Теперь выберите ваш класс")
        request_class(msg)

def request_class(message):
    markup = InlineKeyboardMarkup()
    classes = ["Milliy", "1-A+", "1-A", "1-B", "1-C", "2", "3", "4"]
    for class_name in classes:
        markup.add(InlineKeyboardButton(text=class_name, callback_data=f"class_{class_name}"))
    bot.edit_message_text("Выберите ваш класс:", chat_id=message.chat.id, message_id=message.id, reply_markup=markup)

def request_teacher(message):
    markup = InlineKeyboardMarkup()
    teachers = ["Teacher1", "Teacher2", "Teacher3"]

    for teacher_name in teachers:
        markup.add(InlineKeyboardButton(text=teacher_name, callback_data=f"teacher_{teacher_name}"))

    bot.edit_message_text("Выберите учителя:", chat_id=message.chat.id, message_id=message.id, reply_markup=markup)

def show_main_menu(user_id):
    markup = InlineKeyboardMarkup()
    answers = InlineKeyboardButton(text="Отправить ответы", callback_data='answers')
    profile = InlineKeyboardButton(text="Профиль", callback_data='profile')
    markup.add(answers, profile)
    bot.send_message(user_id, "Главное меню", reply_markup=markup)

def edit_answers_call(user_id, message_id):
    if user_id != ADMIN_ID:
        return

    markup = InlineKeyboardMarkup()
    buttons = []
    for i in range(1, 36):
        buttons.append(InlineKeyboardButton(text=f"{i}) {true_answers.get(i, 'Не задан')}", callback_data=f"edit_correct_{i}"))
    for i in range(0, len(buttons), 4):
        markup.row(*buttons[i:i + 4])
    markup.add(InlineKeyboardButton("Назад", callback_data="main_menu"))

    bot.edit_message_text("Выберите вопрос для редактирования правильного ответа:", chat_id=user_id, message_id=message_id, reply_markup=markup)

def send_edit_answer_menu(user_id, question_index, message_id):
    markup = InlineKeyboardMarkup()
    for option in ["A", "B", "C", "D"]:
        markup.add(InlineKeyboardButton(option, callback_data=f"update_{question_index}_{option}"))
    markup.add(InlineKeyboardButton("Назад", callback_data="back_to_edit"))

    bot.edit_message_text(f"Выберите новый правильный ответ для вопроса {question_index + 1}:", chat_id=user_id, message_id=message_id, reply_markup=markup)

def send_answer_menu(user_id, message_id):
    markup = InlineKeyboardMarkup()
    buttons = []
    for i in range(1, 36):
        buttons.append(InlineKeyboardButton(text=f"{i}) {user_answers[user_id][i - 1]}", callback_data=f"question_{i}"))
    for i in range(0, len(buttons), 4):
        markup.row(*buttons[i:i + 4])
    markup.add(InlineKeyboardButton("Назад в меню", callback_data="main_menu"))
    markup.add(InlineKeyboardButton("✅Отправить✅", callback_data="send_answers"))

    if message_id:
        bot.edit_message_text("Выберите пункт для ответа:", chat_id=user_id, message_id=message_id, reply_markup=markup)

def send_answers_menu(user_id, question_index, message_id):
    markup = InlineKeyboardMarkup()
    for option in ["A", "B", "C", "D"]:
        markup.add(InlineKeyboardButton(option, callback_data=f"answer_{question_index}_{option}"))
    markup.add(InlineKeyboardButton("Назад", callback_data="cancel"))

    if message_id:
        bot.edit_message_text(f"Выберите вариант для пункта {question_index + 1}:", chat_id=user_id, message_id=message_id, reply_markup=markup)
    else: None

while True:
    try:
        bot.polling(none_stop=True)
    except:
        time.sleep(3)
