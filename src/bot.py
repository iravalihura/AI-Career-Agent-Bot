import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, F, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

# Імпортуємо наш ізольований AI-сервіс та парсери
from ai_service import analyze_resume_with_ai
from parser import extract_text_from_docx, extract_text_from_pdf

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

dp = Dispatcher()


class CareerForm(StatesGroup):
  waiting_for_resume = State()
  waiting_for_position = State()


main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📄 Завантажити резюме"),
            KeyboardButton(text="🔍 Пошук вакансій"),
        ],
        [KeyboardButton(text="📊 Мої відгуки та статус")],
    ],
    resize_keyboard=True,
)


async def send_long_message(message: Message, text: str, reply_markup=None):
  """Допоміжна функція для відправки довгих текстів частинами

  (обхід ліміту Telegram у 4096 символів).
  """
  max_length = 4000
  if len(text) <= max_length:
    await message.answer(text, reply_markup=reply_markup)
    return

  for i in range(0, len(text), max_length):
    chunk = text[i : i + max_length]
    markup = reply_markup if i + max_length >= len(text) else None
    await message.answer(chunk, reply_markup=markup)


@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
  await state.clear()
  user_name = html.quote(message.from_user.first_name)
  await message.answer(
      f"Вітаю, {user_name}! 🤖\n\n"
      f"Я — твій реальний **AI Career Agent Bot**. Надішли своє резюме у"
      f" форматі PDF або DOCX, і штучний інтелект проаналізує його та підбере"
      f" вакансії!\n\n"
      f"Обери дію нижче:",
      reply_markup=main_kb,
  )


@dp.message(F.text == "📄 Завантажити резюме")
async def upload_resume_request(message: Message, state: FSMContext) -> None:
  await state.set_state(CareerForm.waiting_for_resume)
  await message.answer(
      "Будь ласка, надішли своє резюме файлом у форматі **PDF** або **DOCX**.",
      reply_markup=ReplyKeyboardRemove(),
  )


@dp.message(CareerForm.waiting_for_resume, F.document)
async def receive_resume(message: Message, state: FSMContext) -> None:
  document = message.document
  file_name = document.file_name.lower()

  if not file_name.endswith((".pdf", ".docx")):
    await message.answer(
        "❌ Помилка. Підтримуються лише файли PDF або DOCX. Спробуй ще раз."
    )
    return

  # Завантажуємо файл із серверів Telegram
  file_info = await message.bot.get_file(document.file_id)
  file_bytes_io = await message.bot.download_file(file_info.file_path)
  file_bytes = file_bytes_io.read()

  # Витягуємо текст залежно від формату
  if file_name.endswith(".pdf"):
    resume_text = extract_text_from_pdf(file_bytes)
  else:
    resume_text = extract_text_from_docx(file_bytes)

  if not resume_text.strip():
    await message.answer(
        "❌ Не вдалося витягти текст із файлу. Можливо, він складається лише з"
        " зображень або захищений."
    )
    return

  # Зберігаємо текст резюме в пам'яті FSM-сесії
  await state.update_data(resume_text=resume_text)
  await state.set_state(CareerForm.waiting_for_position)

  await message.answer(
      f"✅ Резюме **{html.quote(document.file_name)}** успішно розпізнано!\n\n"
      f"Тепер введи **бажану посаду або стек** (наприклад: *Python Developer* або"
      f" *AI Engineer*):",
      reply_markup=ReplyKeyboardRemove(),
  )


@dp.message(CareerForm.waiting_for_position)
async def receive_position(message: Message, state: FSMContext) -> None:
  position = message.text
  data = await state.get_data()
  resume_text = data.get("resume_text")

  wait_msg = await message.answer(
      "🔄 Штучний інтелект аналізує твоє резюме, шукає вакансії на ринку та"
      " готує фідбек... ⏳",
      reply_markup=main_kb,
  )

  # Викликаємо окрему функцію для аналізу через Gemini API
  ai_response = await analyze_resume_with_ai(resume_text, position)

  # Видаляємо повідомлення про завантаження
  await message.bot.delete_message(
      chat_id=message.chat.id, message_id=wait_msg.message_id
  )

  full_response = f"🎯 **Результати AI-аналізу та підбору:**\n\n{ai_response}"

  # Відправляємо результат (безпечно для довгих текстів)
  await send_long_message(message, full_response, reply_markup=main_kb)
  await state.clear()


@dp.message(F.text == "🔍 Пошук вакансій")
async def search_vacancies(message: Message) -> None:
  await message.answer(
      "Скористайся кнопкою **📄 Завантажити резюме**, щоб розпочати персональний"
      " підбір вакансій за твоїм профілем.",
      reply_markup=main_kb,
  )


@dp.message(F.text == "📊 Мої відгуки та статус")
async def show_history(message: Message) -> None:
  await message.answer(
      "📋 Усі активні сесії наразі обробляються в реальному часі. У наступних"
      " спринтах тут буде інтеграція з базою PostgreSQL 🗄️.",
      reply_markup=main_kb,
  )


async def main() -> None:
  if not TOKEN:
    raise ValueError("Помилка: Не задано BOT_TOKEN у змінних середовища!")
  bot = Bot(
      token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
  )
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    print("Бот зупинений.")