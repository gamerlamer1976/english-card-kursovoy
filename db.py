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
    """Создает и возвращает подключение к базе данных."""
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """Создает таблицы и базовые слова, если их нет."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS words (
                    word_id SERIAL PRIMARY KEY,
                    english_word VARCHAR(50) UNIQUE NOT NULL,
                    russian_translation VARCHAR(50) NOT NULL,
                    is_common BOOLEAN DEFAULT FALSE
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_words (
                    user_id INTEGER REFERENCES users(user_id)
                        ON DELETE CASCADE,
                    word_id INTEGER REFERENCES words(word_id)
                        ON DELETE CASCADE,
                    correct_answers INTEGER DEFAULT 0,
                    total_attempts INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, word_id)
                )
            """)

            # Добавление базовых слов (ON CONFLICT предотвращает дублирование)
            cur.execute("""
                INSERT INTO words
                (english_word, russian_translation, is_common)
                VALUES
                ('red', 'красный', TRUE), ('blue', 'синий', TRUE),
                ('green', 'зеленый', TRUE), ('he', 'он', TRUE),
                ('she', 'она', TRUE), ('it', 'оно', TRUE),
                ('house', 'дом', TRUE), ('tree', 'дерево', TRUE),
                ('car', 'машина', TRUE), ('sun', 'солнце', TRUE)
                ON CONFLICT (english_word) DO NOTHING
            """)
            conn.commit()


def add_user_if_not_exists(username):
    """Добавляет пользователя и возвращает его ID."""
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
                conn.commit()
                return user_id

            return user['user_id']


def get_words_for_learning(user_id):
    """Возвращает случайное слово (общее или личное) и 4 варианта ответа."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Выборка: либо базовое слово, либо добавленное этим пользователем
            cur.execute("""
                SELECT w.word_id, w.english_word, w.russian_translation
                FROM words w
                LEFT JOIN user_words uw ON w.word_id = uw.word_id
                    AND uw.user_id = %s
                WHERE w.is_common = TRUE OR uw.user_id = %s
                ORDER BY RANDOM() LIMIT 1
            """, (user_id, user_id))
            target = cur.fetchone()

            if not target:
                return None, []

            # Получаем 3 неправильных варианта перевода
            cur.execute("""
                SELECT w.russian_translation
                FROM words w
                LEFT JOIN user_words uw ON w.word_id = uw.word_id
                    AND uw.user_id = %s
                WHERE w.word_id != %s
                  AND (w.is_common = TRUE OR uw.user_id = %s)
                ORDER BY RANDOM() LIMIT 3
            """, (user_id, target['word_id'], user_id))

            wrong_words = [
                row['russian_translation'] for row in cur.fetchall()
            ]

            options = wrong_words + [target['russian_translation']]
            random.shuffle(options)

            return target, options


def update_stats(user_id, word_id, is_correct):
    """Обновляет или создает запись со статистикой ответа (UPSERT)."""
    cor_add = 1 if is_correct else 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_words
                (user_id, word_id, correct_answers, total_attempts)
                VALUES (%s, %s, %s, 1)
                ON CONFLICT (user_id, word_id) DO UPDATE SET
                correct_answers = user_words.correct_answers + %s,
                total_attempts = user_words.total_attempts + 1
            """, (user_id, word_id, cor_add, cor_add))
            conn.commit()


def add_new_word(user_id, eng, rus):
    """Добавляет личное слово в базу и привязывает к пользователю."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                "SELECT word_id FROM words WHERE english_word = %s",
                (eng,)
            )
            res = cur.fetchone()

            if res:
                word_id = res['word_id']
            else:
                cur.execute(
                    "INSERT INTO words (english_word, russian_translation) "
                    "VALUES (%s, %s) RETURNING word_id",
                    (eng, rus)
                )
                word_id = cur.fetchone()['word_id']

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
    """Получает список личных слов пользователя для удаления."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT w.word_id, w.english_word, w.russian_translation
                FROM user_words uw
                JOIN words w ON uw.word_id = w.word_id
                WHERE uw.user_id = %s AND w.is_common = FALSE
            """, (user_id,))
            return cur.fetchall()


def delete_user_word(user_id, word_id):
    """Удаляет связь личного слова с пользователем."""
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
                SELECT COALESCE(SUM(correct_answers), 0) as corrects,
                       COALESCE(SUM(total_attempts), 0) as totals,
                       COUNT(word_id) as word_count
                FROM user_words
                WHERE user_id = %s
            """, (user_id,))
            return cur.fetchone()
