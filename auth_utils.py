# Импортируем CryptContext из passlib для хеширования и проверки паролей.
# Импортируем JWTError и jwt из jose для работы с JWT-токенами.
# Импортируем datetime и timedelta из datetime для работы с датами и временем.
# Импортируем os для работы с переменными окружения.
# Импортируем load_dotenv из dotenv для загрузки переменных окружения из файла .env.
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env.
load_dotenv()

# Получаем секретный ключ для подписи JWT-токенов из переменных окружения.
# Если переменная не задана, используется значение по умолчанию.
SECRET_KEY = os.getenv("SECRET_KEY")

# Получаем алгоритм для подписи JWT-токенов из переменных окружения.
# Если переменная не задана, используется алгоритм HS256.
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Получаем время жизни токена доступа (в минутах) из переменных окружения.
# Если переменная не задана, используется значение 30 минут.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))

# Создаём контекст для хеширования паролей с использованием алгоритма Argon2.
# Настраиваем параметры алгоритма:
# schemes=["argon2"] — используем только Argon2 для хеширования,
# deprecated="auto" — автоматически помечаем устаревшие схемы,
# argon2__time_cost=3 — количество итераций (затраты по времени),
# argon2__memory_cost=65536 — объём используемой памяти (в KiB),
# argon2__parallelism=1 — количество параллельных потоков,
# argon2__salt_size=16 — размер соли (в байтах).
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=1,
    argon2__salt_size=16
)

# Функция для проверки пароля.
# Сравнивает хеш переданного пароля (plain_password) с сохранённым хешем (hashed_password).
# Возвращает True, если пароли совпадают, иначе False.
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Функция для хеширования пароля.
# Принимает пароль в виде строки и возвращает его хеш.
def get_password_hash(password):
    return pwd_context.hash(password)

# Функция для создания JWT-токена доступа.
# Принимает данные (data) и опционально время истечения токена (expires_delta).
# Если expires_delta не передан, используется значение по умолчанию (ACCESS_TOKEN_EXPIRE_MINUTES).
def create_access_token(data: dict, expires_delta: timedelta = None):
    # Копируем входные данные, чтобы не изменять оригинальный словарь.
    to_encode = data.copy()

    # Устанавливаем время истечения токена:
    # если expires_delta передан, используем его,
    # иначе используем значение по умолчанию.
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Добавляем время истечения в данные токена.
    to_encode.update({"exp": expire})

    # Кодируем данные в JWT-токен, используя секретный ключ и алгоритм.
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Функция для создания JWT-токена для обновления access
def create_refresh_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Функция для проверки валидности JWT-токена.
# Принимает токен в виде строки.
# Возвращает декодированные данные (payload), если токен валиден,
# иначе возвращает None.
def verify_token(token: str):
    try:
        # Декодируем токен, используя секретный ключ и алгоритм.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # В случае ошибки декодирования возвращаем None.
        return None

# In-memory хранилище для refresh токенов
refresh_tokens_store = {}

def store_refresh_token(token: str, user_email: str, expires_at: datetime):
    """Сохраняет refresh токен в памяти"""
    refresh_tokens_store[token] = {
        'user_email': user_email,
        'expires_at': expires_at,
        'revoked': False
    }

def get_refresh_token(token: str):
    """Получает данные refresh токена из памяти"""
    return refresh_tokens_store.get(token)

def revoke_refresh_token(token: str):
    """Отзывает refresh токен"""
    if token in refresh_tokens_store:
        refresh_tokens_store[token]['revoked'] = True

def cleanup_expired_tokens():
    """Очищает истекшие токены (можно вызывать периодически)"""
    current_time = datetime.utcnow()
    expired_tokens = [
        token for token, data in refresh_tokens_store.items()
        if data['expires_at'] < current_time
    ]
    for token in expired_tokens:
        del refresh_tokens_store[token]