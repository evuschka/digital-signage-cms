import os
import time
import random
import json
import sqlite3
import bcrypt
import secrets
import logging
import threading
import mimetypes
import base64
import urllib.parse
from contextlib import closing
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form, status, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from typing import List, Optional

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Digital Signage CMS API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(ClientError)
async def s3_exception_handler(request, exc: ClientError):
    error_code = exc.response.get("Error", {}).get("Code", "Unknown")
    error_message = exc.response.get("Error", {}).get("Message", str(exc))
    logger.error(f"S3 Error: {error_code} - {error_message}")
    return JSONResponse(status_code=500, content={"detail": f"Ошибка хранилища S3 [{error_code}]"})

MINIO_USER = os.getenv("MINIO_ROOT_USER", "admin_cms")
MINIO_PASS = os.getenv("MINIO_ROOT_PASSWORD", "password123")

s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id=MINIO_USER,
    aws_secret_access_key=MINIO_PASS,
    region_name='us-east-1'
)

BUCKET_NAME = "digital-signage-media"
MAX_STORAGE_BYTES = 100 * 1024 * 1024 * 1024
DB_FILE = "cms.db"
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'mkv', 'webm', 'avi', 'jpeg', 'jpg', 'png', 'webp', 'gif', 'svg', 'heic'}

upload_lock = threading.Lock()

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    return conn

