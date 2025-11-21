# Импортируем необходимые модули и классы из FastAPI для создания API,
# работы с зависимостями, обработки ошибок, работы с HTTP-запросами и шаблонами.
# Также импортируем модули для работы с базой данных, моделями и утилитами аутентификации.
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, Form, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json
from datetime import timedelta, datetime
from models import UserCreate, UserLogin, UserResponse, Token, UserRole, RefreshToken, FileInfo, FileRenameRequest, FileListResponse, UserQuotaUpdate
import models
import auth_utils
from database import get_db
from file_storage import file_storage

# Создаём экземпляр FastAPI с указанием метаданных (название и версия API).
app = FastAPI(title="File Storage Auth API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Разрешает все origins
    allow_credentials=True, # Разрешает отправку cookies
    allow_methods=["*"],    # Разрешает все методы
    allow_headers=["*"],    # Разрешает все заголовки
)

# Настраиваем шаблонизатор Jinja2 для рендеринга HTML-страниц.
# Указываем директорию, где хранятся шаблоны.
templates = Jinja2Templates(directory="templates")

# Создаём объект для работы с HTTP Bearer авторизацией.
security = HTTPBearer()

# Обработчики исключений
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        # Получаем поле с ошибкой (игнорируем "body" в начале)
        loc = error["loc"]
        if len(loc) > 1 and loc[0] == "body":
            field = " -> ".join(str(loc) for loc in loc[1:])
        else:
            field = " -> ".join(str(loc) for loc in loc)
        
        errors.append(f"{field}: {error['msg']}")
    
    error_message = "; ".join(errors)
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": error_message
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail
        }
    )

# --- HTML-страницы ---

# Обработчик GET-запроса на корневой путь ("/").
# Возвращает главную страницу (index.html) с использованием шаблона Jinja2.
@app.get("/", response_class=HTMLResponse, tags=["Тестирование"])
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Обработчик GET-запроса на страницу входа ("/login").
# Возвращает страницу входа (login.html).
@app.get("/login", response_class=HTMLResponse, tags=["Тестирование"])
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Обработчик POST-запроса на страницу входа ("/login").
# Принимает email и пароль из формы, проверяет их корректность,
# создаёт токен доступа и перенаправляет пользователя на страницу профиля.
@app.post("/login")
async def login_form(
    request: Request,
    email: str = Form(...),  # Получаем email из формы
    password: str = Form(...),  # Получаем пароль из формы
    db: Session = Depends(get_db)  # Получаем сессию базы данных
):
    try:
        # Ищем пользователя в базе данных по email.
        user = db.query(models.User).filter(models.User.email == email).first()
        user_not_found = user is None  # Флаг: пользователь не найден

        # Если пользователь не найден, возвращаем страницу входа с ошибкой.
        if user_not_found:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Неверный email или пароль"
            })

        # Проверяем корректность пароля.
        password_correct = auth_utils.verify_password(password, user.password_hash)
        # Проверяем, активен ли пользователь.
        user_active = user.is_active
        # Флаги: неверный пароль или неактивный пользователь.
        password_invalid = not password_correct
        user_inactive = not user_active

        # Если пароль неверный, возвращаем страницу входа с ошибкой.
        if password_invalid:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Неверный email или пароль"
            })

        # Если пользователь неактивен, возвращаем страницу входа с ошибкой.
        if user_inactive:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Пользователь деактивирован"
            })

        # Создаём токен доступа с указанием времени истечения.
        access_token_expires = timedelta(minutes=auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_utils.create_access_token(
            data={"sub": user.email, "role": user.role},
            expires_delta=access_token_expires
        )

        # Создаём ответ с перенаправлением на страницу профиля.
        response = RedirectResponse(url="/profile", status_code=303)
        # Сохраняем токен в cookies для дальнейшей аутентификации.
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,  # Запрещаем доступ к cookie через JavaScript
            max_age=3600,  # Время жизни cookie в секундах (1 час)
            secure=False,  # Включить для HTTPS
            samesite="lax"  # Защита от CSRF-атак
        )

        return response

    except Exception as e:
        # В случае ошибки возвращаем страницу входа с сообщением об ошибке.
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Ошибка сервера: {str(e)}"
        })

