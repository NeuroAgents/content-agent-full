#!/usr/bin/env python
# apply_migration.py - Скрипт для применения SQL-миграции

import os
import argparse
import logging
from typing import List, Tuple

from dotenv import load_dotenv
from supabase import create_client, Client as SupabaseClient

# Настройка логирования
def setup_logger() -> logging.Logger:
    """Инициализация и настройка логгера."""
    logger = logging.getLogger("migration")
    logger.setLevel(logging.INFO)
    
    # Создаем обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Задаем формат логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчик к логгеру
    logger.addHandler(console_handler)
    
    return logger

# Инициализация логгера
logger = setup_logger()

def read_migration_file(file_path: str) -> List[str]:
    """Чтение SQL-миграции из файла."""
    if not os.path.exists(file_path):
        logger.error(f"Файл миграции {file_path} не найден")
        return []
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Разделяем на отдельные SQL-запросы по точке с запятой (упрощенная версия)
        # В более сложных случаях может потребоваться более продвинутый парсер SQL
        statements = [stmt.strip() for stmt in content.split(';') if stmt.strip()]
        return statements
    
    except Exception as e:
        logger.error(f"Ошибка при чтении файла миграции: {e}")
        return []

def apply_migration(client: SupabaseClient, sql_statements: List[str]) -> Tuple[int, int]:
    """Применение SQL-миграции к базе данных."""
    success_count = 0
    error_count = 0
    
    for i, statement in enumerate(sql_statements):
        try:
            logger.info(f"Выполнение SQL-запроса #{i+1}...")
            response = client.rpc('execute_sql', {'query': statement})
            success_count += 1
            logger.info(f"SQL-запрос #{i+1} успешно выполнен")
            
        except Exception as e:
            error_count += 1
            logger.error(f"Ошибка при выполнении SQL-запроса #{i+1}: {e}")
    
    return success_count, error_count

def check_field_exists(client: SupabaseClient, table: str, field: str) -> bool:
    """Проверка существования поля в таблице."""
    try:
        query = f"SELECT {field} FROM {table} LIMIT 1"
        response = client.rpc('execute_sql', {'query': query})
        return True
    except Exception:
        return False

def main():
    """Основная функция программы."""
    parser = argparse.ArgumentParser(description='Применение SQL-миграции к базе данных Supabase')
    parser.add_argument('--migration-file', type=str, default='supabase/migrations/20250404000000_add_translation_fields.sql',
                        help='Путь к файлу миграции')
    parser.add_argument('--dry-run', action='store_true', help='Режим без внесения изменений в базу данных')
    args = parser.parse_args()
    
    logger.info("Запуск применения миграции")
    logger.info(f"Файл миграции: {args.migration_file}")
    logger.info(f"Dry run: {args.dry_run}")
    
    # Загружаем переменные окружения
    load_dotenv()
    
    # Получаем настройки подключения к Supabase
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL и SUPABASE_KEY должны быть установлены в .env файле")
        return
    
    try:
        # Инициализируем клиент Supabase
        client = create_client(supabase_url, supabase_key)
        
        # Проверяем, существует ли уже поле title_ru
        field_exists = check_field_exists(client, 'content_items', 'title_ru')
        
        if field_exists:
            logger.info("Поля для переводов уже существуют в базе данных")
            return
        
        # Чтение файла миграции
        sql_statements = read_migration_file(args.migration_file)
        
        if not sql_statements:
            logger.error("Нет SQL-запросов для выполнения")
            return
        
        logger.info(f"Подготовлено {len(sql_statements)} SQL-запросов для выполнения")
        
        # В режиме dry run просто выводим запросы
        if args.dry_run:
            logger.info("Режим dry run, запросы не будут выполнены")
            for i, stmt in enumerate(sql_statements):
                logger.info(f"SQL #{i+1}: {stmt}")
            return
        
        # Применение миграции
        success_count, error_count = apply_migration(client, sql_statements)
        
        logger.info(f"Миграция завершена. Успешно: {success_count}, Ошибок: {error_count}")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении миграции: {e}")

if __name__ == "__main__":
    main() 