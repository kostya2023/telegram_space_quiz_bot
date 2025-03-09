import json
import os
import time
import logging
import re
from telebot import TeleBot, types
from dotenv import load_dotenv
from utils.database import (
    create_tables, add_user, delete_user_progress, get_question, check_answer,
    complete_question, add_user_progress, get_completed_questions, get_all_questions,
    get_my_info, add_to_top, get_top, delete_question, add_question, calculate_total_time, get_all_users
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s](%(asctime)s) - %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

admin_state = {}

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_API")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN", "").split(",") if id.strip()]
bot = TeleBot(BOT_TOKEN)

# Сообщения
messages = {
    "start": "🚀 **Добро пожаловать в космический квиз-бот!**\n\n🌌 Здесь вы сможете проверить свои знания о космосе и сразиться за место в топе. Используйте команду /help, чтобы узнать больше о возможностях бота.",
    "help": "📋 **Доступные команды:**\n\n"
            "▶️ /start\_quiz - Начать новую викторину\n"
            "📊 /stats - Посмотреть вашу статистику\n"
            "🎁 /get\_prize - Получить награду за прохождение\n"
            "👨💻 /author - Узнать об авторе бота\n"
            "🔧 /admin - Админ-панель (только для администраторов)",
    "prize_success": "🎉 **Поздравляем с завершением квиза!**\n\n"
                     "🌟 Вы успешно прошли все вопросы! Пока что награда — это ваша гордость и знания, но в будущем вас ждут сюрпризы. Попробуйте улучшить свой результат и занять первое место в топе! 🏆",
    "prize_failure": "❌ **Не все вопросы пройдены!**\n\n"
                     "📊 Выполнено: {}/{}\n"
                     "Продолжайте отвечать на вопросы, чтобы получить награду! 💪",
    "no_questions": "❌ **Вопросы не найдены!**\n\n"
                    "⚠️ Обратитесь к администратору за помощью. Контактные данные можно найти в разделе /author.",
    "author": "👨💻 **Разработчик бота:**\n\n"
              "• **ФИО:** Горшков Константин Алексеевич\n"
              "• **Telegram:** [@Kos000113](https://t.me/Kos000113)\n"
              "• **GitHub:** [kostya2023](https://github.com/kostya2023)\n"
              "• **Проект:** [space_quiz_bot](https://github.com/kostya2023/telegram_space_quiz_bot)",
    "stats": "📊 **Ваша статистика:**\n\n"
             "• Пройдено вопросов: {}\n"
             "• Общее время: {}\n"
             "• Место в топе: {}",
    "correct_answer": "✅ **Правильно!**\n\n"
                      "🎉 Вы справились! Переходим к следующему вопросу!",
    "incorrect_answer": "❌ **Неверно!**\n\n"
                        "😔 Попробуйте ещё раз или переходите к следующему вопросу.",
    "quiz_completed": "🎉 **Квиз завершён!**\n\n"
                      "⏱️ Ваше время: {} секунд\n"
                      "🏆 Ваш результат добавлен в топ!",
    "admin": {
        "access_denied": "⛔ **Доступ запрещён!**\n\n"
                         "Эта команда доступна только администраторам.",
        "panel": "🔧 **Админ-панель:**\n\n"
                 "Выберите действие:",
        "questions_list": "📚 **Список вопросов:**\n\n",
        "users_list": "👥 **Список пользователей:**\n\n",
        "top_users": "🏆 **Топ-10 пользователей:**\n\n",
        "question_deleted": "🗑️ **Вопрос успешно удалён!**",
        "question_added": "📝 **Вопрос успешно добавлен!**",
        "error": "❌ **Произошла ошибка!**\n\n"
                 "Пожалуйста, попробуйте ещё раз или свяжитесь с разработчиком.",
        "invalid_format": "⚠️ **Неверный формат данных!**\n\n"
                          "Пример правильного формата:\n"
                          "`Вопрос; вариант1; вариант2; вариант3; вариант4; правильный_ответ`",
        "add_question_instruction": "📝 **Добавление нового вопроса:**\n\n"
                                    "Введите вопрос в формате:\n"
                                    "`Вопрос; вариант1; вариант2; вариант3; вариант4; правильный_ответ`"
    }
}

# Состояния пользователей
user_attempts = {}  # Счетчик попыток для каждого пользователя
user_start_time = {}  # Время начала прохождения квиза

def log_action(action: str, user_id: int, details: str = ""):
    logging.info(f"ACTION: {action} | USER_ID: {user_id} | DETAILS: {details}")

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def format_time(seconds: int) -> str:
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes} мин {seconds} сек"