# Обработчик GET-запроса на страницу регистрации ("/register").
# Возвращает страницу регистрации (register.html).
@app.get("/register", response_class=HTMLResponse, tags=["Тестирование"])
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Обработчик POST-запроса на страницу регистрации ("/register").
# Принимает данные из формы, проверяет их, создаёт нового пользователя и перенаправляет на страницу входа.
@app.post("/register")
async def register_form(
    request: Request,
    email: str = Form(...),  # Получаем email из формы
    username: str = Form(...),  # Получаем username из формы
    password: str = Form(...),  # Получаем пароль из формы
    db: Session = Depends(get_db)  # Получаем сессию базы данных
):
    try:
        # Проверяем, существует ли пользователь с таким email.
        existing_user = db.query(models.User).filter(
            models.User.email == email
        ).first()
        email_alrady_used = existing_user is not None  # Флаг: email уже используется

        # Если email уже используется, возвращаем страницу регистрации с ошибкой.
        if email_alrady_used:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Пользователь с таким email уже существует"
            })

        # Проверяем, существует ли пользователь с таким username.
        existing_username = db.query(models.User).filter(
            models.User.username == username
        ).first()
        username_alredy_used = existing_username is not None  # Флаг: username уже используется

        # Если username уже используется, возвращаем страницу регистрации с ошибкой.
        if username_alredy_used:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Пользователь с таким username уже существует"
            })

        # Проверяем длину username.
        username_short = len(username) < 3
        username_long = len(username) > 50
        username_invalid = username_short or username_long  # Флаг: некорректная длина username

        # Если длина username некорректна, возвращаем страницу регистрации с ошибкой.
        if username_invalid:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Username должен быть от 3 до 50 символов"
            })

        # Проверяем длину пароля.
        password_short = len(password) < 6
        password_invalid = password_short  # Флаг: пароль слишком короткий

        # Если пароль слишком короткий, возвращаем страницу регистрации с ошибкой.
        if password_short:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Пароль должен содержать минимум 6 символов"
            })

        # Хешируем пароль для безопасного хранения.
        hashed_password = auth_utils.get_password_hash(password)
        # Создаём нового пользователя в базе данных.
        db_user = models.User(
            email=email,
            username=username,
            password_hash=hashed_password,
            role=UserRole.USER.value  # По умолчанию роль "user"
        )

        # Добавляем пользователя в базу данных и сохраняем изменения.
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Возвращаем страницу входа с сообщением об успешной регистрации.
        return templates.TemplateResponse("login.html", {
            "request": request,
            "success": "Регистрация успешна! Теперь вы можете войти."
        })

    except Exception as e:
        # В случае ошибки откатываем изменения в базе данных и возвращаем страницу регистрации с ошибкой.
        db.rollback()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": f"Ошибка регистрации: {str(e)}"
        })

# Обработчик GET-запроса на страницу профиля ("/profile").
# Проверяет токен доступа и возвращает страницу профиля с данными пользователя.
@app.get("/profile", response_class=HTMLResponse, tags=["Тестирование"])
async def profile_page(request: Request, db: Session = Depends(get_db)):
    # Получаем токен доступа из cookies.
    token = request.cookies.get("access_token")
    token_invalid = token is None  # Флаг: токен отсутствует

    # Если токен отсутствует, перенаправляем на страницу входа.
    if token_invalid:
        return RedirectResponse(url="/login")

    # Проверяем валидность токена.
    payload = auth_utils.verify_token(token)
    payload_invalid = payload is None  # Флаг: токен невалиден

    # Если токен невалиден, удаляем cookie и перенаправляем на страницу входа.
    if payload_invalid:
        response = RedirectResponse(url="/login")
        response.delete_cookie("access_token")
        return response

    # Получаем email пользователя из токена.
    email = payload.get("sub")
    email_invalid = email is None  # Флаг: email отсутствует в токене

    # Если email отсутствует, удаляем cookie и перенаправляем на страницу входа.
    if email_invalid:
        response = RedirectResponse(url="/login")
        response.delete_cookie("access_token")
        return response

    # Ищем пользователя в базе данных по email.
    user = db.query(models.User).filter(models.User.email == email).first()
    user_invalid = user is None  # Флаг: пользователь не найден

    # Если пользователь не найден, удаляем cookie и перенаправляем на страницу входа.
    if user_invalid:
        response = RedirectResponse(url="/login")
        response.delete_cookie("access_token")
        return response

    # Возвращаем страницу профиля с данными пользователя.
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user
    })

# Обработчик GET-запроса на выход ("/logout").
# Удаляет cookie с токеном и перенаправляет на главную страницу.
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response
    
    
# --- API эндпоинты ---

