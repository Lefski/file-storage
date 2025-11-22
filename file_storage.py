import os
import shutil
import uuid
from fastapi import UploadFile, HTTPException, status
from pathlib import Path
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
import models
from datetime import datetime

# =============================================================================
# ПОДСИСТЕМЫ
# =============================================================================

class FileOperations:
    """Подсистема для операций с файлами"""
    
    def save_file(self, content: bytes, file_path: Path) -> None:
        """Сохранение файла на диск"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as buffer:
            buffer.write(content)
    
    def delete_file(self, file_path: Path) -> bool:
        """Удаление файла"""
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def move_file(self, source_path: Path, target_path: Path) -> None:
        """Перемещение файла"""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.rename(target_path)
    
    def copy_file(self, source_path: Path, target_path: Path) -> None:
        """Копирование файла"""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
    
    def file_exists(self, file_path: Path) -> bool:
        """Проверка существования файла"""
        return file_path.exists() and file_path.is_file()
    
    def get_file_size(self, file_path: Path) -> int:
        """Получение размера файла"""
        return file_path.stat().st_size if file_path.exists() else 0

class FolderOperations:
    """Подсистема для операций с папками"""
    
    def create_folder(self, folder_path: Path) -> None:
        """Создание папки"""
        folder_path.mkdir(parents=True, exist_ok=True)
    
    def delete_folder(self, folder_path: Path) -> bool:
        """Удаление папки и всего содержимого"""
        try:
            if folder_path.exists() and folder_path.is_dir():
                shutil.rmtree(folder_path)
                return True
            return False
        except Exception:
            return False
    
    def move_folder(self, source_path: Path, target_path: Path) -> None:
        """Перемещение папки"""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.rename(target_path)
    
    def folder_exists(self, folder_path: Path) -> bool:
        """Проверка существования папки"""
        return folder_path.exists() and folder_path.is_dir()
    
    def list_content(self, folder_path: Path) -> List[Dict]:
        """Получение содержимого папки"""
        if not folder_path.exists():
            return []
        
        items = []
        for item_path in folder_path.iterdir():
            if item_path.is_file():
                stat = item_path.stat()
                items.append({
                    "type": "file",
                    "name": item_path.name,
                    "size": stat.st_size,
                    "created_at": stat.st_ctime
                })
            elif item_path.is_dir():
                stat = item_path.stat()
                items_count = sum(1 for _ in item_path.iterdir())
                items.append({
                    "type": "folder",
                    "name": item_path.name,
                    "created_at": stat.st_ctime,
                    "items_count": items_count
                })
        
        # Сортируем: сначала папки, потом файлы
        items.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))
        return items

class QuotaManager:
    """Подсистема для управления квотами"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
    
    async def check_quota(self, user_id: int, file_size: int, db: Session) -> None:
        """Проверка квоты пользователя"""
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        current_usage = await self.get_storage_usage(user_id)
        if current_usage + file_size > user.quota:
            available = user.quota - current_usage
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Превышена квота хранилища. Доступно: {self.format_bytes(available)}"
            )
    
    async def get_storage_usage(self, user_id: int) -> int:
        """Получение использованного объема"""
        user_folder = self.storage_path / str(user_id)
        
        if not user_folder.exists():
            return 0
        
        total_size = 0
        for file_path in user_folder.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
    
    async def get_storage_info(self, user_id: int, db: Session) -> Dict:
        """Полная информация о хранилище"""
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        used_storage = await self.get_storage_usage(user_id)
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
        """Форматирование размера"""
        if bytes_size == 0:
            return "0 B"
        
        sizes = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while bytes_size >= 1024 and i < len(sizes) - 1:
            bytes_size /= 1024
            i += 1
        
        return f"{bytes_size:.2f} {sizes[i]}"

