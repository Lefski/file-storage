from services.file_service import FileService
from services.quota_service import QuotaService
from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db

def get_file_service() -> FileService:
    """Зависимость для сервиса файлов"""
    return FileService()

def get_quota_service(db: Session = Depends(get_db)) -> QuotaService:
    """Зависимость для сервиса квот"""
    return QuotaService(db)