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
from database import get_db
from models import UserRole
from datetime import timedelta, datetime
from typing import List, Optional, Callable
from file_models import Files, Folder, FolderCreate, FolderResponse, FileMove
from chain_of_duties import (AuthCheckHandler, QuotaCheckHandler, FileTypeCheckHandler, FolderCheckHandler, SaveFileHandler,
    AuthDeleteCheckHandler, FileAccessCheckHandler, DeleteFileHandler,
    AuthFolderCheckHandler, NameFolderCheckHandler, ParentFolderCheckHandler, CreateFolderHandler,
    AuthMoveCheckHandler, FileMoveCheckHandler, FolderMoveCheckHandler, UpdateMoveHandler)

import file_utils
import os
import shutil
import zipfile
import tempfile


# Основной объект приложения FastAPI - корень всей системы
app = FastAPI(title="File Storage Auth API", version="1.0.0")

# Настройка CORS для разрешения кросс-доменных запросов (важно для веб-интерфейса)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # В разработке разрешаем все origins
    allow_credentials=True, # Разрешаем cookies для аутентификации
    allow_methods=["*"],    # Разрешаем все HTTP методы
    allow_headers=["*"],    # Разрешаем все заголовки
)

# Инициализация шаблонизатора Jinja2 для рендеринга HTML страниц
templates = Jinja2Templates(directory="templates")

# Создание объекта для HTTP Bearer авторизации
security = HTTPBearer()

# Кастомный middleware: добавляет информацию о пользователе в каждый запрос
# Этот middleware выполняется перед каждым HTTP запросом
@app.middleware("http")
async def add_user_to_request(request: Request, call_next: Callable):
    # Создаем новую сессию базы данных для этого запроса
    db = next(get_db())
    try:
        # Получаем текущего пользователя из токена в cookies
        user = get_current_user(request, db)
        # Сохраняем пользователя и БД в состоянии запроса для использования в обработчиках
        request.state.user = user
        request.state.db = db
        # Передаем управление следующему middleware или конечному обработчику
        response = await call_next(request)
        return response
    except Exception as e:
        # В случае ошибки все равно продолжаем обработку запроса
        request.state.user = None
        request.state.db = db
        response = await call_next(request)
        return response
    finally:
        # Всегда закрываем сессию БД
        db.close()

# Функция для получения текущего аутентифицированного пользователя
def get_current_user(request: Request, db: Session = Depends(get_db)):
    # Извлекаем токен из cookies браузера
    token = request.cookies.get("access_token")
    if not token:
        return None

    # Верифицируем JWT токен
    payload = auth_utils.verify_token(token)
    if not payload:
        return None

    # Извлекаем email из токена (стандартное поле 'sub' в JWT)
    email = payload.get("sub")
    if not email:
        return None

    # Находим пользователя в базе данных по email
    user = db.query(models.User).filter(models.User.email == email).first()
    return user

# ============================================================================
# ОСНОВНЫЕ HTML СТРАНИЦЫ
# ============================================================================

# Главная страница приложения
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Страница входа в систему
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Обработчик формы входа: аутентификация пользователя и установка токена
@app.post("/login")
async def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Поиск пользователя по email
        user = db.query(models.User).filter(models.User.email == email).first()
        user_not_found = user is None

        if user_not_found:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Неверный email или пароль"
            })

        # Проверка пароля
        password_correct = auth_utils.verify_password(password, user.password_hash)
        # Проверка активности пользователя
        user_active = user.is_active
        password_invalid = not password_correct
        user_inactive = not user_active

        if password_invalid:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Неверный email или пароль"
            })

        if user_inactive:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Пользователь деактивирован"
            })

        # Создание JWT токена доступа
        access_token_expires = timedelta(minutes=auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_utils.create_access_token(
            data={"sub": user.email, "role": user.role},
            expires_delta=access_token_expires
        )

        # Создание ответа с перенаправлением на профиль
        response = RedirectResponse(url="/profile", status_code=303)
        # Установка токена в HTTP-only cookie для безопасности
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,   # Защита от XSS атак
            max_age=3600,    # Время жизни 1 час
            secure=False,    # Для HTTPS нужно установить True
            samesite="lax"   # Защита от CSRF атак
        )

        return response

    except Exception as e:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Ошибка сервера: {str(e)}"
        })

