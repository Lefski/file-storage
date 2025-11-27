from abc import ABC, abstractmethod
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from models import User
from file_models import Files, Folder
import os
import file_utils
from sqlalchemy.sql import func

# --- Базовый класс обработчика ---
# Абстрактный класс, реализующий паттерн "Цепочка обязанностей".
# Позволяет передавать запрос по цепочке обработчиков, пока один из них не обработает его.
class BaseHandler(ABC):
    def __init__(self, next_handler=None):
        # Ссылка на следующий обработчик в цепочке.
        self.next_handler = next_handler

    def handle(self, *args, **kwargs):
        # Если есть следующий обработчик, передать запрос ему.
        if self.next_handler:
            return self.next_handler.handle(*args, **kwargs)
        return None

# Вспомогательная функция для получения пользователя из запроса.
def get_user_from_request(request, db: Session):
    """Получает пользователя из request.state или из базы данных по токену."""
    # Проверяем, есть ли пользователь в состоянии запроса.
    if hasattr(request.state, 'user') and request.state.user:
        return request.state.user

    # Если пользователя нет в request.state, пытаемся получить его из токена.
    token = request.cookies.get("access_token")
    if not token:
        return None

    # Проверяем токен и извлекаем email пользователя.
    from auth_utils import verify_token
    payload = verify_token(token)
    if not payload:
        return None

    email = payload.get("sub")
    if not email:
        return None

    # Ищем пользователя в базе данных по email.
    user = db.query(User).filter(User.email == email).first()
    return user

# --- Обработчики для загрузки файлов ---
# Проверяет, авторизован ли пользователь.
class AuthCheckHandler(BaseHandler):
    def handle(self, request, file, folder_id, db: Session):
        # Получаем пользователя из запроса.
        user = get_user_from_request(request, db)
        if not user:
            # Если пользователь не авторизован, возвращаем ошибку 401.
            raise HTTPException(status_code=401, detail="Не авторизован")
        # Передаем запрос следующему обработчику, добавляя пользователя в аргументы.
        return super().handle(request, file, folder_id, db, user)

# Проверяет, не превышает ли загружаемый файл квоту пользователя.
class QuotaCheckHandler(BaseHandler):
    def handle(self, request, file, folder_id, db: Session, user):
        # Считаем суммарный размер всех файлов пользователя.
        used_space = db.query(func.sum(Files.file_size)).filter(Files.user_id == user.id).scalar() or 0
        # Проверяем, не превышает ли новый файл квоту (по умолчанию 1 ГБ).
        if used_space + (file.size or 0) > (user.quota or 1073741824):
            raise HTTPException(status_code=403, detail="Превышен лимит дискового пространства")
        # Передаем запрос следующему обработчику.
        return super().handle(request, file, folder_id, db, user)

# Проверяет, разрешен ли тип загружаемого файла.
class FileTypeCheckHandler(BaseHandler):
    def handle(self, request, file, folder_id, db: Session, user):
        # Список разрешенных расширений файлов.
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.txt', '.doc', '.docx', '.zip', '.rar'}
        if file.filename:
            # Извлекаем расширение файла.
            file_extension = os.path.splitext(file.filename)[1].lower()
            # Проверяем, разрешен ли тип файла.
            if file_extension not in allowed_extensions:
                raise HTTPException(status_code=400, detail=f"Недопустимый тип файла: {file_extension}")
        # Передаем запрос следующему обработчику.
        return super().handle(request, file, folder_id, db, user)

# Проверяет, существует ли папка, в которую загружается файл.
class FolderCheckHandler(BaseHandler):
    def handle(self, request, file, folder_id, db: Session, user):
        if folder_id:
            # Ищем папку в базе данных.
            folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
            if not folder:
                raise HTTPException(status_code=404, detail="Папка не найдена")
        # Передаем запрос следующему обработчику.
        return super().handle(request, file, folder_id, db, user)

# Сохраняет файл на диск и в базу данных.
class SaveFileHandler(BaseHandler):
    def handle(self, request, file, folder_id, db: Session, user):
        try:
            # Сохраняем файл на диск.
            file_path = file_utils.save_upload_file(file, user.id, file.filename)
            # Получаем размер файла.
            file_size = os.path.getsize(file_path)

            # Создаем запись о файле в базе данных.
            db_file = Files(
                user_id=user.id,
                folder_id=folder_id,
                filename=file.filename,
                file_path=file_path,
                file_size=file_size
            )
            db.add(db_file)
            db.flush()  # Сохраняем файл, чтобы получить ID, но не коммитим транзакцию.

            # Обновляем использованное пространство пользователя.
            current_user = db.query(User).filter(User.id == user.id).first()
            current_user.used_space = (current_user.used_space or 0) + file_size

            # Коммитим все изменения в базе данных.
            db.commit()
            db.refresh(db_file)

            # Возвращаем успешный результат.
            return {"status": "success", "file_id": db_file.id}
        except Exception as e:
            # Откатываем изменения в базе данных при ошибке.
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {str(e)}")

# --- Обработчики для удаления файлов ---
# Проверяет, авторизован ли пользователь перед удалением файла.
class AuthDeleteCheckHandler(BaseHandler):
    def handle(self, request, file_id, db: Session):
        user = get_user_from_request(request, db)
        if not user:
            raise HTTPException(status_code=401, detail="Не авторизован")
        # Передаем запрос следующему обработчику, добавляя пользователя в аргументы.
        return super().handle(request, file_id, db, user)

