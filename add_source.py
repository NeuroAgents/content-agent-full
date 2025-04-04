#!/usr/bin/env python
# add_source.py
"""
Скрипт для добавления нового источника новостей в базу данных
"""
import os
import sys
from dotenv import load_dotenv
from loguru import logger

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули проекта
from src.utils.logger import setup_logger
from src.db import SupabaseClient

def main():
    """Функция для добавления нового источника"""
    # Загружаем переменные окружения из .env файла
    load_dotenv()
    
    # Настраиваем логгирование
    setup_logger()
    logger.info("Запуск скрипта добавления нового источника")
    
    try:
        # Инициализируем клиент Supabase
        db_client = SupabaseClient()
        
        # Определяем новый источник
        new_source = {
            'id': 'a6ae0d19-f828-4f8c-a095-97ba74faee96',
            'name': 'AI In Healthcare News',
            'url': 'https://www.aiin.healthcare',
            'rss_url': 'https://www.aiin.healthcare/rss.xml',
            'parser_type': 'rss',
            'active': True
        }
        
        # Добавляем источник в базу данных
        result = db_client.client.table('sources').insert(new_source).execute()
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Ошибка добавления источника: {result.error}")
            return 1
        
        logger.success(f"Источник успешно добавлен: {new_source['name']}")
        
    except Exception as e:
        logger.exception(f"Ошибка при добавлении источника: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 