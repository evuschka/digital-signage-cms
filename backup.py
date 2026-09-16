import os
import shutil
import sqlite3
import zipfile
from datetime import datetime

DB_FILE = "cms.db"
BACKUP_DIR = "backups"

def create_backup():
    """Механизм создания и хранения резервной копии"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_db_path = os.path.join(BACKUP_DIR, f"cms_temp_{timestamp}.db")
    zip_path = os.path.join(BACKUP_DIR, f"cms_backup_{timestamp}.zip")
    
    print("⏳ Подключение к рабочей базе данных...")
    try:
        # Безопасное копирование "на горячую" (совместимо с WAL-режимом)
        source_conn = sqlite3.connect(DB_FILE)
        dest_conn = sqlite3.connect(temp_db_path)
        with dest_conn:
            source_conn.backup(dest_conn)
        source_conn.close()
        dest_conn.close()
        
        # Сжатие копии в ZIP-архив
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(temp_db_path, "cms.db")
        
        # Удаляем несжатый временный файл
        os.remove(temp_db_path)
        print(f"✅ Успех: Резервная копия создана и сохранена в архив -> {zip_path}")
        return zip_path
    except Exception as e:
        print(f"❌ Ошибка при создании бэкапа: {e}")
        return None

def verify_backup(zip_path):
    """Механизм проверки восстановления (integrity check)"""
    if not os.path.exists(zip_path):
        print("❌ Ошибка: Файл резервной копии не найден.")
        return False

    print(f"🔍 Запуск проверки резервной копии: {zip_path}")
    extract_dir = "temp_verify"
    
    try:
        if not os.path.exists(extract_dir):
            os.makedirs(extract_dir)
            
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(extract_dir)
        
        extracted_db = os.path.join(extract_dir, "cms.db")
        
        # Строгая проверка целостности структуры SQLite
        conn = sqlite3.connect(extracted_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        integrity_result = cursor.fetchone()[0]
        
        # Тестовый запрос для подтверждения читаемости данных
        cursor.execute("SELECT COUNT(*) FROM users;")
        users_count = cursor.fetchone()[0]
        conn.close()
        
        # Очистка временных файлов тестирования
        shutil.rmtree(extract_dir)
        
        if integrity_result.lower() == "ok":
            print(f"✅ Проверка пройдена! База не повреждена. Найдено пользователей в копии: {users_count}")
            return True
        else:
            print("❌ ВНИМАНИЕ: Структура базы данных в архиве повреждена!")
            return False
            
    except Exception as e:
        print(f"❌ Критическая ошибка при проверке: {e}")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        return False

def restore_backup(zip_path):
    """Механизм восстановления с предварительной проверкой"""
    # 1. Сначала обязательно проверяем копию
    if not verify_backup(zip_path):
        print("🛑 Восстановление отменено из-за провала проверки безопасности.")
        return
        
    print("⏳ Начинаем процесс восстановления...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            extracted_db = zipf.extract("cms.db")
        
        # 2. Страховка: переименовываем текущую БД, а не удаляем её
        if os.path.exists(DB_FILE):
            backup_old = f"{DB_FILE}.old"
            if os.path.exists(backup_old):
                os.remove(backup_old)
            os.rename(DB_FILE, backup_old)
            print(f"ℹ️ Текущая БД сохранена как {backup_old}")
        
        # 3. Устанавливаем восстановленную БД
        os.rename(extracted_db, DB_FILE)
        print("✅ Успех: База данных успешно восстановлена из резервной копии!")
        print("⚠️ Рекомендуется перезапустить бэкенд (FastAPI), чтобы сбросить кэш подключений.")
    except Exception as e:
        print(f"❌ Ошибка восстановления: {e}")

if __name__ == "__main__":
    while True:
        print("\n=== Менеджер резервного копирования CMS ===")
        print("1. Создать резервную копию")
        print("2. Проверить целостность копии")
        print("3. Восстановить систему из копии")
        print("0. Выход")
        
        choice = input("Выберите действие (0-3): ")
        
        if choice == '1':
            create_backup()
        elif choice == '2':
            file_name = input("Введите путь к ZIP-файлу (например, backups/cms_backup_20260915_223000.zip): ")
            verify_backup(file_name)
        elif choice == '3':
            file_name = input("Введите путь к ZIP-файлу для восстановления: ")
            restore_backup(file_name)
        elif choice == '0':
            print("Выход из менеджера.")
            break
        else:
            print("Неверный выбор, попробуйте снова.")