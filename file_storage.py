import os
import shutil
import uuid
from fastapi import UploadFile, HTTPException, status
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
import models

class FileStorageFacade:
    """
    Фасад для работы с файловым хранилищем.
    Предоставляет простой интерфейс для сложных файловых операций.
    """
    
    def __init__(self, storage_path: str = "uploads"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
    
    async def upload_file(self, file: UploadFile, user_id: int, db: Session) -> dict:
        """
        Загрузка файла в хранилище с проверкой квоты
        
        Args:
            file: Файл для загрузки
            user_id: ID пользователя
            db: Сессия базы данных для проверки квоты
            
        Returns:
            dict: Информация о загруженном файле
        """
        try:
            # Получаем пользователя и его квоту
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Пользователь не найден"
                )
            
            # Читаем содержимое файла для проверки размера
            content = await file.read()
            file_size = len(content)
            
            # Проверяем квоту
            current_usage = await self.get_user_storage_usage(user_id)
            if current_usage + file_size > user.quota:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Превышена квота хранилища. Доступно: {self.format_bytes(user.quota - current_usage)}"
                )
            
            # Генерируем уникальное имя файла
            file_extension = Path(file.filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Создаем папку пользователя если не существует
            user_folder = self.storage_path / str(user_id)
            user_folder.mkdir(exist_ok=True)
            
            file_path = user_folder / unique_filename
            
            # Сохраняем файл
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            return {
                "filename": unique_filename,
                "original_name": file.filename,
                "file_path": str(file_path),
                "size": file_size,
                "user_id": user_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка загрузки файла: {str(e)}"
            )
    
    async def get_user_storage_usage(self, user_id: int) -> int:
        """
        Получает общий размер файлов пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            int: Размер в байтах
        """
        try:
            user_folder = self.storage_path / str(user_id)
            
            if not user_folder.exists():
                return 0
            
            total_size = 0
            for file_path in user_folder.iterdir():
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return total_size
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка расчета использования хранилища: {str(e)}"
            )
    
    async def get_user_storage_info(self, user_id: int, db: Session) -> dict:
        """
        Получает информацию о хранилище пользователя
        
        Args:
            user_id: ID пользователя
            db: Сессия базы данных
            
        Returns:
            dict: Информация о хранилище
        """
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        used_storage = await self.get_user_storage_usage(user_id)
        available_storage = user.quota - used_storage
        
        return {
            "user_id": user_id,
            "quota": user.quota,
            "used": used_storage,
            "available": available_storage,
            "quota_formatted": self.format_bytes(user.quota),
            "used_formatted": self.format_bytes(used_storage),
            "available_formatted": self.format_bytes(available_storage),
            "usage_percentage": round((used_storage / user.quota) * 100, 2) if user.quota > 0 else 0
        }
    
    def format_bytes(self, bytes_size: int) -> str:
        """
        Форматирует размер в байтах в читаемый вид
        
        Args:
            bytes_size: Размер в байтах
            
        Returns:
            str: Отформатированная строка
        """
        if bytes_size == 0:
            return "0 B"
        
        sizes = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while bytes_size >= 1024 and i < len(sizes) - 1:
            bytes_size /= 1024
            i += 1
        
        return f"{bytes_size:.2f} {sizes[i]}"
    
    async def delete_file(self, filename: str, user_id: int) -> bool:
        """
        Удаление файла из хранилища
        
        Args:
            filename: Имя файла
            user_id: ID пользователя
            
        Returns:
            bool: True если файл удален
        """
        try:
            user_folder = self.storage_path / str(user_id)
            file_path = user_folder / filename
            
            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Файл не найден"
                )
            
            file_path.unlink()
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка удаления файла: {str(e)}"
            )
    
    async def rename_file(self, old_filename: str, new_filename: str, user_id: int) -> dict:
        """
        Переименование файла
        
        Args:
            old_filename: Текущее имя файла
            new_filename: Новое имя файла
            user_id: ID пользователя
            
        Returns:
            dict: Информация о переименованном файле
        """
        try:
            user_folder = self.storage_path / str(user_id)
            old_path = user_folder / old_filename
            new_path = user_folder / new_filename
            
            if not old_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Файл не найден"
                )
            
            if new_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Файл с таким именем уже существует"
                )
            
            old_path.rename(new_path)
            
            return {
                "old_filename": old_filename,
                "new_filename": new_filename,
                "user_id": user_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка переименования файла: {str(e)}"
            )
    
    async def get_user_files(self, user_id: int) -> List[dict]:
        """
        Получение списка файлов пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[dict]: Список файлов пользователя
        """
        try:
            user_folder = self.storage_path / str(user_id)
            
            if not user_folder.exists():
                return []
            
            files = []
            for file_path in user_folder.iterdir():
                if file_path.is_file():
                    files.append({
                        "filename": file_path.name,
                        "size": file_path.stat().st_size,
                        "created_at": file_path.stat().st_ctime
                    })
            
            return files
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка получения списка файлов: {str(e)}"
            )


# Создаем глобальный экземпляр фасада
file_storage = FileStorageFacade()