from fastapi import FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
import auth_utils
from database import get_db
from models import UserCreate, UserLogin, UserResponse, Token, UserRole
from datetime import timedelta

app = FastAPI(title="File Storage Auth API", version="1.0.0")

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

security = HTTPBearer()

# HTML страницы
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Используем ту же логику, что и в API
        user = db.query(models.User).filter(models.User.email == email).first()
        user_not_found = user is None 
        
        if user_not_found:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Неверный email или пароль"
            })
        
        password_correct = auth_utils.verify_password(password, user.password_hash)
        user_active = user.is_active

        password_invalid = not password_correct
        user_inactive = not user_active
        
        if password_invalid:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Неверный email или пароль"
            })
        
        if user_inactive:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Пользователь деактивирован"
            })
        
        # Создание токена
        access_token_expires = timedelta(minutes=auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_utils.create_access_token(
            data={"sub": user.email, "role": user.role}, 
            expires_delta=access_token_expires
        )
        
        # Создаем ответ с перенаправлением
        response = RedirectResponse(url="/profile", status_code=303)
        # Сохраняем токен в cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=3600,  
            secure=False,  
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Ошибка сервера: {str(e)}"
        })

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_form(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Проверка на существующего пользователя с таким email
        existing_user = db.query(models.User).filter(
            models.User.email == email
        ).first()
        email_alrady_used = existing_user is not None
        if email_alrady_used:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Пользователь с таким email уже существует"
            })
        
        # Проверка на существующего пользователя с таким username
        existing_username = db.query(models.User).filter(
            models.User.username == username
        ).first()
        username_alredy_used = existing_username is not None
        if username_alredy_used:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Пользователь с таким username уже существует"
            })
        
        username_short = len(username) < 3
        username_long = len(username) > 50
        username_invalid = username_short or username_long
        # Валидация username
        if username_invalid:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Username должен быть от 3 до 50 символов"
            })
        

        password_short = len(password)< 6
        password_invalid = password_short
        
        # Валидация пароля
        if password_short:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Пароль должен содержать минимум 6 символов"
            })
        
        # Создание пользователя
        hashed_password = auth_utils.get_password_hash(password)
        db_user = models.User(
            email=email,
            username=username,
            password_hash=hashed_password,
            role=UserRole.USER.value
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Перенаправляем на страницу входа с сообщением об успехе
        return templates.TemplateResponse("login.html", {
            "request": request,
            "success": "Регистрация успешна! Теперь вы можете войти."
        })
        
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": f"Ошибка регистрации: {str(e)}"
        })

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    # Получаем токен из cookies
    token = request.cookies.get("access_token")
    token_invalid = token is None
    if token_invalid:
        return RedirectResponse(url="/login")
    
    # Проверяем токен
    payload = auth_utils.verify_token(token)
    payload_invalid = payload is None
    if payload_invalid:
        response = RedirectResponse(url="/login")
        response.delete_cookie("access_token")
        return response
    
    email = payload.get("sub")
    email_invalid = email is None
    if email_invalid:
        response = RedirectResponse(url="/login")
        response.delete_cookie("access_token")
        return response
    
    # Получаем пользователя
    user = db.query(models.User).filter(models.User.email == email).first()
    user_invalid = user is None
    if user_invalid:
        response = RedirectResponse(url="/login")
        response.delete_cookie("access_token")
        return response
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user
    })

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response

# API эндпоинты 
@app.post("/api/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def api_register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(
        models.User.email == user_data.email
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует"
        )
    
    existing_username = db.query(models.User).filter(
        models.User.username == user_data.username
    ).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким username уже существует"
        )
    
    hashed_password = auth_utils.get_password_hash(user_data.password)
    db_user = models.User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hashed_password,
        role=UserRole.USER.value
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/api/login", response_model=Token)
async def api_login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    if not auth_utils.verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь деактивирован"
        )
    
    access_token_expires = timedelta(minutes=auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_utils.create_access_token(
        data={"sub": user.email, "role": user.role}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }

@app.get("/api/me", response_model=UserResponse)
async def api_get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен"
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен"
        )
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return user

@app.get("/api/admin")
async def admin_only(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = auth_utils.verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    role = payload.get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    
    return {"message": "Добро пожаловать в админ-панель!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)