# Страница регистрации нового пользователя
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Обработчик формы регистрации: создание нового пользователя
@app.post("/register")
async def register_form(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Проверка уникальности email
        existing_user = db.query(models.User).filter(
            models.User.email == email
        ).first()
        email_alrady_used = existing_user is not None

        if email_alrady_used:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Пользователь с таким email уже существует"
            })

        # Проверка уникальности username
        existing_username = db.query(models.User).filter(
            models.User.username == username
        ).first()
        username_alredy_used = existing_username is not None

        if username_alredy_used:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Пользователь с таким username уже существует"
            })

        # Валидация длины username
        username_short = len(username) < 3
        username_long = len(username) > 50
        username_invalid = username_short or username_long

        if username_invalid:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Username должен быть от 3 до 50 символов"
            })

        # Валидация длины пароля
        password_short = len(password) < 6
        password_invalid = password_short

        if password_invalid:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Пароль должен содержать минимум 6 символов"
            })

        # Хеширование пароля для безопасного хранения
        hashed_password = auth_utils.get_password_hash(password)
        # Создание нового пользователя
        db_user = models.User(
            email=email,
            username=username,
            password_hash=hashed_password,
            role=UserRole.USER.value  # Роль по умолчанию
        )

        # Сохранение пользователя в БД
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Перенаправление на страницу входа с сообщением об успехе
        return templates.TemplateResponse("login.html", {
            "request": request,
            "success": "Регистрация успешна! Теперь вы можете войти."
        })

    except Exception as e:
        # Откат транзакции при ошибке
        db.rollback()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": f"Ошибка регистрации: {str(e)}"
        })

# Страница профиля пользователя - основной файловый менеджер
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request, 
    db: Session = Depends(get_db),
    search: str = Query(None),
    folder_id: int = Query(None)
):
    # Проверка аутентификации
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    # Получение всех папок пользователя
    folders = db.query(Folder).filter(Folder.user_id == user.id).all()
    
    # Базовый запрос для файлов пользователя
    query = db.query(Files).filter(Files.user_id == user.id)
    
    # Режим поиска: ищем по всем файлам независимо от папки
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        query = query.filter(Files.filename.ilike(search_term))
        files = query.all()
        
        current_folder = None
        search_mode = True
    else:
        # Обычный режим: показываем файлы в конкретной папке
        if folder_id:
            query = query.filter(Files.folder_id == folder_id)
            current_folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
        else:
            # Если папка не указана - показываем файлы в корне
            query = query.filter(Files.folder_id.is_(None))
            current_folder = None
        files = query.all()
        search_mode = False

    # Статистика файлов и папок
    total_files_count = db.query(Files).filter(Files.user_id == user.id).count()
    total_folders_count = len(folders)
    
    # Инициализация квоты пользователя при первом входе
    if not user.quota:
        user.quota = 1024 * 1024 * 1024  # 1 ГБ по умолчанию
        db.commit()
    
    if not user.used_space:
        user.used_space = 0
        db.commit()

    # Расчет использования дискового пространства
    used_gb = round(user.used_space / (1024 * 1024 * 1024), 2)
    total_gb = round(user.quota / (1024 * 1024 * 1024), 2)
    used_percent = round((user.used_space / user.quota) * 100, 1) if user.quota > 0 else 0
    
    # Определение цвета прогресс-бара в зависимости от заполненности
    if used_percent < 70:
        progress_class = "bg-success"
    elif used_percent < 90:
        progress_class = "bg-warning"
    else:
        progress_class = "bg-danger"

    # Рендеринг страницы профиля со всеми данными
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

# Выход из системы - удаление токена из cookies
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response

# ============================================================================
# ОПЕРАЦИИ С ФАЙЛАМИ
# ============================================================================

