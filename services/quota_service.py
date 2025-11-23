from file_storage import file_storage
from sqlalchemy.orm import Session

class QuotaService:
    """Сервис для управления квотами"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def update_user_quota(self, user_id: int, new_quota: int) -> dict:
        """Обновление квоты пользователя"""
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден"
            )
        
        # Используем ваш file_storage для получения текущего использования
        current_usage = await file_storage.get_user_storage_usage(user_id)
        
        if new_quota < current_usage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Новая квота не может быть меньше текущего использования ({file_storage.format_bytes(current_usage)})"
            )
        
        user.quota = new_quota
        self.db.commit()
        self.db.refresh(user)
        
        return {
            "message": "Квота обновлена",
            "user_id": user.id,
            "username": user.username,
            "new_quota": new_quota,
            "new_quota_formatted": file_storage.format_bytes(new_quota),
            "current_usage": current_usage,
            "current_usage_formatted": file_storage.format_bytes(current_usage)
        }