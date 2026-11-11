import streamlit as st
import pdfplumber
import docx
import io
from typing import List
from pydantic import BaseModel
from google import genai
from google.genai import types
from st_supabase_connection import SupabaseConnection, execute_query

# --- 1. ПОДКЛЮЧЕНИЕ К SUPABASE ---
# Создаём соединение. Оно будет использоваться для аутентификации.
connection = st.connection("supabase_connection", type=SupabaseConnection)

# --- 2. ПРОВЕРКА АВТОРИЗАЦИИ ---
# Инициализируем session_state для отслеживания входа
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

# Если пользователь не авторизован, показываем форму входа и останавливаем приложение
if st.session_state.auth_user is None:
    tab1, tab2 = st.tabs(["Вход", "Регистрация"])

    with tab1:
        st.subheader("Войти в аккаунт")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Пароль", type="password", key="login_password")
        if st.button("Войти", type="primary", use_container_width=True):
            try:
                # Используем session_client для безопасной аутентификации
                supabase = connection.session_client()
                response = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if response.user:
                    st.session_state.auth_user = response.user
                    st.rerun()
                else:
                    st.error("Неверный email или пароль.")
            except Exception as e:
                st.error(f"Ошибка входа: {e}")

    with tab2:
        st.subheader("Создать аккаунт")
        new_email = st.text_input("Email", key="reg_email")
        new_password = st.text_input("Пароль", type="password", key="reg_password")
        if st.button("Зарегистрироваться", type="primary", use_container_width=True):
            try:
                supabase = connection.session_client()
                response = supabase.auth.sign_up({"email": new_email, "password": new_password})
                if response.user:
                    st.success("Аккаунт создан! Теперь вы можете войти.")
                else:
                    st.error("Не удалось создать аккаунт. Возможно, email уже используется.")
            except Exception as e:
                st.error(f"Ошибка регистрации: {e}")
    
    # Останавливаем выполнение скрипта, чтобы не показывать остальной интерфейс
    st.stop()

# --- 3. ЕСЛИ ПОЛЬЗОВАТЕЛЬ АВТОРИЗОВАН, ПОКАЗЫВАЕМ ОСНОВНОЕ ПРИЛОЖЕНИЕ ---
# Кнопка выхода в сайдбаре
if st.sidebar.button("Выйти"):
    connection.session_client().auth.sign_out()
    st.session_state.auth_user = None
    st.rerun()

# --- 4. НАСТРОЙКА СТРАНИЦЫ И ЯЗЫКА (ОСТАЛЬНАЯ ЧАСТЬ КОДА) ---
st.set_page_config(page_title="AI Contract Auditor", page_icon="⚖️", layout="wide")

# ... (Здесь идёт остальной код из вашего файла: заголовки, загрузка файла, анализ, вывод результатов) ...
# ВАЖНО: Скопируйте сюда все функции и логику из вашего текущего app.py, начиная с раздела "--- 2. ЗАГОЛОВКИ ---" и до конца.
# Убедитесь, что вы НЕ копируете старые импорты и настройку страницы, которые уже есть выше.
