# Импортируем необходимые модули и классы из FastAPI для создания API,
# работы с зависимостями, обработки ошибок, работы с HTTP-запросами и шаблонами.
# Также импортируем модули для работы с базой данных, моделями и утилитами аутентификации.
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
import auth_utils
from database import get_db
from models import UserCreate, UserLogin, UserResponse, Token, UserRole
from datetime import timedelta

# Создаём экземпляр FastAPI с указанием метаданных (название и версия API).
app = FastAPI(title="File Storage Auth API", version="1.0.0")

# Настраиваем шаблонизатор Jinja2 для рендеринга HTML-страниц.
# Указываем директорию, где хранятся шаблоны.
templates = Jinja2Templates(directory="templates")

# Создаём объект для работы с HTTP Bearer авторизацией.
security = HTTPBearer()

# --- HTML-страницы ---

# Обработчик GET-запроса на корневой путь ("/").
# Возвращает главную страницу (index.html) с использованием шаблона Jinja2.
@app.get("/", response_class=HTMLResponse, tags=["Страницы"])
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Обработчик GET-запроса на страницу входа ("/login").
# Возвращает страницу входа (login.html).
@app.get("/login", response_class=HTMLResponse, tags=["Страницы"])
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
@app.get("/register", response_class=HTMLResponse, tags=["Страницы"])
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
@app.get("/profile", response_class=HTMLResponse, tags=["Страницы"])
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
# Принимает данные пользователя, проверяет их, создаёт нового пользователя и возвращает его данные.
@app.post("/api/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def api_register(user_data: UserCreate, db: Session = Depends(get_db)):
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
# Принимает данные пользователя, проверяет их и возвращает токен доступа.
@app.post("/api/login", response_model=Token)
async def api_login(user_data: UserLogin, db: Session = Depends(get_db)):
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

    # Создаём токен доступа.
    access_token_expires = timedelta(minutes=auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_utils.create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )

    # Возвращаем токен доступа.
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }

# Обработчик GET-запроса для получения данных текущего пользователя через API ("/api/me").
# Проверяет токен доступа и возвращает данные пользователя.
@app.get("/api/me", response_model=UserResponse)
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
@app.get("/api/admin")
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

# Точка входа для запуска приложения.
if __name__ == "__main__":
    import uvicorn
    # Запускаем сервер Uvicorn на хосте 0.0.0.0 и порту 8000.
    uvicorn.run(app, host="0.0.0.0", port=8000)
