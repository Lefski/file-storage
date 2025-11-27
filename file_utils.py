import os
from fastapi import UploadFile, HTTPException
from fastapi.responses import FileResponse

def save_upload_file(upload_file: UploadFile, user_id: int, filename: str) -> str:
    """Сохраняет загруженный файл на диск и возвращает путь к файлу."""
    try:
        # создаем безопасное имя файла
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        if not safe_filename:
            safe_filename = "unnamed_file"
            
        user_upload_dir = f"uploads/{user_id}"
        os.makedirs(user_upload_dir, exist_ok=True)

        file_path = os.path.join(user_upload_dir, safe_filename)

        # проверка на файл с таким же именем
        counter = 1
        original_path = file_path
        while os.path.exists(file_path):
            name, ext = os.path.splitext(original_path)
            file_path = f"{name}_{counter}{ext}"
            counter += 1

        with open(file_path, "wb") as buffer:
            content = upload_file.file.read()
            buffer.write(content)

        return file_path

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {str(e)}")

def rename_file_on_disk(old_path: str, new_path: str):
    """Переименовывает файл на диске."""
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="Файл не найден")

    try:
        # проекрка создания
        new_dir = os.path.dirname(new_path)
        os.makedirs(new_dir, exist_ok=True)
        
        os.rename(old_path, new_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при переименовании файла: {str(e)}")