# Обработчик POST-запроса на регистрацию пользователя через API ("/api/register").
@app.post("/api/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Всё для Фронта"])
async def api_register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя в системе.
    
    Создает учетную запись пользователя с указанными данными.
    Проверяет уникальность email и username перед созданием.
    
    **Требования:**
    - Email должен быть уникальным и валидным
    - Username должен быть уникальным, от 3 до 50 символов
    - Пароль должен содержать минимум 6 символов
    - Username может содержать только буквы, цифры, underscores и дефисы
    
    **Возвращает:**
    - **id**: Уникальный идентификатор пользователя
    - **email**: Email пользователя
    - **username**: Имя пользователя
    - **role**: Роль пользователя (по умолчанию "user")
    - **is_active**: Статус активности (по умолчанию True)
    - **created_at**: Дата и время создания учетной записи
    
    **Ошибки:**
    - 400: Пользователь с таким email уже существует
    - 400: Пользователь с таким username уже существует
    - 422: Невалидные данные (некорректный email, короткий username или пароль)
    """
    # Проверяем, существует ли пользователь с таким email.
    existing_user = db.query(models.User).filter(
        models.User.email == user_data.email
    ).first()

    # Если email уже используется, возвращаем ошибку.
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )

    # Проверяем, существует ли пользователь с таким username.
    existing_username = db.query(models.User).filter(
        models.User.username == user_data.username
    ).first()

    # Если username уже используется, возвращаем ошибку.
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким username уже существует"
        )

    # Хешируем пароль.
    hashed_password = auth_utils.get_password_hash(user_data.password)
    # Создаём нового пользователя в базе данных.
    db_user = models.User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed_password,
        role=UserRole.USER.value
    )

    # Добавляем пользователя в базу данных и сохраняем изменения.
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Возвращаем данные созданного пользователя.
    return db_user

# Обработчик POST-запроса на вход пользователя через API ("/api/login").
@app.post("/api/login", response_model=Token, tags=["Всё для Фронта"])
async def api_login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Аутентификация пользователя и выдача токенов доступа.
    
    Проверяет учетные данные пользователя и выдает пару токенов:
    - Access token для доступа к защищенным ресурсам
    - Refresh token для обновления access token
    
    **Требования:**
    - Email должен существовать в системе
    - Пароль должен быть корректным
    - Учетная запись должна быть активной
    
    **Возвращает:**
    - **access_token**: JWT access token (срок жизни 30 минут)
    - **refresh_token**: JWT refresh token (срок жизни 30 дней)
    - **token_type**: Тип токена (bearer)
    - **role**: Роль пользователя для авторизации
    
    **Ошибки:**
    - 401: Неверный email или пароль
    - 401: Пользователь деактивирован
    - 422: Невалидные данные (некорректный email или пароль)
    
    **Примечание:**
    - Refresh token сохраняется в памяти сервера
    - При перезагрузке сервера все refresh токены сбрасываются
    - Access token должен передаваться в заголовке Authorization: Bearer <token>
    """
    # Ищем пользователя в базе данных по email.
    user = db.query(models.User).filter(models.User.email == user_data.email).first()

    # Если пользователь не найден, возвращаем ошибку.
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )

    # Проверяем корректность пароля.
    if not auth_utils.verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )

    # Проверяем, активен ли пользователь.
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь деактивирован"
        )

    # Создаем оба токена
    access_token_expires = timedelta(minutes=auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_utils.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    refresh_token_expires = timedelta(days=auth_utils.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = auth_utils.create_refresh_token(
        data={"sub": user.email}
    )
    
    # Сохраняем refresh токен в памяти (НЕ в БД)
    auth_utils.store_refresh_token(
        token=refresh_token,
        user_email=user.email,
        expires_at=datetime.utcnow() + refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "role": user.role
    }

# Обработчик GET-запроса для получения данных текущего пользователя через API ("/api/me").
# Проверяет токен доступа и возвращает данные пользователя.
@app.get("/api/me", response_model=UserResponse, tags=["Всё для Фронта"])
async def api_get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # Получаем данные авторизации
    db: Session = Depends(get_db)  # Получаем сессию базы данных
):
    # Получаем токен из данных авторизации.
    token = credentials.credentials
    # Проверяем валидность токена.
    payload = auth_utils.verify_token(token)

    # Если токен невалиден, возвращаем ошибку.
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен"
        )

    # Получаем email пользователя из токена.
    email = payload.get("sub")
    # Если email отсутствует, возвращаем ошибку.
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен"
        )

    # Ищем пользователя в базе данных по email.
    user = db.query(models.User).filter(models.User.email == email).first()
    # Если пользователь не найден, возвращаем ошибку.
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    # Возвращаем данные пользователя.
    return user