# Загрузка файла на сервер с использованием паттерна "Цепочка обязанностей"
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
        # Базовая валидация folder_id
        if folder_id is not None and folder_id < 0:
            raise HTTPException(status_code=400, detail="Некорректный идентификатор папки")
        
        # Создание цепочки обработчиков для загрузки файла
        auth_handler = AuthCheckHandler()
        quota_handler = QuotaCheckHandler()
        file_type_handler = FileTypeCheckHandler()
        folder_handler = FolderCheckHandler()
        save_handler = SaveFileHandler()

        # Сборка цепочки обработчиков
        auth_handler.next_handler = quota_handler
        quota_handler.next_handler = file_type_handler
        file_type_handler.next_handler = folder_handler
        folder_handler.next_handler = save_handler

        # Запуск обработки через цепочку
        result = auth_handler.handle(request, file, folder_id, db)

        # Перенаправление после успешной загрузки
        redirect_url = f"/profile?folder_id={folder_id}" if folder_id else "/profile"
        return RedirectResponse(url=redirect_url, status_code=303)

    except HTTPException as e:
        # Обработка ожидаемых HTTP ошибок
        redirect_url = f"/profile?folder_id={folder_id}" if folder_id else "/profile"
        return RedirectResponse(url=redirect_url, status_code=303)
    
    except Exception as e:
        # Обработка непредвиденных ошибок
        db.rollback()
        print(f"file upload error: {str(e)}")
        redirect_url = f"/profile?folder_id={folder_id}" if folder_id else "/profile"
        return RedirectResponse(url=redirect_url, status_code=303)

