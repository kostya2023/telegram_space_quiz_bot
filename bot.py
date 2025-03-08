import json
import os
import time
import logging
from telebot import TeleBot, types
from dotenv import load_dotenv
from utils.database import (
    create_tables, add_user, delete_user_progress, get_question, check_answer,
    complete_question, add_user_progress, get_completed_questions, get_all_questions,
    get_my_info, add_to_top, get_top, delete_question, add_question, calculate_total_time, get_all_users
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s](%(asctime)s) - %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_API")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN", "").split(",") if id.strip()]
bot = TeleBot(BOT_TOKEN)

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

admin_state = {}
user_start_time = {}

def log_action(action: str, user_id: int, details: str = ""):
    logging.info(f"ACTION: {action} | USER_ID: {user_id} | DETAILS: {details}")

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def format_time(seconds: int) -> str:
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes} мин {seconds} сек"

def send_question(chat_id, question, question_id, user_id, message_id=None):
    keyboard = types.InlineKeyboardMarkup()
    for idx, option in enumerate(question["options"]):
        keyboard.add(types.InlineKeyboardButton(option, callback_data=f"answer_{question_id}_{idx + 1}"))

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
        bot.send_photo(chat_id, photo, caption=question_text, reply_markup=keyboard, parse_mode="MarkdownV2")

@bot.message_handler(commands=["start"])
def send_welcome(message):
    log_action("start", message.from_user.id)
    welcome_text = config["messages"]["start"]
    bot.send_message(message.chat.id, welcome_text, parse_mode="MarkdownV2")

@bot.message_handler(commands=["help"])
def show_help(message):
    log_action("help", message.from_user.id)
    text = config["messages"]["help"]
    if is_admin(message.from_user.id):
        text += config["messages"]["admin_help"]
    bot.send_message(message.chat.id, text, parse_mode="MarkdownV2")

@bot.message_handler(commands=["get_prize"])
def prize(message):
    user_id = message.from_user.id
    completed = get_completed_questions(user_id)
    total_questions = len(get_all_questions())
    
    if len(completed) == total_questions and total_questions > 0:
        prize_text = config["messages"]["prize_success"]
        bot.send_message(message.chat.id, prize_text, parse_mode="MarkdownV2")
    else:
        prize_failure_text = config["messages"]["prize_failure"].format(len(completed), total_questions)
        bot.send_message(message.chat.id, prize_failure_text, parse_mode="MarkdownV2")

@bot.message_handler(commands=["start_quiz"])
def start_quiz(message):
    user_id = message.from_user.id
    log_action("start_quiz", user_id)
    
    delete_user_progress(user_id)
    add_user(user_id, message.from_user.username)
    
    question = get_question(1)
    if not question:
        no_questions_text = config["messages"]["no_questions"]
        bot.send_message(message.chat.id, no_questions_text, parse_mode="MarkdownV2")
        return

    user_start_time[user_id] = int(time.time())
    add_user_progress(user_id, 1, start_time=user_start_time[user_id])
    send_question(message.chat.id, question, 1, user_id)

@bot.message_handler(commands=["author"])
def author(message):
    author_text = config["messages"]["author"]
    bot.send_message(
        message.chat.id,
        author_text,
        parse_mode="MarkdownV2",
        disable_web_page_preview=True
    )

@bot.message_handler(commands=["stats"])
def show_stats(message):
    user_id = message.from_user.id
    stats = get_my_info(user_id)
    completed = get_completed_questions(user_id)
    
    total_time = stats["total_time"]
    formatted_time = format_time(total_time) if total_time != "Нет данных" else "Нет данных"
    
    text = config["messages"]["stats"].format(
        len(completed),
        formatted_time,
        stats["place"] if stats["place"] != "Нет данных" else "🚫"
    )
    bot.send_message(message.chat.id, text, parse_mode="MarkdownV2")

