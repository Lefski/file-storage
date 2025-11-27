from file_storage import file_storage
from sqlalchemy.orm import Session

class FileService:
    """Сервис для операций с файлами"""
    
    async def rename_file(self, old_filename: str, new_filename: str, user_id: int) -> dict:
        """Переименование файла"""
        try:
            result = await file_storage.rename_file(old_filename, new_filename, user_id)
            return {
                "status": "success",
                "message": "Файл успешно переименован",
                "data": result
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка переименования файла: {str(e)}"
            )
    
    async def get_user_files(self, user_id: int) -> list:
        """Получение списка файлов пользователя"""
        try:
            # Используем метод получения содержимого корневой папки
            content = await file_storage.get_folder_content(user_id, "")
            return content.get("items", [])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка получения файлов: {str(e)}"
            )
    
    async def get_user_storage_info(self, user_id: int, db: Session) -> dict:
        """Получение информации о хранилище"""
        try:
            return await file_storage.get_user_storage_info(user_id, db)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка получения информации о хранилище: {str(e)}"
            )
    
    async def get_user_storage_usage(self, user_id: int) -> int:
        """Получение использованного объема"""
        try:
            return await file_storage.get_user_storage_usage(user_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка получения объема хранилища: {str(e)}"
            )