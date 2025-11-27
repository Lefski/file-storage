# Импортируем необходимые модули и классы из FastAPI для создания API,
# работы с зависимостями, обработки ошибок, работы с HTTP-запросами и шаблонами.
# Также импортируем модули для работы с базой данных, моделями и утилитами аутентификации.
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, UploadFile, Query, Response, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import models
import auth_utils
from dependencies.services import get_file_service, get_quota_service
from database import get_db
from models import UserCreate, UserLogin, UserResponse, Token, UserRole, RefreshToken, FileRenameRequest, UserQuotaUpdate, AdminUserListResponse
from datetime import timedelta, datetime
from typing import List, Optional, Callable
from file_models import Files, FileInfoResponse, FileRename, Folder, FolderCreate, FolderResponse, FileMove
from chain_of_duties import (AuthCheckHandler, QuotaCheckHandler, FileTypeCheckHandler, FolderCheckHandler, SaveFileHandler,
    AuthDeleteCheckHandler, FileAccessCheckHandler, DeleteFileHandler,
    AuthFolderCheckHandler, NameFolderCheckHandler, ParentFolderCheckHandler, CreateFolderHandler,
    AuthMoveCheckHandler, FileMoveCheckHandler, FolderMoveCheckHandler, UpdateMoveHandler)

from services.file_service import FileService
from services.quota_service import QuotaService
from dependencies.services import get_file_service, get_quota_service

import file_utils
import os
import shutil
import zipfile
import tempfile


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

@app.middleware("http")
async def add_user_to_request(request: Request, call_next: Callable):
    # Получаем пользователя и добавляем его в request.state
    db = next(get_db())
    try:
        user = get_current_user(request, db)
        request.state.user = user
        request.state.db = db
        response = await call_next(request)
        return response
    except Exception as e:
        # В случае ошибки все равно продолжаем
        request.state.user = None
        request.state.db = db
        response = await call_next(request)
        return response
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = auth_utils.verify_token(token)
    if not payload:
        return None

    email = payload.get("sub")
    if not email:
        return None

    user = db.query(models.User).filter(models.User.email == email).first()
    return user

async def get_current_admin(
    user: models.User = Depends(get_current_user)
) -> models.User:
    """Зависимость для проверки прав администратора"""
    if user.role != "admin":  # Предполагаем, что в модели User есть поле role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    return user

# --- HTML-страницы ---

# Обработчик GET-запроса на корневой путь ("/").
# Возвращает главную страницу (index.html) с использованием шаблона Jinja2.
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Обработчик GET-запроса на страницу входа ("/login").
# Возвращает страницу входа (login.html).
@app.get("/login", response_class=HTMLResponse)
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
@app.get("/register", response_class=HTMLResponse)
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
# Обработчик GET-запроса на страницу профиля ("/profile").
# Проверяет токен доступа и возвращает страницу профиля с данными пользователя.
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request, 
    db: Session = Depends(get_db),
    search: str = Query(None),
    folder_id: int = Query(None)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    # Получаем папки пользователя
    folders = db.query(Folder).filter(Folder.user_id == user.id).all()
    
    # Получаем файлы с учетом поиска и папки
    query = db.query(Files).filter(Files.user_id == user.id)
    
    if search and search.strip():
        # Поиск по всем файлам пользователя независимо от папки
        search_term = f"%{search.strip()}%"
        query = query.filter(Files.filename.ilike(search_term))
        # Если идет поиск, игнорируем folder_id и показываем все найденные файлы
        files = query.all()
        
        current_folder = None
        search_mode = True
    else:
        # Обычный режим - файлы в конкретной папке
        if folder_id:
            query = query.filter(Files.folder_id == folder_id)
            current_folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
        else:
            query = query.filter(Files.folder_id.is_(None))
            current_folder = None
        files = query.all()
        search_mode = False

    # Рассчитываем статистику использования пространства
    total_files_count = db.query(Files).filter(Files.user_id == user.id).count()
    total_folders_count = len(folders)
    

    
    # Убедимся, что у пользователя есть квота (если нет - установим 1 ГБ)
    if not user.quota:
        user.quota = 1024 * 1024 * 1024  # 1 ГБ
        db.commit()
    
    if not user.used_space:
        user.used_space = 0
        db.commit()

    # Рассчитываем проценты для прогресс-бара
    used_gb = round(user.used_space / (1024 * 1024 * 1024), 2)
    total_gb = round(user.quota / (1024 * 1024 * 1024), 2)
    used_percent = round((user.used_space / user.quota) * 100, 1) if user.quota > 0 else 0
    
    # Определяем класс для прогресс-бара
    if used_percent < 70:
        progress_class = "bg-success"
    elif used_percent < 90:
        progress_class = "bg-warning"
    else:
        progress_class = "bg-danger"

    # Возвращаем страницу профиля с данными пользователя.
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "files": files,
        "folders": folders,
        "search_query": search,
        "current_folder": current_folder,
        "search_mode": search_mode,
        "total_files_count": total_files_count,
        "total_folders_count": total_folders_count,
        "used_gb": used_gb,
        "total_gb": total_gb,
        "used_percent": used_percent,
        "progress_class": progress_class
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

