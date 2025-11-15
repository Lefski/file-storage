from database import engine, SessionLocal
from models import User

def check_database_connection():
    """Проверка подключения к базе данных"""
    try:
        # Проверяем подключение
        with engine.connect() as conn:
            print("✅ Подключение к базе данных успешно")
        
        # Проверяем существование таблицы users
        db = SessionLocal()
        try:
            # Пробуем выполнить простой запрос
            user_count = db.query(User).count()
            print(f"✅ Таблица users существует, записей: {user_count}")
        except Exception as e:
            print(f"❌ Ошибка при доступе к таблице users: {e}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")

if __name__ == "__main__":
    check_database_connection()