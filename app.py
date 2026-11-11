import streamlit as st
import pdfplumber
import docx
import io
from typing import List
from pydantic import BaseModel
from google import genai
from google.genai import types

# --- 1. НАСТРОЙКА СТРАНИЦЫ И ЯЗЫКА ---
st.set_page_config(page_title="AI Contract Auditor", page_icon="⚖️", layout="wide")

if "lang" not in st.session_state:
    st.session_state.lang = "ru"

def t(ru_text, en_text):
    """Функция перевода. Возвращает текст на выбранном языке."""
    return ru_text if st.session_state.lang == "ru" else en_text

# Переключатель языка в сайдбаре
lang_choice = st.sidebar.radio("Язык / Language", ["Русский", "English"], index=0 if st.session_state.lang == "ru" else 1)
if (lang_choice == "Русский" and st.session_state.lang != "ru") or (lang_choice == "English" and st.session_state.lang != "en"):
    st.session_state.lang = "ru" if lang_choice == "Русский" else "en"
    st.rerun()

# --- 2. ЗАГОЛОВКИ ---
st.title(t("⚖️ AI-Аудитор договоров", "⚖️ AI Contract Auditor"))
st.caption(t("Для IT-фрилансеров и digital-агентств. Загрузите договор — получите список опасных пунктов с безопасными формулировками.", 
             "For IT freelancers and digital agencies. Upload a contract — get a list of risky clauses with safe wording."))

# --- 3. ЗАГРУЗКА ФАЙЛА ---
uploaded_file = st.file_uploader(
    t("Загрузите договор (PDF или DOCX)", "Upload a contract (PDF or DOCX)"),
    type=["pdf", "docx"]
)

# --- 4. ИЗВЛЕЧЕНИЕ ТЕКСТА ---
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

# --- 5. СТРУКТУРА ОТВЕТА ОТ ИИ (Схема) ---
class RiskItem(BaseModel):
    quote: str
    explanation: str
    safe_wording: str

class AuditResponse(BaseModel):
    risks: List[RiskItem]

# --- 6. ОСНОВНАЯ ЛОГИКА ---
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
                    # Инициализация клиента Gemini
                    # Ключ будет браться из секретов Streamlit Cloud
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

                    # Формируем промпт
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

                    # Запрос к Gemini со структурированным выводом
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=AuditResponse,
                        ),
                    )

                    # Парсим ответ
                    audit_result = response.parsed

                    # Отображаем результаты
                    st.subheader(t("🚨 Найденные риски", "🚨 Found Risks"))
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
                    st.error(t(f"Произошла ошибка: {e}", f"An error occurred: {e}"))
                    st.info(t("Проверьте, что API-ключ Gemini добавлен в секреты приложения.", "Check that the Gemini API key is added to the app secrets."))
