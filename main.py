from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
import secrets
import json
import os
import time
import random
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from io import BytesIO
import base64

app = FastAPI(title="Digital Signage CMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='admin_cms',
    aws_secret_access_key='password123',
    region_name='us-east-1'
)

BUCKET_NAME = "digital-signage-media"
MAX_STORAGE_BYTES = 100 * 1024 * 1024 * 1024
DB_FILE = "database.json"

ALLOWED_EXTENSIONS = {
    'mp4', 'mov', 'mkv', 'webm', 'avi',
    'jpeg', 'jpg', 'png', 'webp', 'gif', 'svg', 'heic'
}

security = HTTPBasic()

DEFAULT_USERS = {
    "admin_main": {"password": "admin123", "role": "admin", "city_id": "global"},
    "user_msk": {"password": "user123", "role": "regional", "city_id": "moscow"},
    "user_spb": {"password": "user123", "role": "regional", "city_id": "spb"},
    "user_novo": {"password": "user123", "role": "regional", "city_id": "novocheboksarsk"},
    "user_yar": {"password": "user123", "role": "regional", "city_id": "yartsevo"},
    "user_azov": {"password": "user123", "role": "regional", "city_id": "azov"},
    "user_oren": {"password": "user123", "role": "regional", "city_id": "orenburg"},
    "user_cher": {"password": "user123", "role": "regional", "city_id": "chernyakhovsk"}
}

SCREENS_DB = {
    "moscow": ["Москва-Экран-1", "Москва-Экран-2", "Москва-Экран-3"],
    "spb": ["СПБ-Экран-1", "СПБ-Экран-2"],
    "novocheboksarsk": ["Новочебоксарск-Экран-1"],
    "yartsevo": ["Ярцево-Экран-1"],
    "azov": ["Азов-Экран-1"],
    "orenburg": ["Оренбург-Экран-1"],
    "chernyakhovsk": ["Черняховск-Экран-1"]
}

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class ResetRequest(BaseModel):
    username: str

class AdminReset(BaseModel):
    username: str

def load_db():
    if not os.path.exists(DB_FILE): 
        data = {"schedules": [], "trash": [], "users": DEFAULT_USERS, "requests": []}
        save_db(data)
        return data
    with open(DB_FILE, "r", encoding="utf-8") as f: 
        data = json.load(f)
    if "users" not in data:
        data["users"] = DEFAULT_USERS
        save_db(data)
    if "requests" not in data:
        data["requests"] = []
        save_db(data)
    return clean_old_records(data)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f: 
        json.dump(data, f, ensure_ascii=False, indent=4)

def clean_old_records(data):
    now = datetime.now()
    one_year = timedelta(days=365)
    valid_schedules = []
    for s in data.get("schedules", []):
        try:
            end_time = datetime.fromisoformat(s.get("time_end", ""))
            if now - end_time < one_year: valid_schedules.append(s)
        except ValueError: valid_schedules.append(s)
            
    valid_trash = []
    for t in data.get("trash", []):
        try:
            del_time = datetime.fromisoformat(t.get("deleted_at", ""))
            if now - del_time < one_year: valid_trash.append(t)
        except ValueError: valid_trash.append(t)

    cleaned_data = {
        "schedules": valid_schedules, 
        "trash": valid_trash, 
        "users": data.get("users", DEFAULT_USERS),
        "requests": data.get("requests", [])
    }
    return cleaned_data

