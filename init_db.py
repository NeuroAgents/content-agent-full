# init_db.py
import os
import sys
import json
from dotenv import load_dotenv
from loguru import logger
import time

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули проекта
from src.utils.logger import setup_logger
from src.db import SupabaseClient

# Пример источников для добавления
SAMPLE_SOURCES = [
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/",
        "rss_url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "parser_type": "rss",
        "active": True
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/ai-artificial-intelligence",
        "rss_url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "parser_type": "rss",
        "active": True
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/",
        "rss_url": "https://venturebeat.com/category/ai/feed/",
        "parser_type": "rss",
        "active": True
    },
    {
        "name": "AI News",
        "url": "https://www.artificialintelligence-news.com/",
        "rss_url": "https://www.artificialintelligence-news.com/feed/",
        "parser_type": "rss",
        "active": True
    }
]

def main():
    """Основная функция для инициализации базы данных"""
    # Загружаем переменные окружения из .env файла
    load_dotenv()
    
    # Настраиваем логгирование
    setup_logger()
    logger.info("Запуск скрипта инициализации базы данных")
    
    try:
        # Инициализируем клиент Supabase
        db_client = SupabaseClient()
        client = db_client.client
        
        # Проверяем существование таблицы sources
        logger.info("Проверка существования таблицы sources...")
        try:
            response = client.table('sources').select('count').limit(1).execute()
            logger.info("Таблица sources уже существует")
        except Exception as e:
            logger.warning(f"Таблица sources не существует, нужно создать таблицы через Supabase SQL Editor: {e}")
            logger.info("Пожалуйста, выполните SQL запрос из файла supabase/migrations/20231101000000_create_content_tables.sql в Supabase SQL Editor")
            return 1
        
        # Добавляем тестовые источники
        logger.info("Добавление тестовых источников...")
        for source in SAMPLE_SOURCES:
            # Проверяем, существует ли источник с таким именем
            check = client.table('sources').select('id').eq('name', source['name']).execute()
            
            if check.data:
                logger.info(f"Источник {source['name']} уже существует")
                continue
                
            # Добавляем источник
            try:
                client.table('sources').insert(source).execute()
                logger.info(f"Добавлен источник: {source['name']}")
            except Exception as e:
                logger.error(f"Ошибка при добавлении источника {source['name']}: {e}")
            
            # Пауза между запросами
            time.sleep(0.5)
        
        logger.success("Инициализация завершена")
        logger.info("Используйте Supabase SQL Editor для создания таблиц, если они не существуют")
        logger.info("SQL скрипт находится в файле: supabase/migrations/20231101000000_create_content_tables.sql")
        
    except Exception as e:
        logger.exception(f"Ошибка при инициализации базы данных: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 