def send_question(chat_id, question, question_id, user_id, message_id=None):
    """
    Отправляет вопрос с вариантами ответов.
    """
    keyboard = types.InlineKeyboardMarkup()
    for idx, option in enumerate(question["options"]):
        keyboard.add(types.InlineKeyboardButton(option, callback_data=f"answer_{question_id}_{idx + 1}"))
    keyboard.add(types.InlineKeyboardButton("💡 Подсказка", callback_data=f"hint_{question_id}"))

    image_path = question.get("image_path")
    if not image_path or not os.path.exists(image_path):
        image_path = "imgs/photo_not_found.jpg"

    if message_id:
        try:
            bot.delete_message(chat_id, message_id)
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения: {e}")

    question_text = f"❓ Вопрос {question_id}: {question['question_text']}"

    with open(image_path, "rb") as photo:
        bot.send_photo(chat_id, photo, caption=question_text, reply_markup=keyboard, parse_mode="Markdown")

@bot.message_handler(commands=["start"])
def send_welcome(message):
    """
    Обработчик команды /start.
    """
    log_action("start", message.from_user.id)
    bot.send_message(message.chat.id, messages["start"], parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=["help"])
def show_help(message):
    """
    Обработчик команды /help.
    """
    log_action("help", message.from_user.id)
    bot.send_message(message.chat.id, messages["help"], parse_mode="Markdown")

@bot.message_handler(commands=["get_prize"])
def prize(message):
    """
    Обработчик команды /get_prize.
    """
    user_id = message.from_user.id
    completed = get_completed_questions(user_id)
    total_questions = len(get_all_questions())
    
    if len(completed) == total_questions and total_questions > 0:
        bot.send_message(message.chat.id, messages["prize_success"], parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, messages["prize_failure"].format(len(completed), total_questions), parse_mode="Markdown")

@bot.message_handler(commands=["start_quiz"])
def start_quiz(message):
    """
    Обработчик команды /start_quiz.
    """
    user_id = message.from_user.id
    log_action("start_quiz", user_id)
    
    delete_user_progress(user_id)
    add_user(user_id, message.from_user.username)
    
    question = get_question(1)
    if not question:
        bot.send_message(message.chat.id, messages["no_questions"], parse_mode="Markdown")
        return

    user_start_time[user_id] = int(time.time())
    add_user_progress(user_id, 1, start_time=user_start_time[user_id])
    send_question(message.chat.id, question, 1, user_id)

