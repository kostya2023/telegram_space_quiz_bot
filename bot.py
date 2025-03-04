from utils import database
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
import time
import logging

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

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_API")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN", "").split(",") if id.strip()]
bot = telebot.TeleBot(BOT_TOKEN)

# Глобальные переменные
admin_state = {}

def log_action(action: str, user_id: int, details: str = ""):
    logging.info(f"ACTION: {action} | USER_ID: {user_id} | DETAILS: {details}")

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ------------ Основные команды ------------
@bot.message_handler(commands=["start"])
def send_welcome(message):
    log_action("start", message.from_user.id)
    text = (
        "🚀 *Добро пожаловать в квиз-бот!*\n\n"
        "Этот бот поможет вам проверить свои знания в увлекательной викторине. "
        "Вы можете начать квиз, посмотреть свою статистику и даже получить приз!\n\n"
        "Используйте команду /help, чтобы увидеть список доступных команд."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=["help"])
def show_help(message):
    log_action("help", message.from_user.id)
    text = (
        "📋 *Список команд:*\n\n"
        "▶️ /start\_quiz - Начать квиз\n"
        "📊 /stats - Ваша статистика\n"
        "🎁 /get\_prize - Получить приз\n"
        "👨‍💻 /author - Об авторе\n"
    )
    if is_admin(message.from_user.id):
        text += "🔧 /admin - Админ-панель\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=["get_prize"])
def prize(message):
    user_id = message.from_user.id
    completed = database.get_completed_questions(user_id)
    total_questions = len(database.get_all_questions())
    
    if len(completed) == total_questions and total_questions > 0:
        text = (
            "🎉 *Поздравляю с прохождением квиза!*\n\n"
            "Пока что я не придумал, какие подарки будут, "
            "так что наслаждайтесь своей победой! 🏆\n\n"
            "Попробуйте улучшить свой результат и выйти в топ! 🚀"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    else:
        bot.send_message(
            message.chat.id,
            f"❌ Для получения приза нужно пройти все вопросы!\n"
            f"Выполнено: {len(completed)}/{total_questions}",
            parse_mode="Markdown"
        )

@bot.message_handler(commands=["start_quiz"])
def start_quiz(message):
    user_id = message.from_user.id
    log_action("start_quiz", user_id)
    
    database.delete_user_progress(user_id)
    database.add_user(user_id, message.from_user.username)
    
    question = database.get_question(1)
    if not question:
        bot.send_message(message.chat.id, "❌ Вопросы не найдены!")
        return

    keyboard = InlineKeyboardMarkup()
    for idx, option in enumerate(question["options"]):
        keyboard.add(InlineKeyboardButton(option, callback_data=f"answer_1_{idx + 1}"))
    
    database.add_user_progress(user_id, 1, start_time=int(time.time()))
    bot.send_message(message.chat.id, question["question_text"], reply_markup=keyboard)

@bot.message_handler(commands=["author"])
def author(message):
    authors_text = (
        "👨‍💻 *Разработчик:*\n\n"
        "*ФИ*: Константин Горшков\n"
        "*Telegram*: @Kos000113\n"
        "*Почта*: kostya\_gorshkov\_06@vk\.com\n"
        "*GitHub*: [kostya2023](https://github\.com/kostya2023)\n\n"
        "🌐 *Репозиторий проекта:*\n"
        "[telegram\_space\_quiz\_bot](https://github\.com/kostya2023/telegram\_space\_quiz\_bot)"
    )
    
    bot.send_message(
        message.chat.id,
        authors_text,
        parse_mode="MarkdownV2",
        disable_web_page_preview=True
    )

@bot.message_handler(commands=["stats"])
def show_stats(message):
    user_id = message.from_user.id
    stats = database.get_my_info(user_id)
    completed = database.get_completed_questions(user_id)
    
    text = (
        f"📊 *Ваша статистика:*\n\n"
        f"• Пройдено вопросов: {len(completed)}\n"
        f"• Общее время: {stats['total_time']} сек\n"
        f"• Место в топе: {stats['place'] if stats['place'] != 'Не в топе' else '🚫'}"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ------------ Админ-панель ------------
def generate_admin_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📝 Управление вопросами", callback_data="admin_questions"),
        InlineKeyboardButton("👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton("📊 Топ-10", callback_data="admin_stats"),
        InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")
    )
    return keyboard

@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⛔ Доступ запрещен!")
        return

    log_action("admin", message.from_user.id)
    bot.send_message(
        message.chat.id,
        "🔧 *Админ-панель*",
        parse_mode="Markdown",
        reply_markup=generate_admin_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ Доступ запрещен!")
        return

    action = call.data.split("_")[1]
    
    if action == "questions":
        questions = database.get_all_questions()
        keyboard = InlineKeyboardMarkup()
        for q in questions:
            keyboard.add(InlineKeyboardButton(
                f"❌ Вопрос {q['question_id']}: {q['question_text'][:20]}...",
                callback_data=f"delete_question_{q['question_id']}"
            ))
        keyboard.add(
            InlineKeyboardButton("➕ Добавить вопрос", callback_data="add_question"),
            InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📚 Список вопросов:",
            reply_markup=keyboard
        )
    
    elif action == "users":
        users = database.get_all_users()
        keyboard = InlineKeyboardMarkup()
        for user in users:
            keyboard.add(InlineKeyboardButton(
                f"👤 {user['username']} (ID: {user['tg_id']})",
                callback_data=f"user_detail_{user['tg_id']}"
            ))
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="👥 Список пользователей:",
            reply_markup=keyboard
        )
    
    elif action == "stats":
        top = database.get_top()
        text = "🏆 *Топ-10 пользователей:*\n\n"
        for place, data in top.items():
            text += f"{place}. {data['Name_user']} — {data['total_time']} сек\n"
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        )
    
    elif action == "back":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔧 Админ-панель",
            reply_markup=generate_admin_menu()
        )
    
    elif action == "close":
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_question_"))
def delete_question(call):
    question_id = int(call.data.split("_")[2])
    if database.delete_question(question_id):
        bot.answer_callback_query(call.id, "✅ Вопрос удален!")
        handle_admin_actions(call)
    else:
        bot.answer_callback_query(call.id, "❌ Ошибка!")

