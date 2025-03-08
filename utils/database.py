import sqlite3
from typing import List, Tuple, Any, Dict, Optional
import time

# Путь к базе данных
db_path = "storage/database.db"

def normalize_fetchall(list_for_normalize: List[Tuple[Any, ...]]) -> List[Any]:
    """
    Преобразует список кортежей в плоский список, извлекая первый элемент каждого кортежа.

    :param list_for_normalize: Список кортежей, например, [("a",), ("b",), ("c",)].
    :return: Плоский список, например, ["a", "b", "c"].
    """
    return [item[0] for item in list_for_normalize]

def create_tables():
    """
    Создает таблицы в базе данных, если они ещё не созданы.
    Если таблицы уже существуют, они не будут перезаписаны.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Создаем таблицу Users, если она не существует
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Users (
                    tg_id TEXT PRIMARY KEY,  -- Уникальный ID пользователя в Telegram
                    username TEXT  -- Имя пользователя
                )
            ''')

            # Создаем таблицу Questions, если она не существует
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Questions (
                    question_id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Уникальный ID вопроса
                    question_text TEXT NOT NULL,  -- Текст вопроса
                    option1 TEXT NOT NULL,  -- Вариант ответа 1
                    option2 TEXT NOT NULL,  -- Вариант ответа 2
                    option3 TEXT NOT NULL,  -- Вариант ответа 3
                    option4 TEXT NOT NULL,  -- Вариант ответа 4
                    correct_option INTEGER NOT NULL,  -- Номер правильного варианта (1, 2, 3 или 4)
                    image_path TEXT  -- Путь к изображению (новая колонка)
                )
            ''')

            # Создаем таблицу UserProgress, если она не существует
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS UserProgress (
                    progress_id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Уникальный ID записи прогресса
                    tg_id TEXT,  -- ID пользователя
                    question_id INTEGER,  -- ID вопроса
                    is_completed INTEGER DEFAULT 0,  -- Статус выполнения вопроса (0 = не пройден, 1 = пройден)
                    start_time INTEGER,  -- Время начала прохождения вопроса (timestamp)
                    end_time INTEGER,  -- Время завершения вопроса (timestamp)
                    FOREIGN KEY (tg_id) REFERENCES Users (tg_id),  -- Внешний ключ на таблицу Users
                    FOREIGN KEY (question_id) REFERENCES Questions (question_id)  -- Внешний ключ на таблицу Questions
                )
            ''')

            # Создаем таблицу TopUsers, если она не существует
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS TopUsers (
                    tg_id TEXT PRIMARY KEY,  -- Уникальный ID пользователя в Telegram
                    username TEXT,  -- Имя пользователя
                    total_time INTEGER,  -- Общее время прохождения квиза (в секундах)
                    FOREIGN KEY (tg_id) REFERENCES Users (tg_id)  -- Внешний ключ на таблицу Users
                )
            ''')

            # Фиксируем изменения в базе данных
            conn.commit()
            print("Таблицы успешно созданы или уже существуют.")

    except sqlite3.Error as e:
        # Обработка ошибок при работе с базой данных
        print(f"Ошибка при создании таблиц: {e}")


# Функция для добавления пользователя
def add_user(user_id: int, username: str) -> bool:
    """
    Добавляет пользователя в базу данных.

    :param user_id: ID пользователя в Telegram.
    :param username: Имя пользователя.
    :return: True, если пользователь успешно добавлен, иначе False.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Проверяем, существует ли пользователь
            cursor.execute("SELECT tg_id FROM Users WHERE tg_id = ?", (str(user_id),))
            if cursor.fetchone():
                print(f"Пользователь {user_id} уже существует.")
                return True  # Пользователь уже существует

            # Добавляем нового пользователя
            cursor.execute("INSERT INTO Users (tg_id, username) VALUES (?, ?)", (str(user_id), username))
            conn.commit()
            print(f"Пользователь {user_id} успешно добавлен.")
            return True  # Пользователь успешно добавлен

    except sqlite3.Error as e:
        # Обработка ошибок при добавлении пользователя
        print(f"Ошибка при добавлении пользователя {user_id}: {e}")
        return False  # Произошла ошибка

