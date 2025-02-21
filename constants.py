# Временные интервалы
REMINDER_CHECK_INTERVAL = 86400  # 24 часа
EXPIRY_WARNING_DAYS = 60
REMINDER_INTERVAL_DAYS = 14

# Ограничения
MAX_CACHE_SIZE = 100
DEFAULT_MAX_TOKENS = 150
MEDICATION_NAME_MAX_LENGTH = 100

# Шаблоны сообщений
from enum import Enum

class Messages(Enum):
    EMPTY_CABINET = "Ваша аптечка пуста."
    ERROR_PROCESSING = "Произошла ошибка при обработке вашего сообщения. Попробуйте позже."
    INVALID_COURSE_FORMAT = "Не удалось распознать данные курса. Пожалуйста, используйте формат: 'курс Название Дозировка Расписание [метод Метод]'." 