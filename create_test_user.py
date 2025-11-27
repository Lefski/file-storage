from database import SessionLocal
from models import User
import auth_utils

def create_test_users():
    """Создание тестовых пользователей с разными ролями"""
    db = SessionLocal()
    
    try:
        # Тестовые пользователи
        test_users = [
            {
                "email": "admin@example.com",
                "username": "admin",
                "password": "admin123",
                "role": "admin"
            },
            {
                "email": "moderator@example.com", 
                "username": "moderator",
                "password": "moderator123",
                "role": "moderator"
            },
            {
                "email": "user@example.com",
                "username": "testuser", 
                "password": "user12345",
                "role": "user"
            },
            {
                "email": "test@example.com",
                "username": "testuser2",
                "password": "test12345", 
                "role": "user"
            }
        ]
        
        created_count = 0
        for user_data in test_users:
            try:
                # Проверяем, существует ли пользователь
                existing_user = db.query(User).filter(
                    (User.email == user_data["email"]) | 
                    (User.username == user_data["username"])
                ).first()
                
                if not existing_user:
                    # Хешируем пароль
                    hashed_password = auth_utils.get_password_hash(user_data["password"])
                    
                    user = User(
                        email=user_data["email"],
                        username=user_data["username"],
                        password_hash=hashed_password,
                        role=user_data["role"]
                    )
                    db.add(user)
                    created_count += 1
                    print(f"✅ Создан пользователь: {user_data['email']} с ролью {user_data['role']}")
                    print(f"   Логин: {user_data['email']}")
                    print(f"   Пароль: {user_data['password']}")
                else:
                    print(f"⚠️ Пользователь {user_data['email']} уже существует")
                    
            except Exception as e:
                print(f"❌ Ошибка при создании пользователя {user_data['email']}: {e}")
                continue
        
        db.commit()
        print(f"\n🎉 Успешно создано {created_count} новых пользователей")
        
        # Показываем всех пользователей
        print("\n📋 Все пользователи в базе:")
        all_users = db.query(User).all()
        for user in all_users:
            print(f"   👤 {user.username} ({user.email}) - роль: {user.role}")
            
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_users()