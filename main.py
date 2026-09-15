from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
import secrets
import sqlite3
import os
import time
import random
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError
from io import BytesIO
import base64

app = FastAPI(title="Digital Signage CMS API (SQLite Edition)")

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
DB_FILE = "cms.db"

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

CITY_TZ_OFFSETS = {
    "global": 3,
    "moscow": 3,
    "spb": 3,
    "novocheboksarsk": 3,
    "yartsevo": 3,
    "azov": 3,
    "orenburg": 5,      # МСК+2
    "chernyakhovsk": 2  # МСК-1
}

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class ResetRequest(BaseModel):
    username: str

class AdminReset(BaseModel):
    username: str

# Инициализация базы данных SQLite
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL,
                        city_id TEXT NOT NULL
                    )''')
    
    # Таблица расписаний
    cursor.execute('''CREATE TABLE IF NOT EXISTS schedules (
                        id INTEGER PRIMARY KEY,
                        file TEXT,
                        playlist_id INTEGER,
                        city TEXT,
                        screens TEXT,
                        time_start TEXT,
                        time_end TEXT
                    )''')

    # Таблица плейлистов
    cursor.execute('''CREATE TABLE IF NOT EXISTS playlists (
                        id INTEGER PRIMARY KEY,
                        name TEXT,
                        city TEXT,
                        items TEXT,
                        "interval" INTEGER,
                        repeats INTEGER
                    )''')

    # Таблица корзины
    cursor.execute('''CREATE TABLE IF NOT EXISTS trash (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        size INTEGER,
                        data TEXT,
                        deleted_at TEXT
                    )''')

    # Таблица запросов на сброс пароля
    cursor.execute('''CREATE TABLE IF NOT EXISTS requests (
                        username TEXT PRIMARY KEY,
                        time TEXT
                    )''')
    
    conn.commit()
    
    # Проверяем, есть ли дефолтные пользователи, если нет — заполняем
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        for uname, udata in DEFAULT_USERS.items():
            cursor.execute('INSERT OR REPLACE INTO users (username, password, role, city_id) VALUES (?, ?, ?, ?)',
                           (uname, udata["password"], udata["role"], udata["city_id"]))
        conn.commit()
        
    conn.close()

# Вызываем инициализацию при старте
init_db()

def clean_old_records_sqlite():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = datetime.now()
    one_month_ago = now - timedelta(days=30)
    one_year_ago = now - timedelta(days=365)

    # Очистка старых расписаний (старше 1 года)
    cursor.execute('SELECT id, time_end FROM schedules')
    for row in cursor.fetchall():
        sch_id, time_end = row
        try:
            end_dt = datetime.fromisoformat(time_end)
            if now - end_dt >= timedelta(days=365):
                cursor.execute('DELETE FROM schedules WHERE id = ?', (sch_id,))
        except ValueError:
            pass

    # Очистка корзины (старше 30 дней)
    cursor.execute('SELECT id, deleted_at FROM trash')
    for row in cursor.fetchall():
        t_id, del_at = row
        try:
            del_dt = datetime.fromisoformat(del_at)
            if now - del_dt >= timedelta(days=30):
                cursor.execute('DELETE FROM trash WHERE id = ?', (t_id,))
        except ValueError:
            pass

    conn.commit()
    conn.close()

def get_dynamic_status(start_str, end_str, city):
    try:
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        offset = CITY_TZ_OFFSETS.get(city, 3)
        now_local = now_utc + timedelta(hours=offset)
        
        start = datetime.fromisoformat(start_str)
        end = datetime.fromisoformat(end_str)
        
        if now_local < start: return "Ожидание"
        elif start <= now_local <= end: return "Активен"
        else: return "Завершен"
    except ValueError: return "Ошибка даты"

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (credentials.username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not secrets.compare_digest(user["password"], credentials.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль", headers={"WWW-Authenticate": "Basic"})
    return {"username": user["username"], "role": user["role"], "city_id": user["city_id"]}

@app.post("/request-reset/")
def request_reset(data: ResetRequest):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (data.username,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('INSERT OR REPLACE INTO requests (username, time) VALUES (?, ?)', (data.username, time_str))
    conn.commit()
    conn.close()
    return {"message": "Запрос отправлен администратору"}

@app.get("/admin/users/")
def get_admin_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT username, role, city_id FROM users')
    users_safe = {row["username"]: {"role": row["role"], "city_id": row["city_id"]} for row in cursor.fetchall()}
    
    cursor.execute('SELECT username, time FROM requests')
    requests = [{"username": row["username"], "time": row["time"]} for row in cursor.fetchall()]
    
    conn.close()
    return {"users": users_safe, "requests": requests}

@app.post("/admin/reset-password/")
def admin_reset_password(data: AdminReset, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (data.username,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    cursor.execute('UPDATE users SET password = ? WHERE username = ?', ("user123", data.username))
    cursor.execute('DELETE FROM requests WHERE username = ?', (data.username,))
    conn.commit()
    conn.close()
    return {"message": f"Пароль пользователя {data.username} успешно сброшен до 'user123'"}

@app.post("/change-password/")
def change_password(data: PasswordChange, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    username = current_user["username"]
    
    cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    if row["password"] != data.old_password:
        conn.close()
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
        
    cursor.execute('UPDATE users SET password = ? WHERE username = ?', (data.new_password, username))
    conn.commit()
    conn.close()
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
    clean_old_records_sqlite()
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM schedules')
    schedules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
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
            if en > st: total_hours += (en - st).total_seconds() / 3600
        except: pass
            
    return {"total_shows": len(schedules), "total_hours": round(total_hours, 1), "status_counts": status_counts, "city_counts": city_counts}

# --- ПЛЕЙЛИСТЫ ---
@app.get("/playlists/")
def get_playlists(current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM playlists')
    playlists = []
    for row in cursor.fetchall():
        p = dict(row)
        p["items"] = json.loads(p["items"]) if p["items"] else []
        playlists.append(p)
    conn.close()
    
    if current_user["role"] != "admin":
        city = current_user["city_id"]
        playlists = [p for p in playlists if p.get("city") == city or p.get("city") == "global"]
    return {"playlists": playlists}

@app.post("/playlists/")
def create_playlist(item: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403, detail="Доступ запрещен")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    p_id = int(datetime.now().timestamp())
    name = item.get("name", "Плейлист")
    city = item.get("city", "global")
    items_json = json.dumps(item.get("items", []), ensure_ascii=False)
    interval = int(item.get("interval", 3))
    repeats = int(item.get("repeats", 1))
    
    cursor.execute('INSERT INTO playlists (id, name, city, items, "interval", repeats) VALUES (?, ?, ?, ?, ?, ?)',
                   (p_id, name, city, items_json, interval, repeats))
    conn.commit()
    conn.close()
    return {"message": "Плейлист успешно создан", "id": p_id}

@app.delete("/playlists/{playlist_id}")
def delete_playlist(playlist_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403, detail="Доступ запрещен")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM playlists WHERE id = ?', (playlist_id,))
    conn.commit()
    conn.close()
    return {"message": "Плейлист удален"}

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
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO trash (name, size, data, deleted_at) VALUES (?, ?, ?, ?)',
                       (file_key, file_size, file_body, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        return {"message": "Файл перемещен в корзину"}
    except ClientError as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/trash/")
def get_trash(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    clean_old_records_sqlite()
    
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT name, size, deleted_at FROM trash')
    trash_items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"trash": trash_items}

@app.post("/trash/restore/{file_name:path}")
def restore_file(file_name: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM trash WHERE name = ?', (file_name,))
    target_item = cursor.fetchone()
    if not target_item:
        conn.close()
        raise HTTPException(status_code=404)
        
    try:
        file_bytes = base64.b64decode(target_item["data"])
        s3_client.upload_fileobj(BytesIO(file_bytes), BUCKET_NAME, target_item["name"])
        cursor.execute('DELETE FROM trash WHERE name = ?', (file_name,))
        conn.commit()
        conn.close()
        return {"message": "Успешно восстановлено"}
    except ClientError as e: 
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/trash/empty/")
def empty_trash(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM trash')
    conn.commit()
    conn.close()
    return {"message": "Корзина очищена"}

@app.get("/screens/")
def get_screens(current_user: dict = Depends(get_current_user)):
    return {"screens": SCREENS_DB}

@app.get("/schedules/")
def get_schedules(current_user: dict = Depends(get_current_user)):
    clean_old_records_sqlite()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM schedules')
    schedules = []
    for row in cursor.fetchall():
        s = dict(row)
        s["screens"] = json.loads(s["screens"]) if s["screens"] else []
        s["status"] = get_dynamic_status(s.get("time_start"), s.get("time_end"), s.get("city", "global"))
        schedules.append(s)
        
    conn.close()
    
    if current_user["role"] != "admin":
        city = current_user["city_id"]
        schedules = [s for s in schedules if s.get("city") == city or s.get("city") == "global"]
        
    return {"schedules": schedules}

@app.post("/schedules/")
def create_schedule(item: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    
    try:
        new_st = datetime.fromisoformat(item.get("time_start"))
        new_en = datetime.fromisoformat(item.get("time_end"))
    except: raise HTTPException(status_code=400, detail="Ошибка формата времени")

    new_scr = item.get("screens", [])
    new_city = item.get("city", "global")

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM schedules')
    existing_schedules = [dict(row) for row in cursor.fetchall()]

    for s in existing_schedules:
        try:
            s_st = datetime.fromisoformat(s.get("time_start"))
            s_en = datetime.fromisoformat(s.get("time_end"))
            if new_st < s_en and s_st < new_en:
                s_scr = json.loads(s.get("screens", "[]"))
                if not s_scr and not new_scr and s.get("city") == new_city:
                    conn.close()
                    raise HTTPException(status_code=400, detail=f"Конфликт: Экраны филиала {new_city} уже заняты в это время.")
                overlap = set(new_scr).intersection(set(s_scr))
                if overlap: 
                    conn.close()
                    raise HTTPException(status_code=400, detail=f"Конфликт времени на экранах: {', '.join(overlap)}")
        except Exception as e:
            if isinstance(e, HTTPException): raise e

    sch_id = int(datetime.now().timestamp())
    file_val = item.get("file")
    playlist_id_val = item.get("playlist_id")
    screens_json = json.dumps(new_scr)
    
    cursor.execute('INSERT INTO schedules (id, file, playlist_id, city, screens, time_start, time_end) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (sch_id, file_val, playlist_id_val, new_city, screens_json, item.get("time_start"), item.get("time_end")))
    conn.commit()
    conn.close()
    
    return {"message": "Расписание сохранено"}

@app.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin": raise HTTPException(status_code=403)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
    conn.commit()
    conn.close()
    return {"message": "Удалено"}