class NameGenerator:
    """Подсистема для генерации имен файлов"""
    
    def generate_unique_name(self, target_folder: Path, original_name: str) -> str:
        """Генерация уникального имени файла"""
        file_path = target_folder / original_name
        
        if not file_path.exists():
            return original_name
        
        file_stem = Path(original_name).stem
        file_suffix = Path(original_name).suffix
        
        counter = 1
        while True:
            new_name = f"{file_stem} ({counter}){file_suffix}"
            new_path = target_folder / new_name
            
            if not new_path.exists():
                return new_name
            
            counter += 1
            
            if counter > 1000:
                return f"{file_stem}_{uuid.uuid4().hex[:8]}{file_suffix}"

# =============================================================================
# ФАСАД
# =============================================================================

class FileStorageFacade:
    """
    Фасад для работы с файловым хранилищем.
    Предоставляет простой интерфейс для сложных файловых операций.
    """
    
    def __init__(self, storage_path: str = "uploads"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Инициализация подсистем
        self.file_ops = FileOperations()
        self.folder_ops = FolderOperations()
        self.quota_mgr = QuotaManager(self.storage_path)
        self.name_gen = NameGenerator()
    
    # =========================================================================
    # ПУБЛИЧНЫЙ ИНТЕРФЕЙС ФАСАДА
    # =========================================================================
    
    async def upload_file(self, file: UploadFile, user_id: int, db: Session, folder_path: str = "") -> dict:
        """
        Загрузка файла в хранилище с проверкой квоты
        
        Args:
            file: Файл для загрузки
            user_id: ID пользователя
            db: Сессия базы данных для проверки квоты
            folder_path: Путь к папке для загрузки
            
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
            
            # Проверяем квоту (подсистема QuotaManager)
            await self.quota_mgr.check_quota(user_id, file_size, db)
            
            # Подготавливаем пути
            user_folder = self.storage_path / str(user_id)
            target_folder = user_folder / folder_path if folder_path else user_folder
            
            # Создаем папки если нужно (подсистема FolderOperations)
            self.folder_ops.create_folder(target_folder)
            
            # Генерируем имя файла с проверкой на дубликаты (подсистема NameGenerator)
            original_filename = file.filename
            filename = self.name_gen.generate_unique_name(target_folder, original_filename)
            file_path = target_folder / filename
            
            # Сохраняем файл (подсистема FileOperations)
            self.file_ops.save_file(content, file_path)
            
            return {
                "filename": filename,
                "original_name": original_filename,
                "file_path": str(file_path.relative_to(self.storage_path)),
                "size": file_size,
                "user_id": user_id,
                "folder_path": folder_path
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка загрузки файла: {str(e)}"
            )
    
    async def create_folder(self, folder_name: str, user_id: int, parent_path: str = "") -> dict:
        """
        Создание новой папки
        
        Args:
            folder_name: Название папки
            user_id: ID пользователя
            parent_path: Родительская папка
            
        Returns:
            dict: Информация о созданной папке
        """
        try:
            user_folder = self.storage_path / str(user_id)
            if parent_path:
                folder_path = user_folder / parent_path / folder_name
            else:
                folder_path = user_folder / folder_name
            
            # Проверяем существование (подсистема FolderOperations)
            if self.folder_ops.folder_exists(folder_path):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Папка с таким именем уже существует"
                )
            
            # Создаем папку (подсистема FolderOperations)
            self.folder_ops.create_folder(folder_path)
            
            return {
                "folder_name": folder_name,
                "folder_path": str(folder_path.relative_to(self.storage_path)),
                "user_id": user_id,
                "parent_path": parent_path
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка создания папки: {str(e)}"
            )
    
    async def get_folder_content(self, user_id: int, folder_path: str = "") -> dict:
        """
        Получение содержимого папки
        
        Args:
            user_id: ID пользователя
            folder_path: Путь к папке
            
        Returns:
            dict: Содержимое папки
        """
        try:
            user_folder = self.storage_path / str(user_id)
            
            if folder_path:
                target_folder = user_folder / folder_path
            else:
                target_folder = user_folder
            
            # Проверяем существование папки
            if not target_folder.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Папка не найдена"
                )
            
            # Получаем содержимое (подсистема FolderOperations)
            items = self.folder_ops.list_content(target_folder)
            
            # Добавляем пути к элементам
            for item in items:
                if folder_path:
                    item["path"] = f"{folder_path}/{item['name']}" if folder_path else item['name']
                else:
                    item["path"] = item['name']
            
            return {
                "current_path": folder_path,
                "items": items
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка получения содержимого папки: {str(e)}"
            )
    
    async def delete_folder(self, folder_path: str, user_id: int) -> bool:
        """
        Удаление папки
        
        Args:
            folder_path: Путь к папке
            user_id: ID пользователя
            
        Returns:
            bool: True если папка удалена
        """
        try:
            user_folder = self.storage_path / str(user_id)
            target_folder = user_folder / folder_path
            
            if not target_folder.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Папка не найдена"
                )
            
            if not target_folder.is_dir():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Указанный путь не является папкой"
                )
            
            # Проверяем, что это не корневая папка пользователя
            if target_folder == user_folder:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Нельзя удалить корневую папку пользователя"
                )
            
            # Удаляем папку (подсистема FolderOperations)
            success = self.folder_ops.delete_folder(target_folder)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Не удалось удалить папку"
                )
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка удаления папки: {str(e)}"
            )
    
    async def rename_folder(self, old_path: str, new_name: str, user_id: int) -> dict:
        """
        Переименование папки
        
        Args:
            old_path: Старый путь к папке
            new_name: Новое название папки
            user_id: ID пользователя
            
        Returns:
            dict: Информация о переименованной папке
        """
        try:
            user_folder = self.storage_path / str(user_id)
            old_folder_path = user_folder / old_path
            parent_path = Path(old_path).parent
            
            if parent_path == Path('.'):
                new_folder_path = user_folder / new_name
            else:
                new_folder_path = user_folder / parent_path / new_name
            
            if not old_folder_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Папка не найдена"
                )
            
            if new_folder_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Папка с таким именем уже существует"
                )
            
            # Переименовываем папку (подсистема FolderOperations)
            self.folder_ops.move_folder(old_folder_path, new_folder_path)
            
            return {
                "old_path": old_path,
                "new_path": str(new_folder_path.relative_to(user_folder)),
                "new_name": new_name,
                "user_id": user_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка переименования папки: {str(e)}"
            )
    
    async def get_user_storage_usage(self, user_id: int) -> int:
        """Получает общий размер файлов пользователя (рекурсивно)"""
        return await self.quota_mgr.get_storage_usage(user_id)
    
    async def get_user_storage_info(self, user_id: int, db: Session) -> dict:
        """Получает информацию о хранилище пользователя"""
        return await self.quota_mgr.get_storage_info(user_id, db)
    
    def format_bytes(self, bytes_size: int) -> str:
        """Форматирует размер в байтах в читаемый вид"""
        return self.quota_mgr.format_bytes(bytes_size)
    
    async def delete_file(self, file_path: str, user_id: int) -> bool:
        """
        Удаление файла из хранилища
        
        Args:
            file_path: Путь к файлу относительно папки пользователя
            user_id: ID пользователя
        """
        try:
            user_folder = self.storage_path / str(user_id)
            full_file_path = user_folder / file_path
            
            if not full_file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Файл не найден"
                )
            
            # Удаляем файл (подсистема FileOperations)
            success = self.file_ops.delete_file(full_file_path)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Не удалось удалить файл"
                )
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка удаления файла: {str(e)}"
            )
    
    async def rename_file(self, old_path: str, new_name: str, user_id: int) -> dict:
        """
        Переименование файла
        
        Args:
            old_path: Старый путь к файлу
            new_name: Новое имя файла
            user_id: ID пользователя
        """
        try:
            user_folder = self.storage_path / str(user_id)
            old_file_path = user_folder / old_path
            parent_path = Path(old_path).parent
            
            if parent_path == Path('.'):
                new_file_path = user_folder / new_name
            else:
                new_file_path = user_folder / parent_path / new_name
            
            if not old_file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Файл не найден"
                )
            
            if new_file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Файл с таким именем уже существует"
                )
            
            # Переименовываем файл (подсистема FileOperations)
            self.file_ops.move_file(old_file_path, new_file_path)
            
            return {
                "old_path": old_path,
                "new_path": str(new_file_path.relative_to(user_folder)),
                "new_name": new_name,
                "user_id": user_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка переименования файла: {str(e)}"
            )
    
    async def move_file(self, source_path: str, target_folder: str, user_id: int, new_filename: Optional[str] = None) -> dict:
        """
        Перемещение файла между папками
        
        Args:
            source_path: Текущий путь к файлу
            target_folder: Целевая папка
            user_id: ID пользователя
            new_filename: Новое имя файла (опционально)
            
        Returns:
            dict: Информация о перемещенном файле
        """
        try:
            user_folder = self.storage_path / str(user_id)
            source_file_path = user_folder / source_path
            
            # Проверяем существование исходного файла
            if not source_file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Исходный файл не найден"
                )
            
            if not source_file_path.is_file():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Указанный путь не является файлом"
                )
            
            # Создаем целевую папку если не существует (подсистема FolderOperations)
            target_folder_path = user_folder / target_folder
            self.folder_ops.create_folder(target_folder_path)
            
            # Определяем имя файла в целевой папке
            if new_filename:
                target_filename = new_filename
            else:
                target_filename = source_file_path.name
            
            target_file_path = target_folder_path / target_filename
            
            # Проверяем, не существует ли уже файл с таким именем в целевой папке
            if target_file_path.exists():
                # Генерируем уникальное имя (подсистема NameGenerator)
                target_filename = self.name_gen.generate_unique_name(target_folder_path, target_filename)
                target_file_path = target_folder_path / target_filename
            
            # Перемещаем файл (подсистема FileOperations)
            self.file_ops.move_file(source_file_path, target_file_path)
            
            return {
                "source_path": source_path,
                "target_path": str(target_file_path.relative_to(user_folder)),
                "filename": target_filename,
                "target_folder": target_folder,
                "user_id": user_id,
                "moved_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка перемещения файла: {str(e)}"
            )

    async def move_folder(self, source_path: str, target_folder: str, user_id: int, new_folder_name: Optional[str] = None) -> dict:
        """
        Перемещение папки
        
        Args:
            source_path: Текущий путь к папке
            target_folder: Целевая папка
            user_id: ID пользователя
            new_folder_name: Новое имя папки (опционально)
            
        Returns:
            dict: Информация о перемещенной папке
        """
        try:
            user_folder = self.storage_path / str(user_id)
            source_folder_path = user_folder / source_path
            
            # Проверяем существование исходной папки
            if not source_folder_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Исходная папка не найдена"
                )
            
            if not source_folder_path.is_dir():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Указанный путь не является папкой"
                )
            
            # Проверяем, что не пытаемся переместить папку в саму себя или её подпапку
            target_folder_path = user_folder / target_folder
            if source_folder_path == target_folder_path or source_folder_path in target_folder_path.parents:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Невозможно переместить папку в саму себя или её подпапку"
                )
            
            # Создаем целевую папку если не существует (подсистема FolderOperations)
            self.folder_ops.create_folder(target_folder_path)
            
            # Определяем имя папки в целевой папке
            if new_folder_name:
                target_folder_name = new_folder_name
            else:
                target_folder_name = source_folder_path.name
            
            target_new_path = target_folder_path / target_folder_name
            
            # Проверяем, не существует ли уже папка с таким именем в целевой папке
            if target_new_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Папка с таким именем уже существует в целевой папке"
                )
            
            # Перемещаем папку (подсистема FolderOperations)
            self.folder_ops.move_folder(source_folder_path, target_new_path)
            
            return {
                "source_path": source_path,
                "target_path": str(target_new_path.relative_to(user_folder)),
                "folder_name": target_folder_name,
                "target_folder": target_folder,
                "user_id": user_id,
                "moved_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка перемещения папки: {str(e)}"
            )

file_storage = FileStorageFacade()