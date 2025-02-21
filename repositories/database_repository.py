from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dataclasses import dataclass
from models import Medication, Course  # Определите модели с использованием SQLAlchemy
from sqlalchemy.sql import select

@dataclass
class Medication:
    id: int
    user_id: int
    name: str
    expiry_date: str
    quantity: int
    added_date: str

@dataclass
class Course:
    id: int
    user_id: int
    medicine_name: str
    dosage: str
    schedule: str
    method: str
    added_date: str

DATABASE_URI = "sqlite+aiosqlite:///app.db"

engine = create_async_engine(DATABASE_URI, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class DatabaseRepository:
    async def create_tables(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def add_medication(self, user_id: int, name: str, expiry_date: str, quantity: int) -> None:
        """
        Добавляет новое лекарство в базу данных.
        
        :param user_id: ID пользователя
        :param name: Название лекарства
        :param expiry_date: Дата истечения срока годности
        :param quantity: Количество
        """
        # Реализация

    async def list_medications(self, user_id: int) -> List[Medication]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Medication).where(Medication.user_id == user_id)
            )
            return result.scalars().all() 