def get_dynamic_status(start_str, end_str):
    try:
        now = datetime.now()
        start = datetime.fromisoformat(start_str)
        end = datetime.fromisoformat(end_str)
        if now < start: return "Ожидание"
        elif start <= now <= end: return "Активен"
        else: return "Завершен"
    except ValueError: return "Ошибка даты"

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    db = load_db()
    users = db.get("users", {})
    user = users.get(credentials.username)
    if not user or not secrets.compare_digest(user["password"], credentials.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль", headers={"WWW-Authenticate": "Basic"})
    return {"username": credentials.username, **user}

@app.post("/request-reset/")
def request_reset(data: ResetRequest):
    db = load_db()
    if data.username not in db["users"]:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Избегаем дубликатов запросов от одного пользователя
    db["requests"] = [r for r in db["requests"] if r["username"] != data.username]
    db["requests"].append({
        "username": data.username, 
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_db(db)
    return {"message": "Запрос отправлен администратору"}

@app.get("/admin/users/")
def get_admin_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    db = load_db()
    users_safe = {uname: {"role": u["role"], "city_id": u["city_id"]} for uname, u in db["users"].items()}
    return {"users": users_safe, "requests": db.get("requests", [])}

@app.post("/admin/reset-password/")
def admin_reset_password(data: AdminReset, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    db = load_db()
    if data.username not in db["users"]:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Сбрасываем пароль до дефолтного
    db["users"][data.username]["password"] = "user123"
    
    # Удаляем запрос из списка активных
    db["requests"] = [r for r in db["requests"] if r["username"] != data.username]
    save_db(db)
    return {"message": f"Пароль пользователя {data.username} успешно сброшен до 'user123'"}

@app.post("/change-password/")
def change_password(data: PasswordChange, current_user: dict = Depends(get_current_user)):
    db = load_db()
    username = current_user["username"]
    if db["users"][username]["password"] != data.old_password:
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
    db["users"][username]["password"] = data.new_password
    save_db(db)
    return {"message": "Пароль успешно изменен"}

def get_total_bucket_size():
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
        return sum(obj['Size'] for obj in response.get('Contents', []))
    except ClientError: return 0

@app.get("/storage-stats/")
def get_storage_stats(current_user: dict = Depends(get_current_user)):
    size = get_total_bucket_size()
    percent = (size / MAX_STORAGE_BYTES) * 100
    return {"used": size, "max": MAX_STORAGE_BYTES, "percent": round(percent, 2)}

@app.get("/monitoring/")
def get_monitoring(current_user: dict = Depends(get_current_user)):
    current_minute = int(time.time() / 60)
    status_list = []
    for city, screens in SCREENS_DB.items():
        if current_user["role"] != "admin" and current_user["city_id"] != city: continue
        for sc in screens:
            random.seed(f"{sc}_{current_minute}")
            is_online = random.choice([True, True, True, False])
            status_list.append({"city": city, "screen": sc, "status": "В сети" if is_online else "Офлайн"})
    return {"monitoring": status_list}

@app.get("/analytics/")
def get_analytics(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403, detail="Доступ запрещен")
    db = load_db()
    schedules = db.get("schedules", [])
    
    total_hours = 0
    status_counts = {"Ожидание": 0, "Активен": 0, "Завершен": 0}
    city_counts = {}
    
    for s in schedules:
        st_status = get_dynamic_status(s.get("time_start"), s.get("time_end"))
        status_counts[st_status] = status_counts.get(st_status, 0) + 1
        
        city = s.get("city", "global")
        city_counts[city] = city_counts.get(city, 0) + 1
        
        try:
            st = datetime.fromisoformat(s.get("time_start"))
            en = datetime.fromisoformat(s.get("time_end"))
            if en > st: total_hours += (en - st).total_seconds() / 3600
        except: pass
            
    return {
        "total_shows": len(schedules),
        "total_hours": round(total_hours, 1),
        "status_counts": status_counts,
        "city_counts": city_counts
    }

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), target_city: str = Form(None), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403, detail="Доступ запрещен")
    filename = file.filename or ""
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS: raise HTTPException(status_code=400, detail=f"Формат '.{ext}' не поддерживается.")
    
    current_size = get_total_bucket_size()
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if current_size + file_size > MAX_STORAGE_BYTES: raise HTTPException(status_code=400, detail="Превышен лимит хранилища в 100 ГБ")
    
    folder = target_city if target_city else "global"
    file_key = f"{folder}/{filename}"
    try:
        s3_client.upload_fileobj(file.file, BUCKET_NAME, file_key)
        return {"success": True, "message": f"Файл {filename} импортирован в {folder}"}
    except ClientError as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/")
def list_files(current_user: dict = Depends(get_current_user)):
    try:
        prefix = "" if current_user["role"] == "admin" else f"{current_user['city_id']}/"
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
        files_list = []
        for obj in response.get("Contents", []):
            files_list.append({
                "name": obj["Key"], "size": obj["Size"], "last_modified": obj["LastModified"].isoformat(),
                "url": s3_client.generate_presigned_url('get_object', Params={'Bucket': BUCKET_NAME, 'Key': obj["Key"]}, ExpiresIn=3600)
            })
        return {"files": files_list}
    except ClientError as e: raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/{file_key:path}")
def delete_file(file_key: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403, detail="Доступ запрещен")
    try:
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=file_key)
        file_size = obj['ContentLength']
        file_body = base64.b64encode(obj['Body'].read()).decode('utf-8')
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=file_key)
        db = load_db()
        db["trash"].append({"name": file_key, "size": file_size, "data": file_body, "deleted_at": datetime.now().isoformat()})
        save_db(db)
        return {"message": "Файл перемещен в корзину"}
    except ClientError as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/trash/")
