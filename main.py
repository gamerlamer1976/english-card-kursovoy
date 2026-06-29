import streamlit as st
import db

# Настройка страницы
st.set_page_config(page_title="EnglishCard", layout="wide")

# Авторизация
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

    # Вкладка 1: Изучение слов
    with tab1:
        st.header("Изучаем слова")

        # Получение нового слова в сессию, если его нет
        if 'current_word' not in st.session_state:
            word_data, options = db.get_words_for_learning(u_id)
            if word_data:
                st.session_state['current_word'] = word_data
                st.session_state['options'] = options
                st.session_state['answered'] = False
            else:
                st.warning("Ваш словарь пуст. Добавьте новые слова.")

        # Отрисовка интерфейса изучения
        if st.session_state.get('current_word'):
            cw = st.session_state['current_word']
            st.write(f"Слово: **{cw['english_word']}**")
            st.write("Как будет по-русски?")

            cols = st.columns(4)
            for i, option in enumerate(st.session_state['options']):
                with cols[i]:
                    # Создание 4 кнопок с вариантами ответов
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

    # Вкладка 2: Добавление слов
    with tab2:
        st.header("Добавление нового слова")
        eng = st.text_input("Английское слово:")
        rus = st.text_input("Перевод:")

        if st.button("Добавить"):
            if eng and rus:
                db.add_new_word(u_id, eng.lower(), rus.lower())
                st.success(f"Слово '{eng}' успешно добавлено в словарь!")
                stats = db.get_user_stats(u_id)
                st.info(f"Теперь вы изучаете слов: {stats['word_count']}")
            else:
                st.error("Пожалуйста, заполните оба поля.")

    # Вкладка 3: Удаление слов
    with tab3:
        st.header("Удаление слова")
        words = db.get_user_words(u_id)

        if words:
            # Формируем словарь {Английское слово: ID слова} для списка выбора
            word_dict = {w['english_word']: w['word_id'] for w in words}
            selected = st.selectbox(
                "Выберите слово для удаления:",
                list(word_dict.keys())
            )

            if st.button("Удалить"):
                db.delete_user_word(u_id, word_dict[selected])
                st.success(f"Слово '{selected}' удалено из вашего списка.")

                # Если удаленное слово висело на вкладке Изучения - сбрасываем
                if st.session_state.get('current_word'):
                    cw = st.session_state['current_word']
                    if cw['word_id'] == word_dict[selected]:
                        del st.session_state['current_word']
                st.rerun()
        else:
            st.write("Словарь пуст.")

    # Вкладка 4: Статистика
    with tab4:
        st.header("Статистика обучения")
        stats = db.get_user_stats(u_id)

        if stats and stats['totals']:
            acc = int((stats['corrects'] / stats['totals']) * 100)
            st.write(f"Всего изучаемых слов: **{stats['word_count']}**")
            st.write(f"Правильных ответов: **{stats['corrects']}**")
            st.write(f"Всего попыток: **{stats['totals']}**")
            st.write(f"Точность ответов: **{acc}%**")
        else:
            st.write("Пока нет статистики. Начните изучение!")
