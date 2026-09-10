from fastapi import FastAPI, UploadFile, File, HTTPException
import boto3
from botocore.exceptions import ClientError

app = FastAPI(title="Digital Signage CMS API")

s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='admin_cms',
    aws_secret_access_key='password123',
    region_name='us-east-1'
)

BUCKET_NAME = "digital-signage-media"

@app.get("/")
def read_root():
    return {"status": "Сервер работает, связь с MinIO установлена"}

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        s3_client.upload_fileobj(
            file.file,
            BUCKET_NAME,
            file.filename
        )
        return {
            "filename": file.filename,
            "message": "Файл успешно загружен в облачное хранилище!"
        }
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/")
def list_files():
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
        if "Contents" not in response:
            return {"files": []}
        
        files_list = []
        for obj in response["Contents"]:
            file_name = obj["Key"]
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': file_name},
                ExpiresIn=3600
            )
            files_list.append({
                "name": file_name,
                "size": obj["Size"],
                "url": url
            })
        
        return {"files": files_list}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

# метод удаления файлов
@app.delete("/files/{file_name}")
def delete_file(file_name: str):
    """
    Удаление файла из S3-хранилища MinIO по его имени
    """
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=file_name)
        return {"message": f"Файл '{file_name}' успешно удален"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))