DEFAULT_USERS = {
    "admin_main": {"password": "admin123", "role": "admin", "city_id": "global"},
    "user_msk": {"password": "user123", "role": "regional", "city_id": "moscow"}
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

CITY_TZ_OFFSETS = {
    "global": 3, "moscow": 3, "spb": 3, "novocheboksarsk": 3,
    "yartsevo": 3, "azov": 3, "orenburg": 5, "chernyakhovsk": 2
}

class PasswordChange(BaseModel):
    old_password: str = Field(..., max_length=100)
    new_password: str = Field(..., max_length=100)

class ResetRequest(BaseModel):
    username: str

class AdminReset(BaseModel):
    username: str

class UserCreate(BaseModel):
    username: str
    password: str = Field(..., max_length=100)
    role: str
    city_id: str

class PlaylistItem(BaseModel):
    file: str
    duration: int = 10

class PlaylistCreate(BaseModel):
    name: str
    city: str
    items: List[PlaylistItem]
    interval: int = 3
    repeats: int = 1

class ScheduleCreate(BaseModel):
    file: Optional[str] = None
    playlist_id: Optional[int] = None
    city: str
    screens: List[str]
    time_start: str
    time_end: str

def init_db():
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL, role TEXT NOT NULL, city_id TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS schedules (id INTEGER PRIMARY KEY, file TEXT, playlist_id INTEGER, city TEXT, screens TEXT, time_start TEXT, time_end TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS playlists (id INTEGER PRIMARY KEY, name TEXT, city TEXT, items TEXT, "interval" INTEGER, repeats INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS trash (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, size INTEGER, data TEXT, deleted_at TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS requests (username TEXT PRIMARY KEY, time TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS activity_log (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, action TEXT NOT NULL, details TEXT, timestamp TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS storage_history (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL, operation TEXT NOT NULL, size INTEGER, username TEXT NOT NULL, timestamp TEXT NOT NULL)''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedules_time ON schedules (time_start, time_end);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_playlists_city ON playlists (city);')
        
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            for uname, udata in DEFAULT_USERS.items():
                cursor.execute('INSERT OR REPLACE INTO users (username, password, role, city_id) VALUES (?, ?, ?, ?)',
                               (uname, get_password_hash(udata["password"]), udata["role"], udata["city_id"]))
        conn.commit()

init_db()

def log_action(username: str, action: str, details: str = ""):
    with closing(get_db_connection()) as conn:
        conn.execute('INSERT INTO activity_log (username, action, details, timestamp) VALUES (?, ?, ?, ?)',
                     (username, action, details, datetime.now().isoformat()))
        conn.commit()

def log_storage_action(filename: str, operation: str, size: int, username: str):
    with closing(get_db_connection()) as conn:
        conn.execute('INSERT INTO storage_history (filename, operation, size, username, timestamp) VALUES (?, ?, ?, ?, ?)',
                     (filename, operation, size, username, datetime.now().isoformat()))
        conn.commit()

def clean_old_records_sqlite():
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute('SELECT id, time_end FROM schedules')
        for row in cursor.fetchall():
            try:
                if now - datetime.fromisoformat(row[1]) >= timedelta(days=365):
                    cursor.execute('DELETE FROM schedules WHERE id = ?', (row[0],))
            except ValueError:
                pass
        cursor.execute('SELECT id, deleted_at FROM trash')
        for row in cursor.fetchall():
            try:
                if now - datetime.fromisoformat(row[1]) >= timedelta(days=30):
                    cursor.execute('DELETE FROM trash WHERE id = ?', (row[0],))
            except ValueError:
                pass
        conn.commit()

def get_dynamic_status(start_str, end_str, city):
    try:
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        offset = CITY_TZ_OFFSETS.get(city, 3)
        now_local = now_utc + timedelta(hours=offset)
        start = datetime.fromisoformat(start_str)
        end = datetime.fromisoformat(end_str)
        if now_local < start:
            return "Ожидание"
        elif start <= now_local <= end:
            return "Активен"
        else:
            return "Завершен"
    except ValueError:
        return "Ошибка даты"

def get_current_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    try:
        encoded_credentials = auth.split(" ")[1]
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded_credentials.split(":", 1)
    except Exception:
        raise HTTPException(status_code=401, detail="Неверные учетные данные")

    with closing(get_db_connection()) as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
    return {"username": user["username"], "role": user["role"], "city_id": user["city_id"]}

@app.post("/request-reset/")
@limiter.limit("3/minute")
def request_reset(request: Request, data: ResetRequest):
    with closing(get_db_connection()) as conn:
        if not conn.execute('SELECT * FROM users WHERE username = ?', (data.username,)).fetchone():
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        conn.execute('INSERT OR REPLACE INTO requests (username, time) VALUES (?, ?)',
                     (data.username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    log_action(data.username, "Сброс пароля", "Запрос на сброс пароля")
    return {"message": "Запрос отправлен администратору"}

@app.get("/admin/users/")
def get_admin_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    with closing(get_db_connection()) as conn:
        users_safe = {row["username"]: {"role": row["role"], "city_id": row["city_id"]}
                      for row in conn.execute('SELECT username, role, city_id FROM users').fetchall()}
        requests = [{"username": row["username"], "time": row["time"]}
                    for row in conn.execute('SELECT username, time FROM requests').fetchall()]
    return {"users": users_safe, "requests": requests}

@app.post("/admin/users/")
def create_user(data: UserCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    with closing(get_db_connection()) as conn:
        if conn.execute('SELECT * FROM users WHERE username = ?', (data.username,)).fetchone():
            raise HTTPException(status_code=400, detail="Пользователь уже существует")
        conn.execute('INSERT INTO users (username, password, role, city_id) VALUES (?, ?, ?, ?)',
                     (data.username, get_password_hash(data.password), data.role, data.city_id))
        conn.commit()
    log_action(current_user["username"], "Создание пользователя", f"Логин: {data.username}, Роль: {data.role}")
    return {"message": "Пользователь успешно создан"}

@app.delete("/admin/users/{username}")
def delete_user(username: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    if username == current_user["username"]:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")
    with closing(get_db_connection()) as conn:
        conn.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.execute('DELETE FROM requests WHERE username = ?', (username,))
        conn.commit()
    log_action(current_user["username"], "Удаление пользователя", f"Логин: {username}")
    return {"message": "Пользователь удален"}

@app.post("/admin/reset-password/")
def admin_reset_password(data: AdminReset, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    with closing(get_db_connection()) as conn:
        if not conn.execute('SELECT * FROM users WHERE username = ?', (data.username,)).fetchone():
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        temp_password = secrets.token_urlsafe(6)
        conn.execute('UPDATE users SET password = ? WHERE username = ?',
                     (get_password_hash(temp_password), data.username))
        conn.execute('DELETE FROM requests WHERE username = ?', (data.username,))
        conn.commit()
    log_action(current_user["username"], "Сброс пароля", f"Выдан временный пароль для: {data.username}")
    return {"message": "Пароль успешно сброшен!", "temp_password": temp_password}

@app.post("/change-password/")
def change_password(data: PasswordChange, current_user: dict = Depends(get_current_user)):
    with closing(get_db_connection()) as conn:
        row = conn.execute('SELECT password FROM users WHERE username = ?', (current_user["username"],)).fetchone()
        if not verify_password(data.old_password, row["password"]):
            raise HTTPException(status_code=400, detail="Неверный текущий пароль")
        conn.execute('UPDATE users SET password = ? WHERE username = ?',
                     (get_password_hash(data.new_password), current_user["username"]))
        conn.commit()
    log_action(current_user["username"], "Смена пароля", "Пользователь сменил пароль")
    return {"message": "Пароль успешно изменен"}

@app.get("/history/")
def get_history(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    with closing(get_db_connection()) as conn:
        logs = [dict(row) for row in conn.execute('SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 200').fetchall()]
    return {"history": logs}

@app.get("/storage-history/")
def get_storage_history(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    with closing(get_db_connection()) as conn:
        history = [dict(row) for row in conn.execute('SELECT * FROM storage_history ORDER BY timestamp DESC LIMIT 200').fetchall()]
    return {"storage_history": history}

def get_total_bucket_size():
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
        return sum(obj['Size'] for obj in response.get('Contents', []))
    except ClientError as e:
        logger.error(f"S3 connection error: {e}")
        return 0

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
        if current_user["role"] != "admin" and current_user["city_id"] != city:
            continue
        for sc in screens:
            random.seed(f"{sc}_{current_minute}")
            status_list.append({
                "city": city,
                "screen": sc,
                "status": "В сети" if random.choice([True, True, True, False]) else "Офлайн"
            })
    return {"monitoring": status_list}

@app.get("/analytics/")
def get_analytics(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    background_tasks.add_task(clean_old_records_sqlite)
    
    with closing(get_db_connection()) as conn:
        schedules = [dict(row) for row in conn.execute('SELECT * FROM schedules').fetchall()]
        
    total_hours = 0
    status_counts = {"Ожидание": 0, "Активен": 0, "Завершен": 0}
    city_counts = {}
    for s in schedules:
        city = s.get("city", "global")
        st_status = get_dynamic_status(s.get("time_start"), s.get("time_end"), city)
        status_counts[st_status] = status_counts.get(st_status, 0) + 1
        city_counts[city] = city_counts.get(city, 0) + 1
        try:
            st = datetime.fromisoformat(s.get("time_start"))
            en = datetime.fromisoformat(s.get("time_end"))
            if en > st:
                total_hours += (en - st).total_seconds() / 3600
        except Exception:
            pass
            
    return {"total_shows": len(schedules), "total_hours": round(total_hours, 1), "status_counts": status_counts, "city_counts": city_counts}

@app.get("/playlists/")
def get_playlists(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    with closing(get_db_connection()) as conn:
        playlists = []
        for row in conn.execute('SELECT * FROM playlists').fetchall():
            p = dict(row)
            p["items"] = json.loads(p["items"]) if p["items"] else []
            playlists.append(p)
    return {"playlists": playlists}

@app.post("/playlists/")
def create_playlist(item: PlaylistCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    p_id = int(datetime.now().timestamp())
    items_json = json.dumps([i.model_dump() for i in item.items], ensure_ascii=False)
    
    with closing(get_db_connection()) as conn:
        conn.execute('INSERT INTO playlists (id, name, city, items, "interval", repeats) VALUES (?, ?, ?, ?, ?, ?)',
                     (p_id, item.name, item.city, items_json, item.interval, item.repeats))
        conn.commit()
    
    log_action(current_user["username"], "Создание плейлиста", f"Название: {item.name}, Город: {item.city}")
    return {"message": "Плейлист успешно создан", "id": p_id}

@app.delete("/playlists/{playlist_id}")
def delete_playlist(playlist_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    with closing(get_db_connection()) as conn:
        conn.execute('DELETE FROM playlists WHERE id = ?', (playlist_id,))
        conn.commit()
    log_action(current_user["username"], "Удаление плейлиста", f"ID плейлиста: {playlist_id}")
    return {"message": "Плейлист удален"}

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), target_city: str = Form(None), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    
    filename = os.path.basename(file.filename or "")
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Формат '.{ext}' не поддерживается.")
    
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    with upload_lock:
        if get_total_bucket_size() + file_size > MAX_STORAGE_BYTES:
            raise HTTPException(status_code=400, detail="Превышен лимит хранилища в 100 ГБ")
        
        folder = target_city if target_city else "global"
        file_key = f"{folder}/{filename}"
        
        try:
            s3_client.head_object(Bucket=BUCKET_NAME, Key=file_key)
            name, ex = os.path.splitext(filename)
            filename = f"{name}_{int(time.time())}{ex}"
            file_key = f"{folder}/{filename}"
        except ClientError:
            pass
        
        content_type, _ = mimetypes.guess_type(filename)
        s3_client.upload_fileobj(file.file, BUCKET_NAME, file_key, ExtraArgs={'ContentType': content_type or 'application/octet-stream'})
        
    log_action(current_user["username"], "Импорт файла", f"Файл: {filename} в {folder}")
    log_storage_action(file_key, "ЗАГРУЗКА", file_size, current_user["username"])
    return {"success": True, "message": f"Файл {filename} импортирован в {folder}"}

@app.get("/media-file/{file_key:path}")
def get_media_file(file_key: str):
    decoded_key = urllib.parse.unquote(file_key)
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=decoded_key)
        content_type, _ = mimetypes.guess_type(decoded_key)
        if not content_type:
            content_type = response.get('ContentType', 'application/octet-stream')

        safe_filename = urllib.parse.quote(os.path.basename(decoded_key))
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"inline; filename*=UTF-8''{safe_filename}"
        }

        return StreamingResponse(
            response['Body'], 
            media_type=content_type,
            headers=headers
        )
    except ClientError as e:
        logger.error(f"S3 proxy error for {decoded_key}: {e}")
        raise HTTPException(status_code=404, detail="Файл не найден в хранилище")

@app.get("/files/")
@limiter.limit("60/minute")
def list_files(request: Request, current_user: dict = Depends(get_current_user)):
    prefix = "" if current_user["role"] == "admin" else f"{current_user['city_id']}/"
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    files_list = []
    
    for obj in response.get("Contents", []):
        if not obj["Key"].startswith("trash/"):
            parts = obj["Key"].split('/')
            encoded_key = "/".join(urllib.parse.quote(p) for p in parts)
            files_list.append({
                "name": obj["Key"], 
                "size": obj["Size"], 
                "last_modified": obj["LastModified"].isoformat(),
                "url": f"http://localhost:8000/media-file/{encoded_key}"
            })
    return {"files": files_list}

@app.delete("/files/{file_key:path}")
def delete_file(file_key: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    
    decoded_key = urllib.parse.unquote(file_key)
    if ".." in decoded_key:
        raise HTTPException(status_code=400, detail="Недопустимое имя файла")

    try:
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=decoded_key)
        file_size = obj['ContentLength']
        
        trash_key = f"trash/{int(time.time())}_{os.path.basename(decoded_key)}"
        s3_client.copy_object(Bucket=BUCKET_NAME, CopySource={'Bucket': BUCKET_NAME, 'Key': decoded_key}, Key=trash_key)
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=decoded_key)
        
        with closing(get_db_connection()) as conn:
            conn.execute('INSERT INTO trash (name, size, data, deleted_at) VALUES (?, ?, ?, ?)',
                         (decoded_key, file_size, trash_key, datetime.now().isoformat()))
            conn.commit()
        
        log_action(current_user["username"], "Удаление файла", f"Файл: {decoded_key} перемещен в корзину")
        log_storage_action(decoded_key, "В КОРЗИНУ", file_size, current_user["username"])
        return {"message": "Файл перемещен в корзину"}
    except ClientError as e:
        logger.error(f"S3 Error on delete: {e}")
        raise HTTPException(status_code=500, detail="Файл не найден в S3 или ошибка доступа")

@app.get("/trash/")
def get_trash(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    background_tasks.add_task(clean_old_records_sqlite)
    with closing(get_db_connection()) as conn:
        trash_items = [dict(row) for row in conn.execute('SELECT name, size, deleted_at FROM trash').fetchall()]
    return {"trash": trash_items}

@app.post("/trash/restore/{file_name:path}")
def restore_file(file_name: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    
    decoded_name = urllib.parse.unquote(file_name)
    with closing(get_db_connection()) as conn:
        target_item = conn.execute('SELECT * FROM trash WHERE name = ?', (decoded_name,)).fetchone()
        if not target_item:
            raise HTTPException(status_code=404, detail="Файл не найден в корзине БД")
            
        try:
            trash_key = target_item["data"]
            file_size = target_item["size"]
            
            s3_client.copy_object(Bucket=BUCKET_NAME, CopySource={'Bucket': BUCKET_NAME, 'Key': trash_key}, Key=decoded_name)
            s3_client.delete_object(Bucket=BUCKET_NAME, Key=trash_key)
            
            conn.execute('DELETE FROM trash WHERE name = ?', (decoded_name,))
            conn.commit()
            
            log_action(current_user["username"], "Восстановление", f"Файл: {decoded_name}")
            log_storage_action(decoded_name, "ВОССТАНОВЛЕНИЕ", file_size, current_user["username"])
            return {"message": "Успешно восстановлено"}
        except ClientError as e:
            logger.error(f"S3 Error on restore: {e}")
            raise HTTPException(status_code=500, detail="Ошибка при восстановлении файла из S3")

@app.delete("/trash/empty/")
def empty_trash(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    with closing(get_db_connection()) as conn:
        trashed = conn.execute('SELECT name, data FROM trash').fetchall()
        for t in trashed:
            try:
                s3_client.delete_object(Bucket=BUCKET_NAME, Key=t["data"])
                log_storage_action(t["name"], "УДАЛЕНО НАВСЕГДА", 0, current_user["username"])
            except Exception as e:
                logger.warning(f"Ошибка физического удаления {t['name']}: {e}")
                
        conn.execute('DELETE FROM trash')
        conn.commit()
    
    log_action(current_user["username"], "Очистка корзины", "Все файлы удалены безвозвратно")
    return {"message": "Корзина очищена"}

@app.get("/screens/")
def get_screens(current_user: dict = Depends(get_current_user)):
    return {"screens": SCREENS_DB}

@app.get("/schedules/")
def get_schedules(background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    background_tasks.add_task(clean_old_records_sqlite)
    with closing(get_db_connection()) as conn:
        schedules = []
        for row in conn.execute('SELECT * FROM schedules').fetchall():
            s = dict(row)
            s["screens"] = json.loads(s["screens"]) if s["screens"] else []
            s["status"] = get_dynamic_status(s.get("time_start"), s.get("time_end"), s.get("city", "global"))
            schedules.append(s)
            
    if current_user["role"] != "admin":
        schedules = [s for s in schedules if s.get("city") in [current_user["city_id"], "global"]]
    return {"schedules": schedules}

@app.get("/schedules/active")
def get_active_schedule(city: str = "moscow", screen: int = 0):
    with closing(get_db_connection()) as conn:
        schedules = [dict(row) for row in conn.execute('SELECT * FROM schedules').fetchall()]
    
    filtered = []
    for s in schedules:
        s_city = s.get("city", "global")
        if city == "global" or s_city == city or s_city == "global":
            filtered.append(s)
            
    items = []
    for s in filtered:
        playlist_id = s.get("playlist_id")
        if playlist_id:
            with closing(get_db_connection()) as conn:
                pl = conn.execute('SELECT items FROM playlists WHERE id = ?', (playlist_id,)).fetchone()
                if pl and pl["items"]:
                    try:
                        pl_items = json.loads(pl["items"])
                        items.extend(pl_items)
                    except Exception:
                        pass
        elif s.get("file"):
            items.append({"file": s.get("file"), "duration": 10})
            
    return {"items": items}

@app.post("/schedules/")
def create_schedule(item: ScheduleCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    try:
        new_st = datetime.fromisoformat(item.time_start)
        new_en = datetime.fromisoformat(item.time_end)
    except Exception:
        raise HTTPException(status_code=400, detail="Ошибка формата времени. Ожидается ISO 8601")

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    offset = CITY_TZ_OFFSETS.get(item.city, 3)
    now_local = now_utc + timedelta(hours=offset)

    if new_en <= new_st:
        raise HTTPException(status_code=400, detail="Время окончания должно быть позже начала.")
    if new_st < now_local - timedelta(minutes=2):
        raise HTTPException(status_code=400, detail=f"Нельзя запланировать в прошлом! Местное время: {now_local.strftime('%H:%M')}.")

    with closing(get_db_connection()) as conn:
        existing_schedules = [dict(row) for row in conn.execute('SELECT * FROM schedules').fetchall()]
        for s in existing_schedules:
            try:
                s_st = datetime.fromisoformat(s.get("time_start"))
                s_en = datetime.fromisoformat(s.get("time_end"))
                if new_st < s_en and s_st < new_en:
                    s_scr = json.loads(s.get("screens", "[]"))
                    if not s_scr and not item.screens and s.get("city") == item.city:
                        raise HTTPException(status_code=400, detail=f"Конфликт: Экраны филиала {item.city} уже заняты в это время.")
                    overlap = set(item.screens).intersection(set(s_scr))
                    if overlap:
                        raise HTTPException(status_code=400, detail=f"Конфликт времени на экранах: {', '.join(overlap)}")
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise e

        sch_id = int(datetime.now().timestamp())
        conn.execute('INSERT INTO schedules (id, file, playlist_id, city, screens, time_start, time_end) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (sch_id, item.file, item.playlist_id, item.city, json.dumps(item.screens), item.time_start, item.time_end))
        conn.commit()
    
    tgt = f"Плейлист ID {item.playlist_id}" if item.playlist_id else f"Файл {item.file}"
    log_action(current_user["username"], "Планирование", f"Запуск: {tgt}, Город: {item.city}")
    return {"message": "Расписание сохранено"}

@app.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403)
    with closing(get_db_connection()) as conn:
        conn.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
        conn.commit()
    log_action(current_user["username"], "Удаление", f"ID расписания: {schedule_id}")
    return {"message": "Удалено"}

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Файл index.html не найден в папке проекта!</h1>"