# Обработчик GET-запроса для доступа к админ-панели ("/api/admin").
# Проверяет токен доступа и роль пользователя.
@app.get("/api/admin", tags=["Всё для Фронта"])
async def admin_only(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # Получаем данные авторизации
    db: Session = Depends(get_db)  # Получаем сессию базы данных
):
    # Получаем токен из данных авторизации.
    token = credentials.credentials
    # Проверяем валидность токена.
    payload = auth_utils.verify_token(token)

    # Если токен невалиден, возвращаем ошибку.
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")

    # Получаем роль пользователя из токена.
    role = payload.get("role")
    # Если роль не "admin", возвращаем ошибку.
    if role != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    # Возвращаем сообщение о доступе к админ-панели.
    return {"message": "Добро пожаловать в админ-панель!"}

# Обновление access токена по refresh токену
@app.post("/api/refresh", tags=["Всё для Фронта"])
async def refresh_token(
    refresh_token_request: RefreshToken,
    db: Session = Depends(get_db)
):
    """
    Обновление access токена с помощью refresh токена.
    
    Используется когда access token истек, но refresh token еще действителен.
    Возвращает новый access token для продолжения работы с API.
    
    **Требования:**
    - Refresh token должен быть валидным JWT
    - Refresh token должен существовать в памяти сервера
    - Refresh token не должен быть отозван
    - Refresh token не должен быть просрочен
    - Пользователь должен существовать и быть активным
    
    **Возвращает:**
    - **access_token**: Новый JWT access token
    - **token_type**: Тип токена (bearer)
    
    **Ошибки:**
    - 401: Невалидный, отозванный, просроченный или не найденный refresh token
    - 401: Пользователь не найден или неактивен
    """
    # Извлекаем строку токена из объекта модели
    refresh_token_str = refresh_token_request.refresh_token
    
    # Проверяем JWT подпись
    payload = auth_utils.verify_token(refresh_token_str)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Проверяем наличие в памяти
    stored_token = auth_utils.get_refresh_token(refresh_token_str)
    if not stored_token:
        raise HTTPException(status_code=401, detail="Refresh token not found")
    
    # Проверяем не отозван ли
    if stored_token['revoked']:
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    
    # Проверяем не истек ли
    if stored_token['expires_at'] < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")
    
    # Получаем пользователя
    user = db.query(models.User).filter(models.User.email == stored_token['user_email']).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    # Создаем новый access токен
    access_token_expires = timedelta(minutes=auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = auth_utils.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@app.post("/api/logout", tags=["Всё для Фронта"])
async def api_logout(
    refresh_token_request: RefreshToken,
    response: Response = None
):
    """
    Выход из учетной записи. Отзыв refresh токена на сервере.
    
    Используется для безопасного завершения сессии пользователя.
    Отзывает переданный refresh token на сервере и очищает cookies в браузере.
    
    **Что происходит:**
    - Refresh token отзывается на сервере
    - Удаляются cookies с access_token и refresh_token
    - Сессия полностью завершается на клиенте и сервере
    
    **Требования:**
    - Refresh token должен быть передан в теле запроса
    - Refresh token должен быть валидным JWT
    - Refresh token должен существовать в памяти сервера
    - Refresh token не должен быть уже отозван
    
    **Возвращает:**
    - **message**: Статус операции
    - **detail**: Детальное описание результата
    
    **Ошибки:**
    - 400: Refresh token не передан
    - 400: Невалидный refresh token
    - 400: Refresh token не найден или уже отозван
    - 400: Refresh token уже отозван ранее
    """
    # Извлекаем строку токена из объекта модели
    refresh_token_str = refresh_token_request.refresh_token
    
    # Проверяем, что токен передан
    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token обязателен"
        )
    
    # Проверяем валидность JWT токена
    payload = auth_utils.verify_token(refresh_token_str)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невалидный refresh token"
        )
    
    # Проверяем, существует ли токен в хранилище
    stored_token = auth_utils.get_refresh_token(refresh_token_str)
    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token не найден или уже отозван"
        )
    
    # Проверяем, не отозван ли токен уже
    if stored_token['revoked']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token уже отозван"
        )
    
    # Отзываем токен на сервере
    auth_utils.revoke_refresh_token(refresh_token_str)
    
    # Очищаем cookies в браузере
    if response:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
    
    return {
        "message": "Успешный выход из системы",
        "detail": "Refresh token отозван и cookies очищены"
    }