@bot.message_handler(commands=["author"])
def author(message):
    """
    Обработчик команды /author.
    """
    bot.send_message(
        message.chat.id,
        messages["author"],
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

@bot.message_handler(commands=["stats"])
def show_stats(message):
    """
    Обработчик команды /stats.
    """
    user_id = message.from_user.id
    stats = get_my_info(user_id)
    completed = get_completed_questions(user_id)
    
    total_time = stats["total_time"]
    formatted_time = format_time(total_time) if total_time != "Нет данных" else "Нет данных"
    
    bot.send_message(message.chat.id, messages["stats"].format(
        len(completed),
        formatted_time,
        stats["place"] if stats["place"] != "Нет данных" else "🚫"
    ), parse_mode="Markdown")

def generate_admin_menu():
    """
    Генерирует меню администратора.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📝 Управление вопросами", callback_data="admin_questions"),
        types.InlineKeyboardButton("👥 Пользователи", callback_data="admin_users"),
        types.InlineKeyboardButton("📊 Топ-10", callback_data="admin_stats"),
        types.InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")
    )
    return keyboard

@bot.message_handler(commands=["admin"])
def admin_panel(message):
    """
    Обработчик команды /admin.
    """
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, messages["admin"]["access_denied"], parse_mode="Markdown")
        return

    log_action("admin", message.from_user.id)
    bot.send_message(
        message.chat.id,
        messages["admin"]["panel"],
        parse_mode="Markdown",
        reply_markup=generate_admin_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    """
    Обработчик действий администратора.
    """
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, messages["admin"]["access_denied"])
        return

    action = call.data.split("_")[1]
    
    if action == "questions":
        questions = get_all_questions()
        keyboard = types.InlineKeyboardMarkup()
        for q in questions:
            keyboard.add(types.InlineKeyboardButton(
                f"❌ Вопрос {q['question_id']}: {q['question_text'][:20]}...",
                callback_data=f"delete_question_{q['question_id']}"
            ))
        keyboard.add(
            types.InlineKeyboardButton("➕ Добавить вопрос", callback_data="add_question"),
            types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=messages["admin"]["questions_list"],
            reply_markup=keyboard
        )
    
    elif action == "users":
        users = get_all_users()
        keyboard = types.InlineKeyboardMarkup()
        for user in users:
            keyboard.add(types.InlineKeyboardButton(
                f"👤 {user['username']} (ID: {user['tg_id']})",
                callback_data=f"user_detail_{user['tg_id']}"
            ))
        keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=messages["admin"]["users_list"],
            reply_markup=keyboard
        )
    
    elif action == "stats":
        top = get_top()
        text = messages["admin"]["top_users"]
        for place, data in top.items():
            text += f"{place}. {data['Name_user']} — {data['total_time']} сек\n"
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        )
    
    elif action == "back":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=messages["admin"]["panel"],
            reply_markup=generate_admin_menu()
        )
    
    elif action == "close":
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_question_"))
def delete_question_callback(call):
    """
    Обработчик удаления вопроса.
    """
    question_id = int(call.data.split("_")[2])
    if delete_question(question_id):
        bot.answer_callback_query(call.id, messages["admin"]["question_deleted"])
        handle_admin_actions(call)
    else:
        bot.answer_callback_query(call.id, messages["admin"]["error"])

@bot.callback_query_handler(func=lambda call: call.data == "add_question")
def ask_new_question(call):
    """
    Обработчик добавления нового вопроса.
    """
    admin_state[call.from_user.id] = "waiting_question"
    bot.send_message(
        call.message.chat.id,
        messages["admin"]["add_question_instruction"]
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "waiting_question")
def add_new_question(message):
    """
    Обработчик добавления нового вопроса.
    """
    try:
        data = message.text.split(";")
        if len(data) != 6:
            raise ValueError(messages["admin"]["invalid_format"])
        
        add_question(
            data[0].strip(),
            data[1].strip(),
            data[2].strip(),
            data[3].strip(),
            data[4].strip(),
            int(data[5].strip())
        )
        bot.send_message(message.chat.id, messages["admin"]["question_added"])
        admin_state[message.from_user.id] = None
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("answer_"))
def handle_answer(call):
    """
    Обработчик ответа на вопрос.
    """
    user_id = call.from_user.id
    _, current_q_id, selected_opt = call.data.split("_")
    current_q_id = int(current_q_id)
    selected_opt = int(selected_opt)

    is_correct = check_answer(current_q_id, selected_opt)

    if is_correct:
        # Если ответ правильный
        complete_question(user_id, current_q_id)
        
        # Получаем описание правильного ответа
        question = get_question(current_q_id)
        correct_answer_description = question.get("description", "Описание отсутствует.")
        
        # Отправляем сообщение с описанием
        bot.answer_callback_query(call.id, f"✅ Верно!\n\n{correct_answer_description}", show_alert=True)
        
        # Получаем следующий вопрос
        next_q = get_question(current_q_id + 1)
        
        if next_q:
            # Удаляем текущее сообщение и отправляем следующий вопрос
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_question(
                call.message.chat.id,
                next_q,
                current_q_id + 1,
                user_id
            )
            add_user_progress(user_id, current_q_id + 1, start_time=user_start_time[user_id])
        else:
            # Если это был последний вопрос, завершаем квиз
            total_time = calculate_total_time(user_id)
            if total_time is not None:
                # Проверяем, обновилось ли время в топе
                if add_to_top(user_id, call.from_user.username, total_time):
                    bot.send_message(
                        call.message.chat.id,
                        messages["quiz_completed"].format(total_time),
                        parse_mode="Markdown"
                    )
                else:
                    bot.send_message(
                        call.message.chat.id,
                        "🎉 Квиз пройден! У вас есть результат лучше, так что время не обновлено.",
                        parse_mode="Markdown"
                    )
    else:
        # Если ответ неправильный
        bot.answer_callback_query(call.id, "❌ Неверно!", show_alert=True)
        

@bot.callback_query_handler(func=lambda call: call.data.startswith("hint_"))
def show_hint(call):
    """
    Обработчик для отображения подсказки.
    """
    nahui, question_id = call.data.split("_")
    question_id = int(question_id)
    
    # Получаем вопрос и подсказку
    question = get_question(question_id)
    hint = question.get("hint", "Подсказка отсутствует.")
    
    # Отправляем подсказку как alert
    bot.answer_callback_query(call.id, f"💡 Подсказка:\n\n{hint}", show_alert=True)

if __name__ == "__main__":
    # Создание таблиц в базе данных, если они ещё не созданы
    create_tables()
    
    # Логирование запуска бота
    logging.info("Бот запущен...")
    
    # Запуск бесконечного цикла опроса серверов Telegram
    bot.infinity_polling()