# Проверяет, существует ли файл и принадлежит ли он пользователю.
class FileAccessCheckHandler(BaseHandler):
    def handle(self, request, file_id, db: Session, user):
        # Ищем файл в базе данных.
        file = db.query(Files).filter(Files.id == file_id, Files.user_id == user.id).first()
        if not file:
            raise HTTPException(status_code=404, detail="Файл не найден")
        # Передаем запрос следующему обработчику, добавляя файл в аргументы.
        return super().handle(request, file_id, db, user, file)

# Удаляет файл с диска и из базы данных.
class DeleteFileHandler(BaseHandler):
    def handle(self, request, file_id, db: Session, user, file):
        try:
            # Получаем размер файла.
            file_size = file.file_size or 0

            # Удаляем файл с диска.
            if os.path.exists(file.file_path):
                os.remove(file.file_path)

            # Обновляем использованное пространство пользователя.
            current_user = db.query(User).filter(User.id == user.id).first()
            current_user.used_space = max(0, (current_user.used_space or 0) - file_size)

            # Удаляем файл из базы данных.
            db.delete(file)
            db.commit()

            # Возвращаем успешный результат.
            return {"status": "success"}
        except Exception as e:
            # Откатываем изменения в базе данных при ошибке.
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка при удалении файла: {str(e)}")

# --- Обработчики для создания папок ---
# Проверяет, авторизован ли пользователь перед созданием папки.
class AuthFolderCheckHandler(BaseHandler):
    def handle(self, request, name, parent_folder_id, db: Session):
        user = get_user_from_request(request, db)
        if not user:
            raise HTTPException(status_code=401, detail="Не авторизован")
        # Передаем запрос следующему обработчику, добавляя пользователя в аргументы.
        return super().handle(request, name, parent_folder_id, db, user)

# Проверяет, существует ли папка с таким именем в текущей директории.
class NameFolderCheckHandler(BaseHandler):
    def handle(self, request, name, parent_folder_id, db: Session, user):
        # Ищем папку с таким именем в базе данных.
        existing_folder = db.query(Folder).filter(
            Folder.name == name,
            Folder.user_id == user.id,
            Folder.parent_folder_id == parent_folder_id
        ).first()
        if existing_folder:
            raise HTTPException(status_code=400, detail="Папка с таким именем уже существует")
        # Передаем запрос следующему обработчику.
        return super().handle(request, name, parent_folder_id, db, user)

# Проверяет существование родительской папки.
class ParentFolderCheckHandler(BaseHandler):
    def handle(self, request, name, parent_folder_id, db: Session, user):
        if parent_folder_id:
            # Ищем родительскую папку в базе данных.
            parent_folder = db.query(Folder).filter(Folder.id == parent_folder_id, Folder.user_id == user.id).first()
            if not parent_folder:
                raise HTTPException(status_code=404, detail="Родительская папка не найдена")
        # Передаем запрос следующему обработчику.
        return super().handle(request, name, parent_folder_id, db, user)

# Создает новую папку в базе данных.
class CreateFolderHandler(BaseHandler):
    def handle(self, request, name, parent_folder_id, db: Session, user):
        try:
            # Создаем новую папку.
            folder = Folder(
                user_id=user.id,
                name=name,
                parent_folder_id=parent_folder_id
            )
            db.add(folder)
            db.commit()
            # Возвращаем успешный результат.
            return {"status": "success", "folder_id": folder.id}
        except Exception as e:
            # Откатываем изменения в базе данных при ошибке.
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка при создании папки: {str(e)}")

# --- Обработчики для перемещения файлов ---
# Проверяет, авторизован ли пользователь перед перемещением файла.
class AuthMoveCheckHandler(BaseHandler):
    def handle(self, request, move_data, db: Session):
        user = get_user_from_request(request, db)
        if not user:
            raise HTTPException(status_code=401, detail="Не авторизован")
        # Передаем запрос следующему обработчику, добавляя пользователя в аргументы.
        return super().handle(request, move_data, db, user)

# Проверяет, существует ли файл.
class FileMoveCheckHandler(BaseHandler):
    def handle(self, request, move_data, db: Session, user):
        # Ищем файл в базе данных.
        file = db.query(Files).filter(Files.id == move_data.file_id, Files.user_id == user.id).first()
        if not file:
            raise HTTPException(status_code=404, detail="Файл не найден")
        # Передаем запрос следующему обработчику, добавляя файл в аргументы.
        return super().handle(request, move_data, db, user, file)

# Проверяет существование целевой папки.
class FolderMoveCheckHandler(BaseHandler):
    def handle(self, request, move_data, db: Session, user, file):
        if move_data.target_folder_id:
            # Ищем целевую папку в базе данных.
            target_folder = db.query(Folder).filter(Folder.id == move_data.target_folder_id, Folder.user_id == user.id).first()
            if not target_folder:
                raise HTTPException(status_code=404, detail="Папка не найдена")
        # Передаем запрос следующему обработчику.
        return super().handle(request, move_data, db, user, file)

# Обновляет информацию о файле в базе данных (перемещает файл в другую папку).
class UpdateMoveHandler(BaseHandler):
    def handle(self, request, move_data, db: Session, user, file):
        try:
            # Обновляем папку файла.
            file.folder_id = move_data.target_folder_id
            file.updated_at = func.now()
            db.commit()
            # Возвращаем успешный результат.
            return {"message": "Файл успешно перемещен"}
        except Exception as e:
            # Откатываем изменения в базе данных при ошибке.
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка при перемещении файла: {str(e)}")