# Функция для удаления пользователя
def delete_user(user_id: int) -> bool:
    """
    Удаляет пользователя из базы данных.

    :param user_id: ID пользователя в Telegram.
    :return: True, если пользователь успешно удален, иначе False.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Удаляем пользователя
            cursor.execute("DELETE FROM Users WHERE tg_id = ?", (str(user_id),))

            # Удаляем прогресс пользователя
            cursor.execute("DELETE FROM UserProgress WHERE tg_id = ?", (str(user_id),))

            # Удаляем пользователя из топа
            cursor.execute("DELETE FROM TopUsers WHERE tg_id = ?", (str(user_id),))

            # Фиксируем изменения в базе данных
            conn.commit()
            print(f"Пользователь {user_id} успешно удален.")
            return True  # Пользователь успешно удален

    except sqlite3.Error as e:
        # Обработка ошибок при удалении пользователя
        print(f"Ошибка при удалении пользователя {user_id}: {e}")
        return False  # Произошла ошибка

# Функция для получения всех пользователей
def get_all_users() -> List[str]:
    """
    Возвращает список всех пользователей.

    :return: Список ID пользователей.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Получаем всех пользователей
            cursor.execute("SELECT tg_id FROM Users")
            users = normalize_fetchall(cursor.fetchall())
            print(f"Найдено {len(users)} пользователей.")
            return users

    except sqlite3.Error as e:
        # Обработка ошибок при получении пользователей
        print(f"Ошибка при получении пользователей: {e}")
        return []

# Функция для добавления вопроса с вариантами ответов и изображением
def add_question(question_text: str, option1: str, option2: str, option3: str, option4: str, correct_option: int, image_path: Optional[str] = None) -> bool:
    """
    Добавляет вопрос в базу данных с вариантами ответов и изображением.

    :param question_text: Текст вопроса.
    :param option1: Вариант ответа 1.
    :param option2: Вариант ответа 2.
    :param option3: Вариант ответа 3.
    :param option4: Вариант ответа 4.
    :param correct_option: Номер правильного варианта (1, 2, 3 или 4).
    :param image_path: Путь к изображению (опционально).
    :return: True, если вопрос успешно добавлен, иначе False.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Добавляем вопрос с вариантами ответов и изображением
            cursor.execute('''
                INSERT INTO Questions (question_text, option1, option2, option3, option4, correct_option, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (question_text, option1, option2, option3, option4, correct_option, image_path))

            # Фиксируем изменения в базе данных
            conn.commit()
            print(f"Вопрос '{question_text}' успешно добавлен.")
            return True  # Вопрос успешно добавлен

    except sqlite3.Error as e:
        # Обработка ошибок при добавлении вопроса
        print(f"Ошибка при добавлении вопроса '{question_text}': {e}")
        return False  # Произошла ошибка


# Функция для получения вопроса с вариантами ответов и изображением
def get_question(question_id: int) -> Optional[Dict[str, Any]]:
    """
    Возвращает вопрос с вариантами ответов и изображением.

    :param question_id: ID вопроса.
    :return: Словарь с вопросом, вариантами ответов и изображением, или None, если вопрос не найден.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Получаем вопрос
            cursor.execute('''
                SELECT question_text, option1, option2, option3, option4, correct_option, image_path
                FROM Questions
                WHERE question_id = ?
            ''', (question_id,))
            question = cursor.fetchone()

            if not question:
                return None  # Вопрос не найден

            # Формируем словарь с вопросом, вариантами ответов и изображением
            return {
                "question_text": question[0],
                "options": [question[1], question[2], question[3], question[4]],
                "correct_option": question[5],
                "image_path": question[6]  # Путь к изображению
            }

    except sqlite3.Error as e:
        # Обработка ошибок при получении вопроса
        print(f"Ошибка при получении вопроса с ID {question_id}: {e}")
        return None

