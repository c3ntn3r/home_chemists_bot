# config.py

from dotenv import load_dotenv
import os

load_dotenv()

# ВАЖНО: не публикуйте эти ключи в открытых репозиториях!
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URI = os.getenv("DATABASE_URI", "app.db")  # Используем SQLite база данных 
LLM_MODEL = os.getenv("LLM_MODEL", "mixtral-8x7b-32768")  # Модель LLM для использования через Groq API

# Валидация
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в .env файле")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY не установлен в .env файле")