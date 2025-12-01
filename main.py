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

# Точка входа для запуска приложения.
if __name__ == "__main__":
    import uvicorn
    # Запускаем сервер Uvicorn на хосте 0.0.0.0 и порту 8000.
    uvicorn.run(app, host="0.0.0.0", port=8000)
