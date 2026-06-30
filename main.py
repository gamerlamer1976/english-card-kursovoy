import streamlit as st
import db


def render_learning_tab(u_id):
    """Отрисовка вкладки изучения слов."""
    st.header("Изучаем слова")

    if 'current_word' not in st.session_state:
        word_data, options = db.get_words_for_learning(u_id)
        if word_data:
            st.session_state['current_word'] = word_data
            st.session_state['options'] = options
            st.session_state['answered'] = False
        else:
            st.warning("Ваш словарь пуст. Добавьте новые слова.")

    if st.session_state.get('current_word'):
        cw = st.session_state['current_word']
        st.write(f"Слово: **{cw['english_word']}**")
        st.write("Как будет по-русски?")

        cols = st.columns(4)
        for i, option in enumerate(st.session_state['options']):
            with cols[i]:
                if st.button(option, key=f"btn_{i}"):
                    if not st.session_state['answered']:
                        is_correct = (option == cw['russian_translation'])
                        db.update_stats(u_id, cw['word_id'], is_correct)
                        st.session_state['answered'] = True

                        if is_correct:
                            st.success("Правильно! Молодец!")
                        else:
                            st.error(
                                "Неправильно. Верный ответ: "
                                f"**{cw['russian_translation']}**"
                            )

        if st.session_state.get('answered'):
            if st.button("Следующее слово"):
                del st.session_state['current_word']
                st.rerun()


def render_add_word_tab(u_id):
    """Отрисовка вкладки добавления нового слова (через st.form)."""
    st.header("Добавление нового слова")

    # Применение st.form для автоматической очистки полей
    with st.form("add_word_form", clear_on_submit=True):
        eng = st.text_input("Английское слово:")
        rus = st.text_input("Перевод:")
        submitted = st.form_submit_button("Добавить")

        if submitted:
            if eng and rus:
                db.add_new_word(u_id, eng.lower(), rus.lower())
                st.success(f"Слово '{eng}' успешно добавлено в словарь!")
                stats = db.get_user_stats(u_id)
                st.info(f"Ваших личных слов в статистике: "
                        f"{stats['word_count']}")
            else:
                st.error("Пожалуйста, заполните оба поля.")


def render_delete_word_tab(u_id):
    """Отрисовка вкладки удаления слов."""
    st.header("Удаление личных слов")
    words = db.get_user_words(u_id)

    if words:
        word_dict = {w['english_word']: w['word_id'] for w in words}
        selected = st.selectbox(
            "Выберите слово для удаления:",
            list(word_dict.keys())
        )

        if st.button("Удалить"):
            db.delete_user_word(u_id, word_dict[selected])
            st.success(f"Слово '{selected}' удалено из вашего списка.")

            if st.session_state.get('current_word'):
                cw = st.session_state['current_word']
                if cw['word_id'] == word_dict[selected]:
                    del st.session_state['current_word']
            st.rerun()
    else:
        st.write("У вас пока нет добавленных личных слов.")


def render_stats_tab(u_id):
    """Отрисовка вкладки статистики."""
    st.header("Статистика обучения")
    stats = db.get_user_stats(u_id)

    if stats and stats['totals'] > 0:
        acc = int((stats['corrects'] / stats['totals']) * 100)
        st.write(f"Слов со статистикой ответов: **{stats['word_count']}**")
        st.write(f"Правильных ответов: **{stats['corrects']}**")
        st.write(f"Всего попыток: **{stats['totals']}**")
        st.write(f"Точность ответов: **{acc}%**")
    else:
        st.write("Пока нет статистики. Начните изучение!")


def main():
    """Главная функция запуска приложения."""
    st.set_page_config(page_title="EnglishCard", layout="wide")

    # Инициализация БД при запуске
    db.init_db()

    if 'user_id' not in st.session_state:
        st.title("Добро пожаловать в EnglishCard!")
        username = st.text_input("Введите ваше имя для начала работы:")
        if st.button("Войти"):
            if username:
                user_id = db.add_user_if_not_exists(username)
                st.session_state['user_id'] = user_id
                st.session_state['username'] = username
                st.rerun()
    else:
        u_id = st.session_state['user_id']
        st.sidebar.write(f"Вы вошли как: **{st.session_state['username']}**")
        if st.sidebar.button("Выйти"):
            st.session_state.clear()
            st.rerun()

        tabs_list = [
            "📚 Изучение",
            "➕ Добавить слово",
            "🗑 Удалить слово",
            "📊 Статистика"
        ]
        tab1, tab2, tab3, tab4 = st.tabs(tabs_list)

        with tab1:
            render_learning_tab(u_id)
        with tab2:
            render_add_word_tab(u_id)
        with tab3:
            render_delete_word_tab(u_id)
        with tab4:
            render_stats_tab(u_id)


if __name__ == '__main__':
    main()
