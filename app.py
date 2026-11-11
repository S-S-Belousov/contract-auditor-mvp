import streamlit as st
import pdfplumber
import docx
import io
from typing import List
from pydantic import BaseModel
from google import genai
from google.genai import types
from st_supabase_connection import SupabaseConnection

# --- 1. ПОДКЛЮЧЕНИЕ К SUPABASE ---
connection = st.connection("supabase_connection", type=SupabaseConnection)

# --- 2. ПРОВЕРКА АВТОРИЗАЦИИ ---
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if st.session_state.auth_user is None:
    st.title("⚖️ AI-Аудитор договоров")
    st.caption("Войдите или зарегистрируйтесь, чтобы начать проверку договоров.")

    tab1, tab2 = st.tabs(["Вход", "Регистрация"])

    with tab1:
        st.subheader("Войти в аккаунт")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Пароль", type="password", key="login_password")
        if st.button("Войти", type="primary", use_container_width=True):
            try:
                supabase = connection.session_client()
                response = supabase.auth.sign_in_with_password({"email": login_email, "password": login_password})
                if response.user:
                    st.session_state.auth_user = response.user
                    st.rerun()
                else:
                    st.error("Неверный email или пароль.")
            except Exception as e:
                st.error(f"Ошибка входа: {e}")

    with tab2:
        st.subheader("Создать аккаунт")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Пароль", type="password", key="reg_password")
        if st.button("Зарегистрироваться", type="primary", use_container_width=True):
            try:
                supabase = connection.session_client()
                response = supabase.auth.sign_up({"email": reg_email, "password": reg_password})
                if response.user:
                    st.success("✅ Аккаунт создан! Теперь перейдите на вкладку «Вход» и войдите.")
                else:
                    st.error("Не удалось создать аккаунт. Возможно, email уже используется.")
            except Exception as e:
                st.error(f"Ошибка регистрации: {e}")

    st.stop()

# --- 3. ПОЛЬЗОВАТЕЛЬ АВТОРИЗОВАН ---
if st.sidebar.button("Выйти"):
    try:
        connection.session_client().auth.sign_out()
    except Exception:
        pass
    st.session_state.auth_user = None
    st.rerun()

st.sidebar.success(f"👤 {st.session_state.auth_user.email}")

# --- 4. НАСТРОЙКА СТРАНИЦЫ И ЯЗЫКА ---
st.set_page_config(page_title="AI Contract Auditor", page_icon="⚖️", layout="wide")

if "lang" not in st.session_state:
    st.session_state.lang = "ru"

def t(ru_text, en_text):
    return ru_text if st.session_state.lang == "ru" else en_text

lang_choice = st.sidebar.radio("Язык / Language", ["Русский", "English"], index=0 if st.session_state.lang == "ru" else 1)
if (lang_choice == "Русский" and st.session_state.lang != "ru") or (lang_choice == "English" and st.session_state.lang != "en"):
    st.session_state.lang = "ru" if lang_choice == "Русский" else "en"
    st.rerun()

# --- 5. ЗАГОЛОВКИ ---
st.title(t("⚖️ AI-Аудитор договоров", "⚖️ AI Contract Auditor"))
st.caption(t("Для IT-фрилансеров и digital-агентств. Загрузите договор — получите список опасных пунктов с безопасными формулировками.",
             "For IT freelancers and digital agencies. Upload a contract — get a list of risky clauses with safe wording."))

# --- 6. ЗАГРУЗКА ФАЙЛА ---
uploaded_file = st.file_uploader(
    t("Загрузите договор (PDF или DOCX)", "Upload a contract (PDF or DOCX)"),
    type=["pdf", "docx"]
)

# --- 7. ИЗВЛЕЧЕНИЕ ТЕКСТА ---
def extract_text_from_file(file) -> str:
    text = ""
    if file.name.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n"
    return text.strip()

# --- 8. СТРУКТУРА ОТВЕТА ОТ ИИ ---
class RiskItem(BaseModel):
    quote: str
    explanation: str
    safe_wording: str

class AuditResponse(BaseModel):
    risks: List[RiskItem]

# --- 9. ОСНОВНАЯ ЛОГИКА ---
if uploaded_file is not None:
    with st.spinner(t("Извлекаем текст из документа...", "Extracting text from document...")):
        contract_text = extract_text_from_file(uploaded_file)

    if not contract_text:
        st.error(t("Не удалось извлечь текст. Возможно, это скан (картинка).", "Could not extract text. It might be a scanned image."))
    else:
        st.success(t(f"Текст извлечён ({len(contract_text)} символов).", f"Text extracted ({len(contract_text)} characters)."))

        if st.button(t("🔍 Проверить договор", "🔍 Audit Contract"), type="primary"):
            with st.spinner(t("Нейросеть анализирует договор...", "AI is analyzing the contract...")):
                try:
                    client = genai.Client(
                        api_key=st.secrets["GEMINI_API_KEY"],
                        http_options=types.HttpOptions(timeout=1_200_000)
                    )

                    prompt = f"""
                    Ты — опытный юрист, специализирующийся на защите интересов IT-фрилансеров и digital-агентств.
                    Проанализируй текст договора ниже. Найди 3-5 самых опасных пунктов, которые:
                    - лишают исполнителя прав на интеллектуальную собственность,
                    - позволяют заказчику не платить или штрафовать на несоразмерные суммы,
                    - содержат скрытые условия или односторонние преимущества заказчика.

                    Для каждого пункта:
                    1. Приведи точную цитату из договора.
                    2. Объясни простым языком, чем это опасно для исполнителя.
                    3. Предложи безопасную формулировку для замены этого пункта.

                    Договор:
                    {contract_text[:15000]}
                    """

                    response = client.models.generate_content(
                        model='gemini-3.8-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=AuditResponse,
                            max_output_tokens=8192,
                        ),
                    )

                    audit_result = response.parsed

                    if audit_result is None:
                        st.error(t("Модель не вернула валидный ответ. Попробуйте ещё раз.",
                                   "The model did not return a valid response. Please try again."))
                        st.stop()

                    st.subheader(t("🚨 Найденные риски", "🚨 Found Risks"))
                    st.caption(t("Нажмите на любой риск, чтобы увидеть детали и безопасную формулировку.",
                                 "Click any risk to see details and safe wording."))

                    for i, risk in enumerate(audit_result.risks, 1):
                        with st.expander(f"{t('Риск', 'Risk')} {i}: {risk.quote[:80]}..."):
                            st.markdown(f"**{t('Цитата из договора:', 'Quote from contract:')}**")
                            st.code(risk.quote, language=None)
                            st.markdown(f"**{t('Чем опасно:', 'Why it is dangerous:')}**")
                            st.warning(risk.explanation)
                            st.markdown(f"**{t('Безопасная формулировка:', 'Safe wording:')}**")
                            st.success(risk.safe_wording)
                            if st.button(t("📋 Скопировать формулировку", "📋 Copy wording"), key=f"copy_{i}"):
                                st.code(risk.safe_wording, language=None)
                                st.toast(t("Формулировка показана для копирования.", "Wording displayed for copying."))

                except Exception as e:
                    st.error(t(f"Произошла ошибка при анализе: {e}", f"An error occurred during analysis: {e}"))