def generate_admin_menu():
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
    if not is_admin(message.from_user.id):
        access_denied_text = config["messages"]["admin"]["access_denied"]
        bot.send_message(message.chat.id, access_denied_text, parse_mode="MarkdownV2")
        return

    log_action("admin", message.from_user.id)
    panel_text = config["messages"]["admin"]["panel"]
    bot.send_message(
        message.chat.id,
        panel_text,
        parse_mode="MarkdownV2",
        reply_markup=generate_admin_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        access_denied_text = config["messages"]["admin"]["access_denied"]
        bot.answer_callback_query(call.id, access_denied_text)
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
        questions_list_text = config["messages"]["admin"]["questions_list"]
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=questions_list_text,
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
        users_list_text = config["messages"]["admin"]["users_list"]
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=users_list_text,
            reply_markup=keyboard
        )
    
    elif action == "stats":
        top = get_top()
        text = config["messages"]["admin"]["top_users"]
        for place, data in top.items():
            text += f"{place}. {data['Name_user']} — {data['total_time']} сек\n"
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back"))
        )
    
    elif action == "back":
        panel_text = config["messages"]["admin"]["panel"]
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=panel_text,
            reply_markup=generate_admin_menu()
        )
    
    elif action == "close":
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_question_"))
def delete_question_callback(call):
    question_id = int(call.data.split("_")[2])
    if delete_question(question_id):
        question_deleted_text = config["messages"]["admin"]["question_deleted"]
        bot.answer_callback_query(call.id, question_deleted_text)
        handle_admin_actions(call)
    else:
        error_text = config["messages"]["admin"]["error"]
        bot.answer_callback_query(call.id, error_text)

@bot.callback_query_handler(func=lambda call: call.data == "add_question")
def ask_new_question(call):
    admin_state[call.from_user.id] = "waiting_question"
    add_question_instruction = config["messages"]["admin"]["add_question_instruction"]
    bot.send_message(
        call.message.chat.id,
        add_question_instruction
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "waiting_question")
def add_new_question(message):
    try:
        data = message.text.split(";")
        if len(data) != 6:
            raise ValueError(config["messages"]["admin"]["invalid_format"])
        
        add_question(
            data[0].strip(),
            data[1].strip(),
            data[2].strip(),
            data[3].strip(),
            data[4].strip(),
            int(data[5].strip())
        )
        question_added_text = config["messages"]["admin"]["question_added"]
        bot.send_message(message.chat.id, question_added_text)
        admin_state[message.from_user.id] = None
    except Exception as e:
        error_text = f"❌ Ошибка: {e}"
        bot.send_message(message.chat.id, error_text)

@bot.callback_query_handler(func=lambda call: call.data.startswith("answer_"))
def handle_answer(call):
    user_id = call.from_user.id
    _, current_q_id, selected_opt = call.data.split("_")
    current_q_id = int(current_q_id)
    selected_opt = int(selected_opt)

    is_correct = check_answer(current_q_id, selected_opt)

    if is_correct:
        complete_question(user_id, current_q_id)
        correct_answer_text = config["messages"]["correct_answer"]
        bot.answer_callback_query(call.id, correct_answer_text)
        next_q = get_question(current_q_id + 1)
        
        if next_q:
            elapsed_time = int(time.time()) - user_start_time[user_id]
            send_question(
                call.message.chat.id,
                next_q,
                current_q_id + 1,
                user_id,
                message_id=call.message.message_id
            )
            add_user_progress(user_id, current_q_id + 1, start_time=user_start_time[user_id])
        else:
            total_time = calculate_total_time(user_id)
            if total_time is not None:
                add_to_top(user_id, call.from_user.username, total_time)
                quiz_completed_text = config["messages"]["quiz_completed"].format(total_time)
                bot.send_message(
                    call.message.chat.id,
                    quiz_completed_text,
                    parse_mode="MarkdownV2"
                )
    else:
        incorrect_answer_text = config["messages"]["incorrect_answer"]
        bot.answer_callback_query(call.id, incorrect_answer_text)
        question = get_question(1)
        send_question(
            call.message.chat.id,
            question,
            1,
            user_id,
            message_id=call.message.message_id
        )

if __name__ == "__main__":
    create_tables()
    logging.info("Бот запущен...")
    bot.infinity_polling()