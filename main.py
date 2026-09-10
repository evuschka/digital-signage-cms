from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
import boto3
import secrets
from botocore.exceptions import ClientError

app = FastAPI(title="Digital Signage CMS API")

# Настройка CORS для работы авторизации из браузера
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
MAX_STORAGE_BYTES = 100 * 1024 * 1024 * 1024  # 100 GB

security = HTTPBasic()

# База данных пользователей (в реальности хранится в PostgreSQL)
USERS = {
    "admin": {"password": "admin123", "role": "admin", "city": "all"},
    "moscow_user": {"password": "user123", "role": "user", "city": "moscow"}
}

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    user = USERS.get(credentials.username)
    if not user or not secrets.compare_digest(user["password"], credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return {"username": credentials.username, **user}

def get_total_bucket_size():
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
        return sum(obj['Size'] for obj in response.get('Contents', []))
    except ClientError:
        return 0

@app.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    target_city: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    if get_total_bucket_size() + file.size > MAX_STORAGE_BYTES:
        raise HTTPException(status_code=400, detail="Превышен глобальный лимит хранилища в 100 ГБ")

    # Логика изоляции папок
    folder = current_user["city"]
    if current_user["role"] == "admin":
        folder = target_city if target_city else "global"
    
    file_key = f"{folder}/{file.filename}"

    try:
        s3_client.upload_fileobj(file.file, BUCKET_NAME, file_key)
        return {"message": f"Файл успешно загружен в папку {folder}/"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/")
def list_files(current_user: dict = Depends(get_current_user)):
    try:
        # Пользователь видит только свою папку, админ видит всё
        prefix = "" if current_user["role"] == "admin" else f"{current_user['city']}/"
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
        
        files_list = []
        for obj in response.get("Contents", []):
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': obj["Key"]},
                ExpiresIn=3600
            )
            files_list.append({"name": obj["Key"], "size": obj["Size"], "url": url})
        
        return {"files": files_list}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/{file_key:path}")
def delete_file(file_key: str, current_user: dict = Depends(get_current_user)):
    # Защита: региональный пользователь не может удалить чужой файл
    if current_user["role"] != "admin" and not file_key.startswith(f"{current_user['city']}/"):
        raise HTTPException(status_code=403, detail="Нет прав на удаление этого файла")
        
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=file_key)
        return {"message": "Файл удален"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))