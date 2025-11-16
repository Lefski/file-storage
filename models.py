# Импортируем необходимые модули и классы из SQLAlchemy для работы с базой данных:
# Column — для определения колонок таблицы,
# Integer, String, DateTime, Boolean — типы данных для колонок,
# declarative_base — база для декларативного определения моделей,
# func — для использования SQL-функций (например, now()).
# Импортируем Pydantic для валидации данных и создания схем,
# EmailStr — для валидации email,
# validator — для создания кастомных валидаторов,
# Optional и datetime — для работы с опциональными полями и датами.
# Импортируем enum для создания перечислений (ролей пользователей).
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
import enum

# Создаём базовый класс для декларативного определения моделей SQLAlchemy.
Base = declarative_base()

# --- Перечисление ролей пользователей ---
# Создаём класс UserRole, наследуемый от str и enum.Enum,
# для определения возможных ролей пользователей в системе.
class UserRole(str, enum.Enum):
    USER = "user"        # Обычный пользователь
    ADMIN = "admin"      # Администратор
    MODERATOR = "moderator"  # Модератор

# --- Модель пользователя для SQLAlchemy ---
# Определяем класс User, наследуемый от Base,
# который соответствует таблице "users" в базе данных.
class User(Base):
    __tablename__ = "users"  # Имя таблицы в базе данных

    # Определяем колонки таблицы:
    id = Column(Integer, primary_key=True, index=True)  # Уникальный идентификатор пользователя
    username = Column(String(50), unique=True, index=True, nullable=False)  # Уникальное имя пользователя
    email = Column(String(100), unique=True, index=True, nullable=False)  # Уникальный email пользователя
    password_hash = Column(String(255), nullable=False)  # Хеш пароля пользователя
    role = Column(String(20), default=UserRole.USER, nullable=False)  # Роль пользователя (по умолчанию "user")
    is_active = Column(Boolean, default=True)  # Флаг активности пользователя (по умолчанию True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Дата и время создания записи
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # Дата и время последнего обновления записи

# --- Валидаторы для полей пользователя ---
# Класс UsernameValidator для валидации имени пользователя.
class UsernameValidator:
    MIN_LENGTH = 3  # Минимальная длина имени пользователя
    MAX_LENGTH = 50  # Максимальная длина имени пользователя

    @classmethod
    def validate(cls, username: str) -> str:
        # Удаляем символы '_' и '-' для проверки на алфавитно-цифровые символы.
        cleaned_username = username.replace('_','').replace('-','')
        # Проверяем, что имя пользователя содержит только буквы, цифры, underscores и дефисы.
        if not cleaned_username.isalnum():
            raise ValueError('Username должен содержать только буквы, цифры, underscores и дефисы')
        # Проверяем минимальную длину имени пользователя.
        if len(username) < cls.MIN_LENGTH:
            raise ValueError('Username должен содержать минимум 3 символа')
        # Проверяем максимальную длину имени пользователя.
        if len(username) > cls.MAX_LENGTH:
            raise ValueError('Username не может превышать 50 символов')
        return username

# Класс PasswordValidator для валидации пароля.
class PasswordValidator:
    MIN_LENGTH = 6  # Минимальная длина пароля

    @classmethod
    def validate(cls, password: str) -> str:
        # Проверяем минимальную длину пароля.
        if len(password) < cls.MIN_LENGTH:
            raise ValueError('Пароль должен содержать минимум 6 символов')
        return password

# --- Pydantic-схемы для валидации данных ---
# Схема UserCreate для валидации данных при создании пользователя.
class UserCreate(BaseModel):
    email: EmailStr  # Email пользователя (валидируется как email)
    username: str  # Имя пользователя
    password: str  # Пароль пользователя

    # Валидатор для имени пользователя.
    @validator('username')
    def validate_username(cls, value):
        return UsernameValidator.validate(value)

    # Валидатор для пароля.
    @validator('password')
    def validate_password(cls, value):
        return PasswordValidator.validate(value)

# Схема UserLogin для валидации данных при входе пользователя.
class UserLogin(BaseModel):
    email: EmailStr  # Email пользователя
    password: str  # Пароль пользователя

# Схема UserResponse для возврата данных пользователя.
class UserResponse(BaseModel):
    id: int  # Уникальный идентификатор пользователя
    email: str  # Email пользователя
    username: str  # Имя пользователя
    role: str  # Роль пользователя
    is_active: bool  # Флаг активности пользователя
    created_at: datetime  # Дата и время создания записи

    # Настройка для совместимости с ORM-моделями (например, SQLAlchemy).
    class Config:
        from_attributes = True

# Схема Token для возврата токена доступа.
class Token(BaseModel):
    access_token: str  # Токен доступа
    token_type: str  # Тип токена (например, "bearer")
    role: str  # Роль пользователя

# Схема TokenData для хранения данных из токена.
class TokenData(BaseModel):
    email: Optional[str] = None  # Email пользователя (опционально)
    role: Optional[str] = None  # Роль пользователя (опционально)
