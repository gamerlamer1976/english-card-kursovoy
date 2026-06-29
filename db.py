import random
import psycopg2
from psycopg2.extras import DictCursor


# Данные настроек PostgreSQL
DB_CONFIG = {
    'dbname': 'english_card_db',
    'user': 'postgres',
    'password': '123',
    'host': 'localhost',
    'port': '5432'
}


def get_connection():
    """Создаем и подключаемся к базе данных."""
    return psycopg2.connect(**DB_CONFIG)


def add_user_if_not_exists(username):
    """Добавляем пользователя и привязываем 10 базовых слов."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT user_id FROM users WHERE username = %s",
                (username,)
            )
            user = cur.fetchone()

            if not user:
                cur.execute(
                    "INSERT INTO users (username) VALUES (%s) "
                    "RETURNING user_id",
                    (username,)
                )
                user_id = cur.fetchone()['user_id']

                cur.execute("""
                    INSERT INTO user_words (user_id, word_id)
                    SELECT %s, word_id FROM words LIMIT 10
                """, (user_id,))

                conn.commit()
                return user_id

            return user['user_id']


def get_words_for_learning(user_id):
    """Возвращает случайное слово пользователя и 4 варианта ответа."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Получаем 1 случайное слово, которое изучает пользователь
            cur.execute("""
                SELECT w.word_id, w.english_word, w.russian_translation
                FROM user_words uw
                JOIN words w ON uw.word_id = w.word_id
                WHERE uw.user_id = %s
                ORDER BY RANDOM() LIMIT 1
            """, (user_id,))
            target = cur.fetchone()

            if not target:
                return None, []

            # Получаем 3 неправильных перевода из общей базы
            cur.execute("""
                SELECT russian_translation FROM words
                WHERE word_id != %s
                ORDER BY RANDOM() LIMIT 3
            """, (target['word_id'],))

            wrong_words = [
                row['russian_translation'] for row in cur.fetchall()
            ]

            # Формируем список из 4 вариантов и перемешиваем
            options = wrong_words + [target['russian_translation']]
            random.shuffle(options)

            return target, options


def update_stats(user_id, word_id, is_correct):
    """Обновляет счетчики ответов пользователя."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            if is_correct:
                cur.execute("""
                    UPDATE user_words
                    SET correct_answers = correct_answers + 1,
                        total_attempts = total_attempts + 1
                    WHERE user_id = %s AND word_id = %s
                """, (user_id, word_id))
            else:
                cur.execute("""
                    UPDATE user_words
                    SET total_attempts = total_attempts + 1
                    WHERE user_id = %s AND word_id = %s
                """, (user_id, word_id))
            conn.commit()


def add_new_word(user_id, eng, rus):
    """Добавляет новое слово в базу и привязывает к пользователю."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Проверяем, есть ли уже такое английское слово в общей базе
            cur.execute(
                "SELECT word_id FROM words WHERE english_word = %s",
                (eng,)
            )
            res = cur.fetchone()

            if res:
                word_id = res['word_id']
            else:
                # Если нет - добавляем
                cur.execute(
                    "INSERT INTO words (english_word, russian_translation) "
                    "VALUES (%s, %s) RETURNING word_id",
                    (eng, rus)
                )
                word_id = cur.fetchone()['word_id']

            # Привязываем слово к пользователю, если еще не привязано
            cur.execute(
                "SELECT 1 FROM user_words "
                "WHERE user_id = %s AND word_id = %s",
                (user_id, word_id)
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO user_words (user_id, word_id) "
                    "VALUES (%s, %s)",
                    (user_id, word_id)
                )
            conn.commit()


def get_user_words(user_id):
    """Получает список всех слов конкретного пользователя для удаления."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT w.word_id, w.english_word, w.russian_translation
                FROM user_words uw
                JOIN words w ON uw.word_id = w.word_id
                WHERE uw.user_id = %s
            """, (user_id,))
            return cur.fetchall()


def delete_user_word(user_id, word_id):
    """Удаляет связь слова с пользователем."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_words "
                "WHERE user_id = %s AND word_id = %s",
                (user_id, word_id)
            )
            conn.commit()


def get_user_stats(user_id):
    """Получает статистику ответов пользователя."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT SUM(correct_answers) as corrects,
                       SUM(total_attempts) as totals,
                       COUNT(word_id) as word_count
                FROM user_words
                WHERE user_id = %s
            """, (user_id,))
            return cur.fetchone()