# Функция для проверки правильности ответа
def check_answer(question_id: int, user_answer: int) -> bool:
    """
    Проверяет, правильный ли ответ дал пользователь.

    :param question_id: ID вопроса.
    :param user_answer: Номер варианта, выбранного пользователем (1, 2, 3 или 4).
    :return: True, если ответ правильный, иначе False.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Получаем правильный ответ
            cursor.execute('''
                SELECT correct_option
                FROM Questions
                WHERE question_id = ?
            ''', (question_id,))
            correct_option = cursor.fetchone()

            if not correct_option:
                return False  # Вопрос не найден

            # Сравниваем ответ пользователя с правильным ответом
            return user_answer == correct_option[0]

    except sqlite3.Error as e:
        # Обработка ошибок при проверке ответа
        print(f"Ошибка при проверке ответа на вопрос {question_id}: {e}")
        return False

# Функция для начала прохождения вопроса
def start_question(user_id: int, question_id: int) -> bool:
    """
    Начинает прохождение вопроса и записывает время начала.

    :param user_id: ID пользователя в Telegram.
    :param question_id: ID вопроса.
    :return: True, если успешно, иначе False.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Записываем время начала прохождения вопроса (timestamp)
            start_time = int(time.time())
            cursor.execute('''
                INSERT INTO UserProgress (tg_id, question_id, start_time)
                VALUES (?, ?, ?)
            ''', (str(user_id), question_id, start_time))

            # Фиксируем изменения в базе данных
            conn.commit()
            print(f"Пользователь {user_id} начал вопрос {question_id} в {start_time}.")
            return True  # Успешно

    except sqlite3.Error as e:
        # Обработка ошибок при начале вопроса
        print(f"Ошибка при начале вопроса {question_id} для пользователя {user_id}: {e}")
        return False  # Произошла ошибка


# Функция для завершения прохождения вопроса
def complete_question(user_id: int, question_id: int) -> bool:
    """
    Завершает прохождение вопроса и записывает время завершения.

    :param user_id: ID пользователя в Telegram.
    :param question_id: ID вопроса.
    :return: True, если успешно, иначе False.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Записываем время завершения прохождения вопроса (timestamp)
            end_time = int(time.time())
            cursor.execute('''
                UPDATE UserProgress
                SET end_time = ?, is_completed = 1
                WHERE tg_id = ? AND question_id = ? AND end_time IS NULL
            ''', (end_time, str(user_id), question_id))

            # Фиксируем изменения в базе данных
            conn.commit()
            print(f"Пользователь {user_id} завершил вопрос {question_id} в {end_time}.")
            return True  # Успешно

    except sqlite3.Error as e:
        # Обработка ошибок при завершении вопроса
        print(f"Ошибка при завершении вопроса {question_id} для пользователя {user_id}: {e}")
        return False  # Произошла ошибка

# Функция для вычисления общего времени прохождения квиза
def calculate_total_time(user_id: int) -> Optional[int]:
    """
    Вычисляет общее время прохождения квиза для пользователя.

    :param user_id: ID пользователя в Telegram.
    :return: Общее время в секундах, или None, если данные отсутствуют.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Получаем все записи о прохождении вопросов
            cursor.execute('''
                SELECT start_time, end_time
                FROM UserProgress
                WHERE tg_id = ? AND is_completed = 1
            ''', (str(user_id),))
            progress_records = cursor.fetchall()

            if not progress_records:
                return None  # Нет данных

            # Вычисляем общее время
            total_time = 0
            for start_time, end_time in progress_records:
                total_time += (end_time - start_time)

            return total_time

    except sqlite3.Error as e:
        # Обработка ошибок при вычислении времени
        print(f"Ошибка при вычислении времени для пользователя {user_id}: {e}")
        return None