@app.post("/api/files/upload", tags=["Файловое хранилище"])
async def upload_file(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Загрузка файла в хранилище пользователя с проверкой квоты.
    
    Требует авторизации через Bearer token.
    Файл сохраняется с уникальным именем для безопасности.
    Проверяет не превышена ли квота хранилища.
    
    **Возвращает:**
    - Информация о загруженном файле
    
    **Ошибки:**
    - 401: Невалидный токен
    - 400: Превышена квота хранилища
    - 500: Ошибка загрузки файла
    """
    # Проверяем токен и получаем пользователя
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Используем фасад для загрузки файла (передаем db для проверки квоты)
    file_info = await file_storage.upload_file(file, user.id, db)
    return file_info

@app.delete("/api/files/{filename}", tags=["Файловое хранилище"])
async def delete_file(
    filename: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Удаление файла из хранилища пользователя.
    
    Требует авторизации через Bearer token.
    Удаляет файл по имени.
    
    **Ошибки:**
    - 401: Невалидный токен
    - 404: Файл не найден
    - 500: Ошибка удаления файла
    """
    # Проверяем токен и получаем пользователя
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Используем фасад для удаления файла
    result = await file_storage.delete_file(filename, user.id)
    return {"message": "Файл успешно удален", "filename": filename}

@app.put("/api/files/rename", tags=["Файловое хранилище"])
async def rename_file(
    rename_request: FileRenameRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Переименование файла в хранилище пользователя.
    
    Требует авторизации через Bearer token.
    Изменяет имя файла на новое.
    
    **Ошибки:**
    - 401: Невалидный токен
    - 404: Файл не найден
    - 400: Файл с таким именем уже существует
    - 500: Ошибка переименования файла
    """
    # Проверяем токен и получаем пользователя
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Используем фасад для переименования файла
    result = await file_storage.rename_file(
        rename_request.old_filename,
        rename_request.new_filename,
        user.id
    )
    return result

@app.get("/api/files", tags=["Файловое хранилище"])
async def get_files(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Получение списка файлов пользователя.
    
    Требует авторизации через Bearer token.
    Возвращает список всех файлов пользователя.
    
    **Возвращает:**
    - Список файлов с информацией о каждом
    
    **Ошибки:**
    - 401: Невалидный токен
    - 500: Ошибка получения списка файлов
    """
    # Проверяем токен и получаем пользователя
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Используем фасад для получения списка файлов
    files = await file_storage.get_user_files(user.id)
    return {"files": files}

@app.get("/api/storage/info", tags=["Файловое хранилище"])
async def get_storage_info(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Получение информации о хранилище пользователя.
    
    Требует авторизации через Bearer token.
    Возвращает информацию о квоте и использованном месте.
    
    **Возвращает:**
    - **quota**: Общая квота в байтах
    - **used**: Использовано байт
    - **available**: Доступно байт
    - **usage_percentage**: Процент использования
    - **formatted**: Отформатированные значения для отображения
    """
    # Проверяем токен и получаем пользователя
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    storage_info = await file_storage.get_user_storage_info(user.id, db)
    return storage_info

@app.put("/api/admin/users/{user_id}/quota", tags=["Администрирование"])
async def update_user_quota(
    user_id: int,
    quota_update: UserQuotaUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Изменение квоты хранилища пользователя (только для администраторов).
    
    Требует авторизации через Bearer token с ролью admin.
    Позволяет изменить лимит хранилища для пользователя.
    
    **Параметры:**
    - **user_id**: ID пользователя
    - **quota**: Новая квота в байтах
    
    **Возвращает:**
    - Обновленная информация о пользователе
    
    **Ошибки:**
    - 401: Невалидный токен
    - 403: Недостаточно прав
    - 404: Пользователь не найден
    """
    # Проверяем права администратора
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # Находим пользователя
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Проверяем, что новая квота не меньше текущего использования
    current_usage = await file_storage.get_user_storage_usage(user_id)
    if quota_update.quota < current_usage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Новая квота не может быть меньше текущего использования ({file_storage.format_bytes(current_usage)})"
        )
    
    # Обновляем квоту
    user.quota = quota_update.quota
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Квота обновлена",
        "user_id": user.id,
        "username": user.username,
        "new_quota": quota_update.quota,
        "new_quota_formatted": file_storage.format_bytes(quota_update.quota),
        "current_usage": current_usage,
        "current_usage_formatted": file_storage.format_bytes(current_usage)
    }

# Точка входа для запуска приложения.
if __name__ == "__main__":
    import uvicorn
    # Запускаем сервер Uvicorn на хосте 0.0.0.0 и порту 8000.
    uvicorn.run(app, host="0.0.0.0", port=8000)
