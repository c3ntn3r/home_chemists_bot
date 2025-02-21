import logging
from typing import Optional, Callable
import asyncio
import aiosqlite
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, CallbackQueryHandler
from telegram.ext import filters
from config import TELEGRAM_BOT_TOKEN, GROQ_API_KEY, DATABASE_URI, LLM_MODEL, ALLOWED_USERS
from constants import Messages
from repositories.database_repository import DatabaseRepository
from services.llm_service import GroqLLMService
from formatters.message_formatter import MessageFormatter
import re
from calendar import monthrange
from telegram.error import TelegramError

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def check_access(func: Callable):
    """Декоратор для проверки доступа пользователя"""
    async def wrapper(self, update: Update, context):
        user_id = update.effective_user.id
        if not ALLOWED_USERS or user_id in ALLOWED_USERS:
            return await func(self, update, context)
        logger.warning(f"Попытка несанкционированного доступа от пользователя {user_id}")
        await update.message.reply_text(Messages.ACCESS_DENIED.value)
    return wrapper

class MedicineBot:
    def __init__(self):
        self.db_repository = DatabaseRepository(DATABASE_URI)
        self.llm_service = GroqLLMService(GROQ_API_KEY, LLM_MODEL)
        self.formatter = MessageFormatter()
        
        self._COMMANDS = {
            "аптечка": "list_meds",
            "курс": "list_courses",
            "срок": "expiry_medications"
        }
        
    def _parse_medication_message(self, text: str) -> Optional[dict]:
        """Парсинг сообщения о добавлении лекарства"""
        pattern = r"лекарство\s+([\w\s\-]+)\s+(\d{2}\.\d{2})\s*x(\d+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            expiry = match.group(2).strip()
            quantity = int(match.group(3))
            month, year = expiry.split(".")
            year_full = int("20" + year)
            month = int(month)
            last_day = monthrange(year_full, month)[1]
            expiry_date = datetime(year_full, month, last_day).date().isoformat()
            return {"name": name, "expiry_date": expiry_date, "quantity": quantity}
        return None
        
    @check_access
    async def start(self, update: Update, context) -> None:
        keyboard = [
            ["Моя аптечка", "Мой курс лекарств"],
            ["Сроки годности"]
        ]
        await update.message.reply_text(
            "Здравствуйте! Я бот для управления вашей домашней аптечкой.",
            reply_markup={"keyboard": keyboard, "resize_keyboard": True}
        )

    @check_access
    async def handle_message(self, update: Update, context) -> None:
        try:
            user_id = update.message.from_user.id
            text = update.message.text.lower()
            
            # Быстрая проверка команд без LLM
            for key, command in self._COMMANDS.items():
                if key in text:
                    response = await self._handle_command(command, user_id)
                    await update.message.reply_text(response)
                    return
            
            # Остальная логика...
            response = await self._process_message(user_id, text)
            await update.message.reply_text(response)
            
        except TelegramError as te:
            logger.error(f"Telegram ошибка: {te}")
            await update.message.reply_text("Произошла ошибка взаимодействия с Telegram.")
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await update.message.reply_text(Messages.ERROR_PROCESSING.value)

    async def _process_message(self, user_id: int, text: str) -> str:
        """Обработка сообщения пользователя"""
        if not isinstance(user_id, int) or not isinstance(text, str):
            logger.error(f"Некорректные входные данные: user_id={user_id}, text={text}")
            return "Ошибка: некорректные входные данные"

        # 1. Проверка на прямые команды без LLM
        if re.match(r"лекарство\s+[\w\s\-]+\s+\d{2}\.\d{2}\s*x\d+", text, re.IGNORECASE):
            med_data = self._parse_medication_message(text)
            if med_data:
                self.db_repository.add_medication(
                    user_id, 
                    med_data["name"], 
                    med_data["expiry_date"], 
                    med_data["quantity"]
                )
                return f"Лекарство '{med_data['name']}' добавлено с сроком годности до {med_data['expiry_date']} (количество: {med_data['quantity']})."

        try:
            # 2. Получение намерения через LLM
            llm_response = await self.llm_service.get_completion(
                f"Проанализируй сообщение и определи намерение: '{text}'\n"
                "Ответь одним словом: добавить/рекомендация/аптечка/курс"
            )

            if not llm_response:
                return "Извините, произошла ошибка при обработке запроса. Попробуйте позже."

            # 3. Обработка симптомов
            if "рекомендация" in llm_response.lower():
                medications = self.db_repository.list_medications(user_id)
                if not medications:
                    return "Ваша аптечка пуста. Невозможно дать рекомендации."

                symptom_prompt = (
                    f"Пользователь описывает следующие симптомы: '{text}'\n"
                    f"Доступные лекарства:\n{', '.join(med.name for med in medications)}\n\n"
                    "Дай рекомендацию по приему лекарств из списка. "
                    "Учитывай:\n"
                    "1. Основные показания к применению\n"
                    "2. Возможные противопоказания\n"
                    "3. Дозировку\n"
                    "4. Меры предосторожности\n"
                    "Если нет подходящих лекарств, укажи это."
                )
                recommendation = await self.llm_service.get_completion(symptom_prompt)
                return recommendation if recommendation else "Не удалось сформировать рекомендацию."

            # 4. Просмотр аптечки
            elif "аптечка" in text.lower() or "лист" in text.lower():
                medications = self.db_repository.list_medications(user_id)
                return self.formatter.format_medications_list(medications)

            # 5. Добавление курса приема
            elif "курс" in text.lower():
                pattern = r"курс\s+([\w\s\-]+)\s+([\w\d]+)\s+([\w\s\-:]+)(?:\s+метод\s+([\w\s\-]+))?"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    medicine_name = match.group(1).strip()
                    dosage = match.group(2).strip()
                    schedule = match.group(3).strip()
                    method = match.group(4).strip() if match.group(4) else "Не указан"
                    self.db_repository.add_course(user_id, medicine_name, dosage, schedule, method)
                    return f"Курс приема для '{medicine_name}' добавлен: дозировка {dosage}, расписание: {schedule}, метод: {method}."
                return Messages.INVALID_COURSE_FORMAT.value

            return f"Не удалось определить действие. Попробуйте переформулировать запрос."

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
            return Messages.ERROR_PROCESSING.value

    @check_access
    async def button(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data
        
        try:
            if data == "list_meds":
                meds = self.db_repository.list_medications(user_id)
                text = self.formatter.format_medications_list(meds)
            elif data == "list_courses":
                courses = self.db_repository.list_courses(user_id)
                text = self.formatter.format_courses_list(courses)
        except Exception as e:
            logger.error(f"Ошибка доступа для пользователя {user_id}: {e}")
            text = Messages.ERROR_PROCESSING.value
        
        await query.edit_message_text(text=text)

    async def _handle_command(self, command: str, user_id: int) -> str:
        """Обработка команд от кнопок"""
        try:
            if command == "list_meds":
                medications = await self.db_repository.list_medications(user_id)
                return self.formatter.format_medications_list(medications)
            
            elif command == "list_courses":
                courses = await self.db_repository.list_courses(user_id)
                return self.formatter.format_courses_list(courses)
            
            elif command == "expiry_medications":
                medications = await self.db_repository.list_medications(user_id)
                if not medications:
                    return Messages.EMPTY_CABINET
                
                today = datetime.today().date()
                expiring_meds = []
                
                for med in medications:
                    expiry_date = datetime.fromisoformat(med.expiry_date).date()
                    days_to_expiry = (expiry_date - today).days
                    if days_to_expiry > 0:
                        expiring_meds.append(f"{med.name} - истекает через {days_to_expiry} дней")
                
                if not expiring_meds:
                    return "Нет лекарств с приближающимся сроком годности."
                
                return "Сроки годности:\n" + "\n".join(expiring_meds)
            
            return "Неизвестная команда"
            
        except Exception as e:
            logger.error(f"Ошибка при обработке команды {command}: {e}")
            return Messages.ERROR_PROCESSING.value

async def main() -> None:
    bot = MedicineBot()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(CallbackQueryHandler(bot.button))
    
    # Запускаем задачу напоминаний
    asyncio.create_task(reminder_task(application))
    
    await application.run_polling()

async def check_reminders(application):
    """
    Функция для проверки и отправки напоминаний о приближающемся окончании срока годности лекарств,
    а также удаления просроченных лекарств.
    """
    with DatabaseRepository(DATABASE_URI).get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, user_id, name, expiry_date FROM medications")
        meds = cur.fetchall()
    
    today = datetime.today().date()
    
    for med in meds:
        med_id, user_id, name, expiry_str = med
        expiry_date = datetime.fromisoformat(expiry_str).date()
        days_to_expiry = (expiry_date - today).days
        
        # Если лекарство просрочено, удаляем его и отправляем уведомление
        if days_to_expiry < 0:
            try:
                logger.info(f"Удаление просроченного лекарства {name} для пользователя {user_id}")
                with DatabaseRepository(DATABASE_URI).get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("DELETE FROM medications WHERE id = ?", (med_id,))
                    conn.commit()
                await application.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"⚠️ Внимание! Лекарство {name} было автоматически удалено из вашей аптечки, "
                        f"так как его срок годности истёк {expiry_date}.\n"
                        "Пожалуйста, утилизируйте это лекарство надлежащим образом."
                    )
                )
            except Exception as e:
                logger.error(f"Ошибка при удалении просроченного лекарства {name} для пользователя {user_id}: {e}")
        # Напоминание: за 60 дней и затем каждые 14 дней
        elif days_to_expiry == 60 or (days_to_expiry < 60 and (60 - days_to_expiry) % 14 == 0):
            try:
                await application.bot.send_message(
                    chat_id=user_id,
                    text=f"Напоминание: лекарство {name} истекает через {days_to_expiry} дней."
                )
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")

async def reminder_task(application):
    """
    Асинхронная задача для проверки напоминаний каждый день.
    """
    while True:
        await check_reminders(application)
        await asyncio.sleep(3600)  # Проверка каждый час

if __name__ == '__main__':
    asyncio.run(main()) 