def add_to_top(user_id: int, username: str, new_total_time: int) -> bool:
    """
    Добавляет пользователя в топ, если новое время меньше текущего времени в топе.
    Если время в топе больше или отсутствует, то запись добавляется или обновляется.

    :param user_id: ID пользователя в Telegram.
    :param username: Имя пользователя.
    :param new_total_time: Новое общее время прохождения квиза (в секундах).
    :return: True, если запись успешно добавлена или обновлена, иначе False.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Получаем текущее время пользователя в топе, если оно существует
            cursor.execute('''
                SELECT total_time
                FROM TopUsers
                WHERE tg_id = ?
            ''', (str(user_id),))
            current_time = cursor.fetchone()

            # Если текущее время существует и оно меньше нового времени, не обновляем
            if current_time and current_time[0] < new_total_time:
                print(f"Текущее время пользователя {user_id} в топе меньше нового времени. Обновление не требуется.")
                return False

            # Если текущее время больше или отсутствует, добавляем или обновляем запись
            cursor.execute('''
                INSERT OR REPLACE INTO TopUsers (tg_id, username, total_time)
                VALUES (?, ?, ?)
            ''', (str(user_id), username, new_total_time))

            # Фиксируем изменения в базе данных
            conn.commit()
            print(f"Пользователь {user_id} добавлен в топ с временем {new_total_time} секунд.")
            return True  # Успешно

    except sqlite3.Error as e:
        # Обработка ошибок при добавлении в топ
        print(f"Ошибка при добавлении пользователя {user_id} в топ: {e}")
        return False  # Произошла ошибка

# Функция для получения топа пользователей
def get_top() -> Dict[int, Dict[str, str]]:
    """
    Возвращает топ-10 пользователей.

    :return: Словарь с топом пользователей в формате:
        {
            1: {"total_time": "00:10:23", "Name_user": "User1"},
            2: {"total_time": "00:15:45", "Name_user": "User2"},
            ...
        }
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Получаем топ-10 пользователей, отсортированных по времени
            cursor.execute('''
                SELECT username, total_time
                FROM TopUsers
                ORDER BY total_time ASC
                LIMIT 10
            ''')
            top_users = cursor.fetchall()

            # Формируем словарь с топом
            top_dict = {
                i + 1: {"total_time": user[1], "Name_user": user[0]}
                for i, user in enumerate(top_users)
            }
            return top_dict

    except sqlite3.Error as e:
        # Обработка ошибок при получении топа
        print(f"Ошибка при получении топа: {e}")
        return {}

# Функция для получения информации о текущем пользователе
def get_my_info(user_id: int) -> Dict[str, Any]:
    """
    Возвращает информацию о текущем пользователе.

    :param user_id: ID пользователя в Telegram.
    :return: Словарь с информацией о пользователе в формате:
        {
            "total_time": 123,
            "place": "5"
        }
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Получаем общее время пользователя
            cursor.execute('''
                SELECT total_time
                FROM TopUsers
                WHERE tg_id = ?
            ''', (str(user_id),))
            user_time = cursor.fetchone()

            if not user_time:
                return {"total_time": "Нет данных", "place": "Нет данных"}

            # Получаем место пользователя в топе
            cursor.execute('''
                SELECT COUNT(*) + 1
                FROM TopUsers
                WHERE total_time < ?
            ''', (user_time[0],))
            place = cursor.fetchone()[0]

            return {"total_time": user_time[0], "place": str(place)}

    except sqlite3.Error as e:
        # Обработка ошибок при получении информации
        print(f"Ошибка при получении информации о пользователе {user_id}: {e}")
        return {"total_time": "Ошибка", "place": "Ошибка"}

# Функция для получения списка пройденных вопросов
def get_completed_questions(user_id: int) -> List[int]:
    """
    Возвращает список ID пройденных вопросов для пользователя.

    :param user_id: ID пользователя в Telegram.
    :return: Список ID пройденных вопросов.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Получаем пройденные вопросы
            cursor.execute('''
                SELECT question_id
                FROM UserProgress
                WHERE tg_id = ? AND is_completed = 1
            ''', (str(user_id),))
            completed_questions = normalize_fetchall(cursor.fetchall())
            print(f"Пользователь {user_id} прошел {len(completed_questions)} вопросов.")
            return completed_questions

    except sqlite3.Error as e:
        # Обработка ошибок при получении пройденных вопросов
        print(f"Ошибка при получении пройденных вопросов для пользователя {user_id}: {e}")
        return []


