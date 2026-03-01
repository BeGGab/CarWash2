from contextlib import asynccontextmanager
import sqlalchemy as sa
from typing import Optional
from typing import Annotated, List, AsyncGenerator
from sqlalchemy import Text, String, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeMeta,
    class_mapper,
    mapped_column,
)
from sqlalchemy.ext.asyncio import AsyncAttrs

from .config import settings


metadata = sa.MetaData()



engine = create_async_engine(settings.database_url, echo=False, future=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
async_session_maker = async_session_factory
class BaseServiceModel(AsyncAttrs):
    __abstract__ = True

    """Базовый класс для таблиц сервиса."""

    @classmethod
    def on_conflict_constrauuid(cls) -> Optional[tuple]:
        return None

    def to_dict(self) -> dict:
        """Универсальный метод для конвертации объекта SQLAlchemy в словарь"""
        # Получаем маппер для текущей модели
        columns = class_mapper(self.__class__).columns
        # Возвращаем словарь всех колонок и их значений
        return {column.key: getattr(self, column.key) for column in columns}


Base: DeclarativeMeta = declarative_base(metadata=metadata, cls=BaseServiceModel)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()