@bot.callback_query_handler(func=lambda call: call.data == "add_question")
def ask_new_question(call):
    admin_state[call.from_user.id] = "waiting_question"
    bot.send_message(
        call.message.chat.id,
        "📝 Введите вопрос в формате:\n"
        "«Вопрос; вариант1; вариант2; вариант3; вариант4; правильный_ответ»\n"
        "Пример:\n"
        "«Сколько планет в Солнечной системе?; 8; 9; 10; 7; 1»"
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "waiting_question")
def add_new_question(message):
    try:
        data = message.text.split(";")
        if len(data) != 6:
            raise ValueError("Неверный формат!")
        
        database.add_question(
            data[0].strip(),
            data[1].strip(),
            data[2].strip(),
            data[3].strip(),
            data[4].strip(),
            int(data[5].strip())
        )
        bot.send_message(message.chat.id, "✅ Вопрос добавлен!")
        admin_state[message.from_user.id] = None
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

# ------------ Обработка ответов ------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("answer_"))
def handle_answer(call):
    user_id = call.from_user.id
    _, current_q_id, selected_opt = call.data.split("_")
    current_q_id = int(current_q_id)
    selected_opt = int(selected_opt)

    is_correct = database.check_answer(current_q_id, selected_opt)

    if is_correct:
        database.complete_question(user_id, current_q_id)
        bot.answer_callback_query(call.id, "✅ Правильно!")
        next_q = database.get_question(current_q_id + 1)
        
        if next_q:
            keyboard = InlineKeyboardMarkup()
            for idx, opt in enumerate(next_q["options"]):
                keyboard.add(InlineKeyboardButton(opt, callback_data=f"answer_{current_q_id + 1}_{idx + 1}"))
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=next_q["question_text"],
                reply_markup=keyboard
            )
            database.add_user_progress(user_id, current_q_id + 1, start_time=int(time.time()))
        else:
            database.add_to_top(user_id, call.from_user.username)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🎉 Квиз пройден! Ваш результат добавлен в топ!"
            )
    else:
        bot.answer_callback_query(call.id, "❌ Неправильно! Попробуйте еще раз.")

if __name__ == "__main__":
    database.create_tables()
    logging.info("Бот запущен...")
    bot.infinity_polling()