@app.post("/profile/upload")
async def upload_profile_file(
    request: Request,
    file: UploadFile = UploadFile(...),
    folder_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    def get_redirect_url(folder_id: Optional[int]) -> str:
        """Вспомогательная функция для формирования URL перенаправления."""
        return f"/profile?folder_id={folder_id}" if folder_id else "/profile"
    
    try:
        # Проверяем корректность folder_id
        if folder_id is not None and folder_id < 0:
            raise HTTPException(status_code=400, detail="Некорректный идентификатор папки")# Проверяем корректность folder_id
        
        # обьявление операций цепи пользователя
        auth_handler = AuthCheckHandler()
        quota_handler = QuotaCheckHandler()
        file_type_handler = FileTypeCheckHandler()
        folder_handler = FolderCheckHandler()
        save_handler = SaveFileHandler()

        # обьявление цепи
        auth_handler.next_handler = quota_handler
        quota_handler.next_handler = file_type_handler
        file_type_handler.next_handler = folder_handler
        folder_handler.next_handler = save_handler

        # запуск цепи
        result = auth_handler.handle(request, file, folder_id, db)

        # Перенаправляем на страницу профиля
        redirect_url = f"/profile?folder_id={folder_id}" if folder_id else "/profile"
        return RedirectResponse(url=redirect_url, status_code=303)

    except HTTPException as e:
        redirect_url = f"/profile?folder_id={folder_id}" if folder_id else "/profile"
        return RedirectResponse(url=redirect_url, status_code=303)

    
    except Exception as e:
        db.rollback()
        # В случае ошибки возвращаем на страницу профиля
        print(f"file uppload error: {str(e)}")
        redirect_url = get_current_user(folder_id)
        return RedirectResponse(url=redirect_url, status_code=303)


# изменение имени файла пользователя
@app.post("/profile/rename/{file_id}", response_class=RedirectResponse)
async def rename_profile_file(
    file_id: int,
    request: Request,
    new_filename: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    file = db.query(Files).filter(Files.id == file_id, Files.user_id == user.id).first()
    if not file:
        return RedirectResponse(url="/profile", status_code=303)

    if not new_filename:
        return RedirectResponse(url="/profile", status_code=303)

    if not new_filename.strip():
        raise HTTPException(status_code=400, detail="Имя файла не может быть пустым")

    if any(char in new_filename for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
        raise HTTPException(status_code=400, detail="Имя файла содержит запрещённые символы")

    file_dir = os.path.dirname(file.file_path)
    new_file_path = os.path.join(file_dir, new_filename)

    if os.path.exists(new_file_path):
        raise HTTPException(status_code=400, detail="Файл с таким именем уже существует")

    try:
        file_utils.rename_file_on_disk(file.file_path, new_file_path)
        file.filename = new_filename
        file.file_path = new_file_path
        file.updated_at = func.now()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при переименовании файла: {str(e)}")

    return RedirectResponse(url="/profile", status_code=303)

# Скачивание файла пользователя
@app.get("/profile/download/{file_id}")
async def download_profile_file(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    file = db.query(Files).filter(Files.id == file_id, Files.user_id == user.id).first()
    if not file:
        raise HTTPException(status_code=404, detail="Файл не найден")

    if not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="Файл не найден на сервере")

    # Возвращаем файл для скачивания
    return FileResponse(
        path=file.file_path,
        filename=file.filename,
        media_type='application/octet-stream'
    )


@app.post("/profile/download-multiple")
async def download_multiple_files(
    request: Request,
    file_ids: List[int] = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    # Получаем файлы пользователя
    files = db.query(Files).filter(
        Files.id.in_(file_ids),
        Files.user_id == user.id
    ).all()

    if not files:
        raise HTTPException(status_code=404, detail="Файлы не найдены")

    # Создаем временный ZIP архив
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        with zipfile.ZipFile(tmp_file.name, 'w') as zipf:
            for file in files:
                if os.path.exists(file.file_path):
                    # Добавляем файл в архив с исходным именем
                    zipf.write(file.file_path, file.filename)

        # Возвращаем ZIP архив
        return FileResponse(
            path=tmp_file.name,
            filename=f"files_{user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            media_type='application/zip'
        )
    
    
# Создание новой папки
@app.post("/profile/folders/create")
async def create_folder(
    request: Request,
    name: str = Form(...),
    parent_folder_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # Обрабатываем parent_folder_id (может быть пустой строкой)
        target_parent_folder_id = None
        if parent_folder_id and parent_folder_id.strip():
            try:
                folder_id_int = int(parent_folder_id)
                target_parent_folder_id = folder_id_int
            except ValueError:
                pass

        # Создаём цепочку обработчиков
        auth_folder_handler = AuthFolderCheckHandler()
        name_folder_handler = NameFolderCheckHandler()
        parent_folder_handler = ParentFolderCheckHandler()
        create_folder_handler = CreateFolderHandler()

        # Собираем цепочку
        auth_folder_handler.next_handler = name_folder_handler
        name_folder_handler.next_handler = parent_folder_handler
        parent_folder_handler.next_handler = create_folder_handler

        # Запускаем цепочку
        result = auth_folder_handler.handle(request, name, target_parent_folder_id, db)

        # Перенаправляем на страницу профиля
        redirect_url = f"/profile?folder_id={target_parent_folder_id}" if target_parent_folder_id else "/profile"
        return RedirectResponse(url=redirect_url, status_code=303)

    except HTTPException as e:
        redirect_url = f"/profile?folder_id={target_parent_folder_id}" if target_parent_folder_id else "/profile"
        return RedirectResponse(url=redirect_url, status_code=303)


# Удаление файла
@app.post("/profile/delete/{file_id}", response_class=RedirectResponse)
async def delete_file(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
         # обьявление операций цепи пользователя
        auth_delete_handler = AuthDeleteCheckHandler()
        access_delete_handler = FileAccessCheckHandler()
        delete_file_handler = DeleteFileHandler()

        # сборка цепи
        auth_delete_handler.next_handler = access_delete_handler
        access_delete_handler.next_handler = delete_file_handler

        # запуск цепи
        result = auth_delete_handler.handle(request, file_id, db)

        # Перенаправляем на страницу профиля
        return RedirectResponse(url="/profile", status_code=303)

    except HTTPException as e:
        return RedirectResponse(url="/profile", status_code=303)

# Удаление папки
@app.post("/profile/folders/delete/{folder_id}", response_class=RedirectResponse)
async def delete_folder(
    folder_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
    if not folder:
        return RedirectResponse(url="/profile", status_code=303)

    # Нельзя удалить корневую папку
    if folder.name == "Корневая папка":
        return RedirectResponse(url="/profile", status_code=303)

    # Удаляем все файлы в папке
    files = db.query(Files).filter(Files.folder_id == folder_id).all()
    for file in files:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
        db.delete(file)

    # Удаляем подпапки рекурсивно
    subfolders = db.query(Folder).filter(Folder.parent_folder_id == folder_id).all()
    for subfolder in subfolders:
        # Рекурсивно удаляем подпапки
        await delete_folder_internal(subfolder.id, user.id, db)

    # Удаляем саму папку
    db.delete(folder)
    db.commit()

    return RedirectResponse(url="/profile", status_code=303)

async def delete_folder_internal(folder_id: int, user_id: int, db: Session):
    """Внутренняя функция для рекурсивного удаления папок"""
    # Удаляем файлы в папке
    files = db.query(Files).filter(Files.folder_id == folder_id).all()
    for file in files:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
        db.delete(file)

    # Удаляем подпапки
    subfolders = db.query(Folder).filter(Folder.parent_folder_id == folder_id).all()
    for subfolder in subfolders:
        await delete_folder_internal(subfolder.id, user_id, db)

    # Удаляем саму папку
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if folder:
        db.delete(folder)




@app.post("/api/move-file")
async def move_file(
    request: Request,
    move_data: FileMove,
    db: Session = Depends(get_db)
):
    try:
        # Создаём цепочку обработчиков
        auth_move_handler = AuthMoveCheckHandler()
        file_move_handler = FileMoveCheckHandler()
        folder_move_handler = FolderMoveCheckHandler()
        update_move_handler = UpdateMoveHandler()

        # Собираем цепочку
        auth_move_handler.next_handler = file_move_handler
        file_move_handler.next_handler = folder_move_handler
        folder_move_handler.next_handler = update_move_handler

        # Запускаем цепочку
        result = auth_move_handler.handle(request, move_data, db)

        # Возвращаем успешный ответ
        return {"message": "Файл успешно перемещен"}

    except HTTPException as e:
        raise e



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
    user: models.User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Переименование файла пользователя"""
    return await file_service.rename_file(
        rename_request.old_filename,
        rename_request.new_filename,
        user.id
    )

@app.get("/api/files", tags=["Файловое хранилище"])
async def get_files(
    user: models.User = Depends(get_current_user),
    file_service: FileService = Depends(get_file_service)
):
    """Получение списка файлов пользователя"""
    files = await file_service.get_user_files(user.id)
    return {"files": files}

@app.get("/api/storage/info", tags=["Файловое хранилище"])
async def get_storage_info(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    file_service: FileService = Depends(get_file_service)
):
    """Получение информации о хранилище пользователя"""
    return await file_service.get_user_storage_info(user.id, db)

@app.put("/api/admin/users/{user_id}/quota", tags=["Администрирование"])
async def update_user_quota(
    user_id: int,
    quota_update: UserQuotaUpdate,
    admin: models.User = Depends(get_current_admin),
    quota_service: QuotaService = Depends(get_quota_service)
):
    """Обновление квоты пользователя (только для администраторов)"""
    return await quota_service.update_user_quota(user_id, quota_update.quota)

@app.get("/api/admin/users", response_model=AdminUserListResponse, tags=["Администрирование"])
async def get_all_users(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Получение списка всех пользователей в системе (только для администраторов).
    
    Требует авторизации через Bearer token с ролью admin.
    Поддерживает пагинацию через параметры skip и limit.
    
    **Параметры запроса:**
    - **skip**: Количество записей для пропуска (по умолчанию 0)
    - **limit**: Максимальное количество записей (по умолчанию 100, максимум 1000)
    
    **Возвращает:**
    - **users**: Список пользователей с расширенной информацией
    - **total_count**: Общее количество пользователей
    
    **Информация о каждом пользователе:**
    - **id**: ID пользователя
    - **username**: Имя пользователя
    - **email**: Email пользователя
    - **role**: Роль пользователя
    - **is_active**: Статус активности
    - **created_at**: Дата регистрации
    - **quota**: Квота хранилища
    - **used_storage**: Использованное место
    - **storage_usage_percentage**: Процент использования хранилища
    
    **Ошибки:**
    - 401: Невалидный токен
    - 403: Недостаточно прав
    """
    # Проверяем права администратора
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    # Ограничиваем максимальный лимит
    if limit > 1000:
        limit = 1000
    
    # Получаем пользователей с пагинацией
    users_query = db.query(models.User)
    total_count = users_query.count()
    users = users_query.offset(skip).limit(limit).all()
    
    # Формируем расширенную информацию о пользователях
    users_with_storage = []
    for user in users:
        try:
            used_storage = await file_storage.get_user_storage_usage(user.id)
            storage_usage_percentage = round((used_storage / user.quota) * 100, 2) if user.quota > 0 else 0
            
            users_with_storage.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "quota": user.quota,
                "used_storage": used_storage,
                "storage_usage_percentage": storage_usage_percentage,
                "quota_formatted": file_storage.format_bytes(user.quota),
                "used_storage_formatted": file_storage.format_bytes(used_storage)
            })
        except Exception as e:
            # В случае ошибки получения информации о хранилище, используем значения по умолчанию
            users_with_storage.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "quota": user.quota,
                "used_storage": 0,
                "storage_usage_percentage": 0,
                "quota_formatted": file_storage.format_bytes(user.quota),
                "used_storage_formatted": "0 B"
            })
    
    return {
        "users": users_with_storage,
        "total_count": total_count
    }

@app.get("/api/admin/users/{user_id}/storage-details", tags=["Администрирование"])
async def get_user_storage_details(
    user_id: int,
    admin: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Получение детальной информации о хранилище пользователя (только для администраторов).
    
    Требует авторизации через Bearer token с ролью admin.
    Возвращает полную информацию о файлах и использовании хранилища.
    
    **Параметры:**
    - **user_id**: ID пользователя
    
    **Возвращает:**
    - Детальная информация о хранилище и файлах пользователя
    
    **Ошибки:**
    - 401: Невалидный токен
    - 403: Недостаточно прав
    - 404: Пользователь не найден
    """
    # Получаем полную информацию
    try:
        # Получаем содержимое корневой папки пользователя
        folder_content = await file_storage.get_folder_content(user_id, "")
        storage_info = await file_storage.get_user_storage_info(user_id, db)
        
        return {
            "user_id": user_id,
            "storage_info": storage_info,
            "files": folder_content.get("items", [])
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения информации о хранилище: {str(e)}"
        )

# Добавьте эти эндпоинты в main.py

@app.post("/api/folders", tags=["Файловое хранилище"])
async def create_folder(
    folder_data: models.FolderCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Создание новой папки
    
    Требует авторизации через Bearer token.
    Создает новую папку в указанном расположении.
    
    **Параметры:**
    - **folder_name**: Название папки
    - **parent_path**: Родительская папка (опционально)
    
    **Ошибки:**
    - 401: Невалидный токен
    - 400: Папка с таким именем уже существует
    - 500: Ошибка создания папки
    """
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    result = await file_storage.create_folder(
        folder_data.folder_name,
        user.id,
        folder_data.parent_path
    )
    return result

@app.get("/api/folders/content", response_model=models.FolderContentResponse, tags=["Файловое хранилище"])
async def get_folder_content(
    folder_path: str = "",
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Получение содержимого папки
    
    Требует авторизации через Bearer token.
    Возвращает список файлов и папок в указанной папке.
    
    **Параметры запроса:**
    - **folder_path**: Путь к папке (опционально)
    
    **Возвращает:**
    - **current_path**: Текущий путь
    - **items**: Список элементов (файлы и папки)
    - **storage_info**: Информация о хранилище
    
    **Ошибки:**
    - 401: Невалидный токен
    - 404: Папка не найдена
    - 500: Ошибка получения содержимого
    """
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    folder_content = await file_storage.get_folder_content(user.id, folder_path)
    storage_info = await file_storage.get_user_storage_info(user.id, db)
    
    return {
        "current_path": folder_content["current_path"],
        "items": folder_content["items"],
        "storage_info": storage_info
    }

@app.delete("/api/folders", tags=["Файловое хранилище"])
async def delete_folder(
    folder_path: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Удаление папки
    
    Требует авторизации через Bearer token.
    Удаляет папку и все её содержимое.
    
    **Параметры запроса:**
    - **folder_path**: Путь к папке для удаления
    
    **Ошибки:**
    - 401: Невалидный токен
    - 404: Папка не найдена
    - 400: Нельзя удалить корневую папку
    - 500: Ошибка удаления папки
    """
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    result = await file_storage.delete_folder(folder_path, user.id)
    return {"message": "Папка успешно удалена", "folder_path": folder_path}

@app.put("/api/folders/rename", tags=["Файловое хранилище"])
async def rename_folder(
    rename_request: models.FileRenameRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Переименование папки
    
    Требует авторизации через Bearer token.
    Изменяет название папки.
    
    **Параметры:**
    - **old_filename**: Старый путь к папке
    - **new_filename**: Новое название папки
    
    **Ошибки:**
    - 401: Невалидный токен
    - 404: Папка не найдена
    - 400: Папка с таким именем уже существует
    - 500: Ошибка переименования
    """
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    result = await file_storage.rename_folder(
        rename_request.old_filename,
        rename_request.new_filename,
        user.id
    )
    return result

# Обновим существующий эндпоинт загрузки файлов для поддержки папок
@app.post("/api/files/upload", tags=["Файловое хранилище"])
async def upload_file(
    file: UploadFile = File(...),
    folder_path: str = "",
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Загрузка файла в хранилище пользователя с поддержкой папок
    
    Требует авторизации через Bearer token.
    Файл сохраняется с оригинальным именем в указанной папке.
    
    **Параметры запроса:**
    - **folder_path**: Путь к папке для загрузки (опционально)
    
    **Возвращает:**
    - Информация о загруженном файле
    
    **Ошибки:**
    - 401: Невалидный токен
    - 400: Превышена квота хранилища
    - 500: Ошибка загрузки файла
    """
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    file_info = await file_storage.upload_file(file, user.id, db, folder_path)
    return file_info

# Обновим эндпоинт получения файлов пользователя
@app.get("/api/users/{user_id}/files", response_model=models.UserFilesResponse, tags=["Файловое хранилище"])
async def get_user_files(
    user_id: int,
    folder_path: str = "",
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Получение содержимого папки пользователя
    
    Требует авторизации через Bearer token.
    Обычные пользователи могут запрашивать только свои файлы.
    Администраторы могут запрашивать файлы любого пользователя.
    
    **Параметры запроса:**
    - **folder_path**: Путь к папке (опционально)
    
    **Возвращает:**
    - **user_id**: ID пользователя
    - **username**: Имя пользователя
    - **email**: Email пользователя
    - **files**: Список файлов и папок
    - **storage_info**: Информация о хранилище
    
    **Ошибки:**
    - 401: Невалидный токен
    - 403: Недостаточно прав
    - 404: Пользователь не найден
    """
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    current_user_email = payload.get("sub")
    current_user = db.query(models.User).filter(models.User.email == current_user_email).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="Текущий пользователь не найден")
    
    is_admin = current_user.role == "admin"
    is_own_files = current_user.id == user_id
    
    if not (is_admin or is_own_files):
        raise HTTPException(
            status_code=403, 
            detail="Недостаточно прав для просмотра файлов этого пользователя"
        )
    
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    folder_content = await file_storage.get_folder_content(user_id, folder_path)
    storage_info = await file_storage.get_user_storage_info(user_id, db)
    
    return {
        "user_id": target_user.id,
        "username": target_user.username,
        "email": target_user.email,
        "files": folder_content["items"],
        "storage_info": storage_info
    }

@app.post("/api/files/move", tags=["Файловое хранилище"])
async def move_file(
    move_request: models.FileMoveRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Перемещение файла между папками
    
    Требует авторизации через Bearer token.
    Перемещает файл из текущего расположения в указанную папку.
    
    **Параметры:**
    - **source_path**: Текущий путь к файлу
    - **target_folder**: Целевая папка
    - **new_filename**: Новое имя файла (опционально)
    
    **Возвращает:**
    - Информация о перемещенном файле
    
    **Ошибки:**
    - 401: Невалидный токен
    - 404: Исходный файл не найден
    - 400: Указанный путь не является файлом
    - 500: Ошибка перемещения файла
    
    **Примеры:**
    - Перемещение файла из корня в папку "documents":
    ```json
    {
        "source_path": "report.pdf",
        "target_folder": "documents"
    }
    ```
    - Перемещение с переименованием:
    ```json
    {
        "source_path": "documents/old_name.pdf",
        "target_folder": "archive",
        "new_filename": "new_name.pdf"
    }
    ```
    - Перемещение файла из подпапки:
    ```json
    {
        "source_path": "documents/projects/report.pdf",
        "target_folder": "archive/2024"
    }
    ```
    """
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    result = await file_storage.move_file(
        move_request.source_path,
        move_request.target_folder,
        user.id,
        move_request.new_filename
    )
    return result

@app.post("/api/folders/move", tags=["Файловое хранилище"])
async def move_folder(
    move_request: models.FileMoveRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Перемещение папки
    
    Требует авторизации через Bearer token.
    Перемещает папку из текущего расположения в указанную папку.
    
    **Параметры:**
    - **source_path**: Текущий путь к папке
    - **target_folder**: Целевая папка
    - **new_filename**: Новое имя папки (опционально)
    
    **Возвращает:**
    - Информация о перемещенной папке
    
    **Ошибки:**
    - 401: Невалидный токен
    - 404: Исходная папка не найдена
    - 400: Указанный путь не является папкой
    - 400: Невозможно переместить папку в саму себя
    - 500: Ошибка перемещения папки
    
    **Примеры:**
    - Перемещение папки в другую папку:
    ```json
    {
        "source_path": "projects",
        "target_folder": "archive/2024"
    }
    ```
    - Перемещение с переименованием:
    ```json
    {
        "source_path": "temp_projects",
        "target_folder": "archive",
        "new_filename": "projects_2024"
    }
    ```
    """
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    result = await file_storage.move_folder(
        move_request.source_path,
        move_request.target_folder,
        user.id,
        move_request.new_filename
    )
    return result

@app.post("/api/files/copy", tags=["Файловое хранилище"])
async def copy_file(
    move_request: models.FileMoveRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Копирование файла в другую папку
    
    Требует авторизации через Bearer token.
    Создает копию файла в указанной папке.
    
    **Параметры:**
    - **source_path**: Текущий путь к файлу
    - **target_folder**: Целевая папка
    - **new_filename**: Новое имя файла (опционально)
    
    **Возвращает:**
    - Информация о скопированном файле
    
    **Ошибки:**
    - 401: Невалидный токен
    - 404: Исходный файл не найден
    - 400: Указанный путь не является файлом
    - 500: Ошибка копирования файла
    """
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Для копирования сначала читаем файл, затем сохраняем в новом месте
    user_folder = file_storage.storage_path / str(user.id)
    source_file_path = user_folder / move_request.source_path
    
    if not source_file_path.exists() or not source_file_path.is_file():
        raise HTTPException(status_code=404, detail="Исходный файл не найден")
    
    # Определяем имя файла для копии
    if move_request.new_filename:
        target_filename = move_request.new_filename
    else:
        target_filename = source_file_path.name
    
    target_folder_path = user_folder / move_request.target_folder
    target_folder_path.mkdir(parents=True, exist_ok=True)
    target_file_path = target_folder_path / target_filename
    
    # Генерируем уникальное имя если файл уже существует
    if target_file_path.exists():
        target_filename = file_storage._generate_unique_filename(target_folder_path, target_filename)
        target_file_path = target_folder_path / target_filename
    
    # Копируем файл
    import shutil
    shutil.copy2(source_file_path, target_file_path)
    
    return {
        "source_path": move_request.source_path,
        "target_path": str(target_file_path.relative_to(user_folder)),
        "filename": target_filename,
        "target_folder": move_request.target_folder,
        "user_id": user.id,
        "copied_at": datetime.now().isoformat(),
        "operation": "copy"
    }

# Точка входа для запуска приложения.
if __name__ == "__main__":
    import uvicorn
    # Запускаем сервер Uvicorn на хосте 0.0.0.0 и порту 8000.
    uvicorn.run(app, host="0.0.0.0", port=8000)