# Функция для удаления прогресса пользователя
def delete_user_progress(user_id: int) -> bool:
    """
    Удаляет весь прогресс пользователя.

    :param user_id: ID пользователя в Telegram.
    :return: True, если успешно, иначе False.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Удаляем прогресс пользователя
            cursor.execute("DELETE FROM UserProgress WHERE tg_id = ?", (str(user_id),))

            # Фиксируем изменения в базе данных
            conn.commit()
            print(f"Прогресс пользователя {user_id} успешно удален.")
            return True  # Прогресс успешно удален

    except sqlite3.Error as e:
        # Обработка ошибок при удалении прогресса
        print(f"Ошибка при удалении прогресса пользователя {user_id}: {e}")
        return False  # Произошла ошибка

def add_user_progress(user_id: int, question_id: int, start_time: Optional[int] = None, end_time: Optional[int] = None) -> bool:
    """
    Добавляет или обновляет запись о прогрессе пользователя в таблице UserProgress.

    :param user_id: ID пользователя в Telegram.
    :param question_id: ID вопроса.
    :param start_time: Время начала прохождения вопроса (timestamp). Если не указано, время начала не обновляется.
    :param end_time: Время завершения вопроса (timestamp). Если не указано, время завершения не обновляется.
    :return: True, если запись успешно добавлена или обновлена, иначе False.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Проверяем, существует ли уже запись о прогрессе для этого вопроса и пользователя
            cursor.execute('''
                SELECT progress_id, start_time, end_time
                FROM UserProgress
                WHERE tg_id = ? AND question_id = ?
            ''', (str(user_id), question_id))
            existing_record = cursor.fetchone()

            if existing_record:
                # Если запись существует, обновляем её
                progress_id = existing_record[0]
                current_start_time = existing_record[1]
                current_end_time = existing_record[2]

                # Обновляем только end_time, если он передан
                if end_time is not None:
                    cursor.execute('''
                        UPDATE UserProgress
                        SET end_time = ?, is_completed = 1
                        WHERE progress_id = ?
                    ''', (end_time, progress_id))
                # Обновляем start_time, только если он передан и текущий start_time отсутствует
                elif start_time is not None and current_start_time is None:
                    cursor.execute('''
                        UPDATE UserProgress
                        SET start_time = ?
                        WHERE progress_id = ?
                    ''', (start_time, progress_id))
            else:
                # Если записи нет, создаем новую
                if start_time is None:
                    # Если start_time не передан, это ошибка (начало вопроса должно быть записано)
                    print(f"Ошибка: start_time не передан для нового вопроса.")
                    return False

                cursor.execute('''
                    INSERT INTO UserProgress (tg_id, question_id, start_time, end_time, is_completed)
                    VALUES (?, ?, ?, ?, ?)
                            ''', (str(user_id), question_id, start_time, end_time, 1 if end_time else 0))

            # Фиксируем изменения в базе данных
            conn.commit()
            print(f"Прогресс пользователя {user_id} для вопроса {question_id} успешно обновлен.")
            return True  # Успешно

    except sqlite3.Error as e:
        # Обработка ошибок при добавлении или обновлении прогресса
        print(f"Ошибка при записи прогресса для пользователя {user_id}: {e}")
        return False  # Произошла ошибка

