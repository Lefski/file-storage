import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Используем прямую ссылку на вашу удаленную БД
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:iNteNtyS@185.175.128.99:5454/filestorage")

# Создаем engine с настройками для удаленной БД
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_recycle=3600,   # Переподключение каждый час
    echo=True  # Логирование SQL запросов (можно убрать в продакшене)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Зависимость для получения сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()