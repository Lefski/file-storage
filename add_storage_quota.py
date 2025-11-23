from database import engine
from models import Base, User
from sqlalchemy.orm import sessionmaker

# Создаем сессию
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def add_quota_column():
    # Создаем таблицы (если нужно)
    Base.metadata.create_all(bind=engine)
    
    # Обновляем существующих пользователей
    db = SessionLocal()
    try:
        # Устанавливаем квоту 1 ГБ для всех существующих пользователей
        users = db.query(User).all()
        for user in users:
            if user.quota is None:
                user.quota = 1073741824  # 1 ГБ
        
        db.commit()
        print("Квота хранилища успешно добавлена для всех пользователей")
    except Exception as e:
        db.rollback()
        print(f"Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    add_quota_column()