import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
  raise ValueError("❌ Помилка: змінна GOOGLE_API_KEY не знайдена у файлі .env")

client = genai.Client(api_key=api_key)


async def analyze_resume_with_ai(resume_text: str, target_position: str) -> str:
    prompt = (
        f"Ти — просунутий кар'єрний AI-агент і рекрутер. Користувач шукає роботу за посадою/стеком: **{target_position}**.\n"
        f"Ось текст його резюме:\n---\n{resume_text}\n---\n\n"
        "Зроби наступне, обов'язково використавши веб-пошук (Google Search):\n"
        "1. **Пошук реальних вакансій:** Знайди 2-3 реальні актуальні вакансії на ринку та вкажи прямі посилання на них.\n"
        "2. **Match Score:** Оціни відповідність цього резюме у відсотках.\n"
        "3. **Поради:** Надай 2-3 поради щодо покращення резюме.\n"
        "4. **Супровідний лист:** Напиши професійний супровідний лист."
    )

    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
            ),
        )
        return response.text
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            return (
                "⏳ **Перевищено ліміт запитів до AI (обов'язкова квота безкоштовного тарифу).**\n\n"
                "Будь ласка, зачекайте 1–2 хвилини, поки ліміт оновиться, і спробуйте надіслати запит знову."
            )
        return f"❌ Помилка при зверненні до Gemini API: {error_str}"