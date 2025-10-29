from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
import enum

Base = declarative_base()

# Enum для ролей
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# Pydantic схемы


class UsernameValidator:
    MIN_LENGTH = 3
    MAX_LENGTH = 50


    @classmethod
    def validate(cls, username: str) -> str:
        cleaned_username = username.replace('_','').replace('-','')

        if not cleaned_username.isalnum():
            raise ValueError('Username должен содержать только буквы, цифры, underscores и дефисы')
        if len(username) < cls.MIN_LENGTH:
            raise ValueError('Username должен содержать минимум 3 символа')
        if len(username) > cls.MAX_LENGTH:
            raise ValueError('Username не может превышать 50 символов')
        return username
    
class PasswordValidator:
    MIN_LENGTH = 6

    @classmethod
    def validate(cls, password: str) -> str:
        if len(password) < cls.MIN_LENGTH:
            raise ValueError('Пароль должен содержать минимум 6 символов')
        return password
    

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

    @validator('username')
    def validate_username(cls, value):
        return UsernameValidator.validate(value)
    
    @validator('password')
    def validate_password(cls, value):
        return PasswordValidator.validate(value)


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None