def get_trash(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    db = load_db()
    return {"trash": [{"name": item["name"], "size": item["size"]} for item in db["trash"]]}

@app.post("/trash/restore/{file_name:path}")
def restore_file(file_name: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    db = load_db()
    target_item = next((item for item in db["trash"] if item["name"] == file_name), None)
    if not target_item: raise HTTPException(status_code=404)
    try:
        file_bytes = base64.b64decode(target_item["data"])
        s3_client.upload_fileobj(BytesIO(file_bytes), BUCKET_NAME, target_item["name"])
        db["trash"] = [item for item in db["trash"] if item["name"] != file_name]
        save_db(db)
        return {"message": "Успешно восстановлено"}
    except ClientError as e: raise HTTPException(status_code=500, detail=str(e))

@app.delete("/trash/empty/")
def empty_trash(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    db = load_db()
    db["trash"] = []
    save_db(db)
    return {"message": "Корзина очищена"}

@app.get("/screens/")
def get_screens(current_user: dict = Depends(get_current_user)):
    return {"screens": SCREENS_DB}

@app.get("/schedules/")
def get_schedules(current_user: dict = Depends(get_current_user)):
    db = load_db()
    schedules = db["schedules"]
    if current_user["role"] != "admin":
        city = current_user["city_id"]
        schedules = [s for s in schedules if s.get("city") == city or s.get("city") == "global"]
    for s in schedules: s["status"] = get_dynamic_status(s.get("time_start"), s.get("time_end"))
    return {"schedules": schedules}

@app.post("/schedules/")
def create_schedule(item: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    db = load_db()
    try:
        new_st = datetime.fromisoformat(item.get("time_start"))
        new_en = datetime.fromisoformat(item.get("time_end"))
    except: raise HTTPException(status_code=400, detail="Ошибка формата времени")

    new_scr = item.get("screens", [])
    new_city = item.get("city", "global")

    for s in db["schedules"]:
        try:
            s_st = datetime.fromisoformat(s.get("time_start"))
            s_en = datetime.fromisoformat(s.get("time_end"))
            if new_st < s_en and s_st < new_en:
                s_scr = s.get("screens", [])
                if not s_scr and not new_scr and s.get("city") == new_city:
                    raise HTTPException(status_code=400, detail=f"Конфликт: Экраны филиала {new_city} уже заняты в это время.")
                overlap = set(new_scr).intersection(set(s_scr))
                if overlap: raise HTTPException(status_code=400, detail=f"Конфликт времени на экранах: {', '.join(overlap)}")
        except Exception as e:
            if isinstance(e, HTTPException): raise e

    new_item = {
        "id": int(datetime.now().timestamp()),
        "file": item.get("file"), "city": new_city,
        "screens": new_scr, "time_start": item.get("time_start"),
        "time_end": item.get("time_end"), "status": "Вычисляется..."
    }
    db["schedules"].append(new_item)
    save_db(db)
    return {"message": "Расписание сохранено"}

@app.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    db = load_db()
    db["schedules"] = [s for s in db["schedules"] if s["id"] != schedule_id]
    save_db(db)
    return {"message": "Удалено"}