# Переименование файла с валидацией имени
@app.post("/profile/rename/{file_id}", response_class=RedirectResponse)
async def rename_profile_file(
    file_id: int,
    request: Request,
    new_filename: str = Form(...),
    db: Session = Depends(get_db)
):
    # Проверка аутентификации
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    # Поиск файла с проверкой владельца
    file = db.query(Files).filter(Files.id == file_id, Files.user_id == user.id).first()
    if not file:
        return RedirectResponse(url="/profile", status_code=303)

    # Базовая валидация нового имени
    if not new_filename:
        return RedirectResponse(url="/profile", status_code=303)

    if not new_filename.strip():
        raise HTTPException(status_code=400, detail="Имя файла не может быть пустым")

    # Проверка на запрещенные символы в имени файла
    if any(char in new_filename for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
        raise HTTPException(status_code=400, detail="Имя файла содержит запрещённые символы")

    # Формирование нового пути к файлу
    file_dir = os.path.dirname(file.file_path)
    new_file_path = os.path.join(file_dir, new_filename)

    # Проверка уникальности имени в папке
    if os.path.exists(new_file_path):
        raise HTTPException(status_code=400, detail="Файл с таким именем уже существует")

    # Переименование файла на диске и обновление записи в БД
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

# Скачивание отдельного файла
@app.get("/profile/download/{file_id}")
async def download_profile_file(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    # Проверка аутентификации
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    # Поиск файла с проверкой владельца
    file = db.query(Files).filter(Files.id == file_id, Files.user_id == user.id).first()
    if not file:
        raise HTTPException(status_code=404, detail="Файл не найден")

    # Проверка существования файла на диске
    if not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="Файл не найден на сервере")

    # Возврат файла для скачивания
    return FileResponse(
        path=file.file_path,
        filename=file.filename,
        media_type='application/octet-stream'
    )

# Скачивание нескольких файлов в ZIP архиве
@app.post("/profile/download-multiple")
async def download_multiple_files(
    request: Request,
    file_ids: List[int] = Form(...),
    db: Session = Depends(get_db)
):
    # Проверка аутентификации
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    # Получение всех запрошенных файлов пользователя
    files = db.query(Files).filter(
        Files.id.in_(file_ids),
        Files.user_id == user.id
    ).all()

    if not files:
        raise HTTPException(status_code=404, detail="Файлы не найдены")

    # Создание временного ZIP архива
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
        with zipfile.ZipFile(tmp_file.name, 'w') as zipf:
            for file in files:
                if os.path.exists(file.file_path):
                    # Добавление файла в архив
                    zipf.write(file.file_path, file.filename)

        # Возврат ZIP архива для скачивания
        return FileResponse(
            path=tmp_file.name,
            filename=f"files_{user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            media_type='application/zip'
        )

# ============================================================================
# ОПЕРАЦИИ С ПАПКАМИ
# ============================================================================

# Создание новой папки
@app.post("/profile/folders/create")
async def create_folder(
    request: Request,
    name: str = Form(...),
    parent_folder_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        # Обработка parent_folder_id (может быть пустой строкой)
        target_parent_folder_id = None
        if parent_folder_id and parent_folder_id.strip():
            try:
                folder_id_int = int(parent_folder_id)
                target_parent_folder_id = folder_id_int
            except ValueError:
                pass

        # Создание цепочки обработчиков для создания папки
        auth_folder_handler = AuthFolderCheckHandler()
        name_folder_handler = NameFolderCheckHandler()
        parent_folder_handler = ParentFolderCheckHandler()
        create_folder_handler = CreateFolderHandler()

        # Сборка цепочки обработчиков
        auth_folder_handler.next_handler = name_folder_handler
        name_folder_handler.next_handler = parent_folder_handler
        parent_folder_handler.next_handler = create_folder_handler

        # Запуск обработки через цепочку
        result = auth_folder_handler.handle(request, name, target_parent_folder_id, db)

        # Перенаправление после успешного создания
        redirect_url = f"/profile?folder_id={target_parent_folder_id}" if target_parent_folder_id else "/profile"
        return RedirectResponse(url=redirect_url, status_code=303)

    except HTTPException as e:
        redirect_url = f"/profile?folder_id={target_parent_folder_id}" if target_parent_folder_id else "/profile"
        return RedirectResponse(url=redirect_url, status_code=303)

# Удаление файла через цепочку обязанностей
@app.post("/profile/delete/{file_id}", response_class=RedirectResponse)
async def delete_file(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        # Создание цепочки обработчиков для удаления файла
        auth_delete_handler = AuthDeleteCheckHandler()
        access_delete_handler = FileAccessCheckHandler()
        delete_file_handler = DeleteFileHandler()

        # Сборка цепочки обработчиков
        auth_delete_handler.next_handler = access_delete_handler
        access_delete_handler.next_handler = delete_file_handler

        # Запуск обработки через цепочку
        result = auth_delete_handler.handle(request, file_id, db)

        return RedirectResponse(url="/profile", status_code=303)

    except HTTPException as e:
        return RedirectResponse(url="/profile", status_code=303)

# Удаление папки с рекурсивным удалением всего содержимого
@app.post("/profile/folders/delete/{folder_id}", response_class=RedirectResponse)
async def delete_folder(
    folder_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    # Проверка аутентификации
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")

    # Поиск папки с проверкой владельца
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
    if not folder:
        return RedirectResponse(url="/profile", status_code=303)

    # Защита от удаления корневой папки
    if folder.name == "Корневая папка":
        return RedirectResponse(url="/profile", status_code=303)

    # Удаление всех файлов в папке
    files = db.query(Files).filter(Files.folder_id == folder_id).all()
    for file in files:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
        db.delete(file)

    # Рекурсивное удаление всех подпапок
    subfolders = db.query(Folder).filter(Folder.parent_folder_id == folder_id).all()
    for subfolder in subfolders:
        await delete_folder_internal(subfolder.id, user.id, db)

    # Удаление самой папки
    db.delete(folder)
    db.commit()

    return RedirectResponse(url="/profile", status_code=303)

# Вспомогательная функция для рекурсивного удаления папок
async def delete_folder_internal(folder_id: int, user_id: int, db: Session):
    """Внутренняя функция для рекурсивного удаления папок"""
    # Удаление файлов в текущей папке
    files = db.query(Files).filter(Files.folder_id == folder_id).all()
    for file in files:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
        db.delete(file)

    # Рекурсивное удаление подпапок
    subfolders = db.query(Folder).filter(Folder.parent_folder_id == folder_id).all()
    for subfolder in subfolders:
        await delete_folder_internal(subfolder.id, user_id, db)

    # Удаление самой папки
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if folder:
        db.delete(folder)

# API для перемещения файлов между папками (используется для drag&drop)
@app.post("/api/move-file")
async def move_file(
    request: Request,
    move_data: FileMove,
    db: Session = Depends(get_db)
):
    try:
        # Создание цепочки обработчиков для перемещения файла
        auth_move_handler = AuthMoveCheckHandler()
        file_move_handler = FileMoveCheckHandler()
        folder_move_handler = FolderMoveCheckHandler()
        update_move_handler = UpdateMoveHandler()

        # Сборка цепочки обработчиков
        auth_move_handler.next_handler = file_move_handler
        file_move_handler.next_handler = folder_move_handler
        folder_move_handler.next_handler = update_move_handler

        # Запуск обработки через цепочку
        result = auth_move_handler.handle(request, move_data, db)

        # Возврат успешного ответа для JavaScript
        return {"message": "Файл успешно перемещен"}

    except HTTPException as e:
        raise e

# ============================================================================
# ЗАПУСК СЕРВЕРА
# ============================================================================

# Точка входа для запуска приложения
if __name__ == "__main__":
    import uvicorn
    # Запускаем сервер Uvicorn на всех сетевых интерфейсах порта 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)