def update_question_image(question_id: int, image_path: str) -> bool:
    """
    Обновляет путь к изображению для вопроса.

    :param question_id: ID вопроса.
    :param image_path: Новый путь к изображению.
    :return: True, если обновление прошло успешно, иначе False.
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Обновляем путь к изображению
            cursor.execute('''
                UPDATE Questions
                SET image_path = ?
                WHERE question_id = ?
            ''', (image_path, question_id))

            # Фиксируем изменения в базе данных
            conn.commit()
            print(f"Изображение для вопроса {question_id} успешно обновлено.")
            return True  # Успешно

    except sqlite3.Error as e:
        # Обработка ошибок при обновлении изображения
        print(f"Ошибка при обновлении изображения для вопроса {question_id}: {e}")
        return False  # Произошла ошибка


# Добавляем новые функции для администратора
def delete_question(question_id: int) -> bool:
    """Удаляет вопрос по ID."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Questions WHERE question_id = ?", (question_id,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Ошибка при удалении вопроса: {e}")
        return False

def get_all_users() -> List[Dict[str, Any]]:
    """Возвращает список всех пользователей."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tg_id, username FROM Users")
            return [{"tg_id": row[0], "username": row[1]} for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Ошибка при получении пользователей: {e}")
        return []

def delete_user_data(user_id: int) -> bool:
    """Полностью удаляет все данные пользователя."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Удаляем из Users, UserProgress и TopUsers
            cursor.execute("DELETE FROM Users WHERE tg_id = ?", (str(user_id),))
            cursor.execute("DELETE FROM UserProgress WHERE tg_id = ?", (str(user_id),))
            cursor.execute("DELETE FROM TopUsers WHERE tg_id = ?", (str(user_id),))
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Ошибка при удалении пользователя: {e}")
        return False
    
def get_all_questions() -> List[Dict]:
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Questions")
            return [{
                "question_id": row[0],
                "question_text": row[1],
                "correct_option": row[6]
            } for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Ошибка: {e}")
        return []

# Функция для пересоздания базы данных
def recreate_database():
    """
    Пересоздает базу данных (удаляет и создает таблицы заново).
    """
    try:
        # Подключаемся к базе данных
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Удаляем таблицы, если они существуют
            cursor.execute("DROP TABLE IF EXISTS UserProgress")
            cursor.execute("DROP TABLE IF EXISTS Questions")
            cursor.execute("DROP TABLE IF EXISTS Users")
            cursor.execute("DROP TABLE IF EXISTS TopUsers")

            # Создаем таблицы заново
            create_tables()
            print("База данных успешно пересоздана.")

    except sqlite3.Error as e:
        # Обработка ошибок при пересоздании базы данных
        print(f"Ошибка при пересоздании базы данных: {e}")

def calculate_total_time(user_id: int) -> Optional[int]:
    """
    Вычисляет общее время прохождения квиза для пользователя.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Получаем все записи о прохождении вопросов
            cursor.execute('''
                SELECT end_time
                FROM UserProgress
                WHERE tg_id = ? AND is_completed = 1 AND question_id = 25
            ''', (str(user_id),))
            end_time = cursor.fetchone()

            cursor.execute('''
                SELECT start_time
                FROM UserProgress
                WHERE tg_id = ? AND is_completed = 1 AND question_id = 1
            ''', (str(user_id),))
            start_time = cursor.fetchone()


            end_time = end_time[0]
            start_time = start_time[0]
            total_time = int(end_time) - int(start_time)
            return total_time

    except sqlite3.Error as e:
        # Обработка ошибок при вычислении времени
        print(f"Ошибка при вычислении времени для пользователя {user_id}: {e}")
        return None

if __name__ == "__main__":
    recreate_database()
    
    # Основные вопросы
    add_question(
        "Какая планета Солнечной системы самая большая?",
        "Марс", "Венера", "Юпитер", "Сатурн",
        3,  # Юпитер
        "./imgs/question1.jpg"  # Путь к изображению
    )
    
    add_question(
        "Как называется галактика, в которой находится Солнечная система?",
        "Туманность Андромеды", "Млечный Путь", "Сомбреро", "Сигара",
        2,  # Млечный Путь
        "./imgs/question2.jpg"
    )
    
    add_question(
        "Сколько спутников у Марса?",
        "0", "1", "2", "3",
        3,  # 2 (Фобос и Деймос)
        "./imgs/question3.jpg"
    )
    
    add_question(
        "Какой объект называют 'космическим пылесосом'?",
        "Комета", "Чёрная дыра", "Нейтронная звезда", "Квазар",
        2,  # Чёрная дыра
        "./imgs/question4.jpg"
    )
    
    add_question(
        "Сколько минут длился первый полёт человека в космос?",
        "89", "108", "12", "202",
        2,  # 108 минут (Гагарин)
        "./imgs/question5.jpg"
    )

    add_question(
        "Какой газ придаёт Нептуну синий цвет?",
        "Кислород", "Метан", "Гелий", "Углекислый газ",
        2,  # Метан
        "./imgs/question6.jpg"
    )
    
    add_question(
        "Как называется крупнейший вулкан Солнечной системы?",
        "Эверест", "Олимп", "Этна", "Кракатау",
        2,  # Олимп (Марс)
        "./imgs/question7.jpg"
    )
    
    add_question(
        "Какая звезда самая яркая на ночном небе?",
        "Полярная", "Сириус", "Вега", "Альдебаран",
        2,  # Сириус
        "./imgs/question8.jpg"
    )
    
    add_question(
        "Сколько земных лет длится год на Венере?",
        "0.6", "1.9", "3.2", "225",
        4,  # 225 дней ≈ 0.6 лет (ловушка! Правильный ответ 4)
        "./imgs/question9.jpg"
    )
    
    add_question(
        "Какой космический аппарат первым покинул Солнечную систему?",
        "Вояджер-1", "Спутник-1", "Кассини", "Хаббл",
        1,  # Вояджер-1
        "./imgs/question10.jpg"
    )

    # Дополнительные вопросы
    add_question(
        "Какое явление возникает при падении метеорита в атмосферу?",
        "Звездопад", "Метеорный поток", "Солнечное затмение", "Полярное сияние",
        1,  # Звездопад
        "./imgs/question11.jpg"
    )
    
    add_question(
        "Как называется обратная сторона Луны?",
        "Тёмная сторона", "Морская сторона", "Ближняя сторона", "Дальняя сторона",
        4,  # Дальняя сторона
        "./imgs/question12.jpg"
    )
    
    add_question(
        "Какой элемент преобладает в составе Солнца?",
        "Кислород", "Углерод", "Гелий", "Водород",
        4,  # Водород (≈73%)
        "./imgs/question13.jpg"
    )
    
    add_question(
        "Сколько колец у Сатурна?",
        "3", "7", "Тысячи", "Нет колец",
        3,  # Тысячи тонких колец
        "./imgs/question14.jpg"
    )
    
    add_question(
        "Какая планета вращается 'лёжа на боку'?",
        "Уран", "Нептун", "Плутон", "Венера",
        1,  # Уран
        "./imgs/question15.jpg"
    )

    # Сложные вопросы
    add_question(
        "Как называется гипотетическая форма жизни на основе кремния?",
        "Ксеноморфы", "Силиконы", "Кремниевые люди", "Серафимы",
        2,  # Силиконы
        "./imgs/question16.jpg"
    )
    
    add_question(
        "Какой телескоп обнаружил экзопланеты в 'зоне жизни'?",
        "Хаббл", "Джеймс Уэбб", "Кеплер", "Спитцер",
        3,  # Кеплер
        "./imgs/question17.jpg"
    )
    
    add_question(
        "Какая галактика столкнётся с Млечным Путём через 4 млрд лет?",
        "Туманность Андромеды", "Большое Магелланово Облако", "Треугольник", "Скульптор",
        1,  # Андромеда
        "./imgs/question18.jpg"
    )
    
    add_question(
        "Сколько земных лет длится один день на Меркурии?",
        "58 дней", "176 дней", "365 дней", "88 дней",
        2,  # 176 дней (из-за резонанса вращения)
        "./imgs/question19.jpg"
    )
    
    add_question(
        "Как называется точка, где гравитация перестаёт действовать?",
        "Сингулярность", "Горизонт событий", "Точка Лагранжа", "Гравитационный колодец",
        3,  # Точка Лагранжа
        "./imgs/question20.jpg"
    )

    # Завершающие вопросы
    add_question(
        "Какой элемент образуется в ядрах умирающих звёзд?",
        "Железо", "Золото", "Уран", "Кислород",
        1,  # Железо
        "./imgs/question21.jpg"
    )
    
    add_question(
        "Какое расстояние измеряют в парсеках?",
        "Скорость света", "Масса звёзд", "Космические расстояния", "Яркость",
        3,  # Расстояния
        "./imgs/question22.jpg"
    )
    
    add_question(
        "Как называется взрыв сверхновой типа Ia?",
        "Термоядерный", "Гравитационный коллапс", "Киллонова", "Гипернова",
        1,  # Термоядерный (из-за белого карлика)
        "./imgs/question23.jpg"
    )
    
    add_question(
        "Сколько процентов Вселенной составляет видимая материя?",
        "5%", "27%", "68%", "95%",
        1,  # 5% (остальное — тёмная материя и энергия)
        "./imgs/question24.jpg"
    )
    
    add_question(
        "Какой объект испускает повторяющиеся радиосигналы?",
        "Пульсар", "Квазар", "Метеорит", "Кометное ядро",
        1,  # Пульсар
        "./imgs/question25.jpg"
    )

    print("База данных успешно инициализирована с 25 вопросами и изображениями!")