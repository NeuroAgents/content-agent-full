#!/usr/bin/env python
# update_sources.py
import os
import sys
from dotenv import load_dotenv
import time
from loguru import logger

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули проекта
from src.utils.logger import setup_logger
from src.db import SupabaseClient

# Обновленные URL для источников
UPDATED_SOURCES = {
    "The Verge AI": {
        "rss_url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
    },
    "AI News": {
        "rss_url": "https://www.artificialintelligence-news.com/feed/"
    }
}

def main():
    """Функция для обновления источников в базе данных"""
    # Загружаем переменные окружения из .env файла
    load_dotenv()
    
    # Настраиваем логгирование
    setup_logger()
    logger.info("Запуск скрипта обновления источников")
    
    try:
        # Инициализируем клиент Supabase
        db_client = SupabaseClient()
        client = db_client.client
        
        # Получаем список всех источников
        logger.info("Получение списка источников...")
        try:
            response = client.table('sources').select('*').execute()
            sources = response.data
            logger.info(f"Получено {len(sources)} источников")
        except Exception as e:
            logger.error(f"Ошибка получения списка источников: {e}")
            return 1
        
        # Обновляем источники с новыми URL
        updated_count = 0
        for source in sources:
            source_name = source.get('name')
            if source_name in UPDATED_SOURCES:
                logger.info(f"Обновление источника: {source_name}")
                try:
                    update_data = UPDATED_SOURCES[source_name]
                    client.table('sources').update(update_data).eq('id', source['id']).execute()
                    logger.success(f"Источник {source_name} успешно обновлен")
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Ошибка обновления источника {source_name}: {e}")
                
                # Пауза между запросами
                time.sleep(0.5)
        
        logger.success(f"Обновление завершено. Обновлено источников: {updated_count}")
        
    except Exception as e:
        logger.exception(f"Ошибка при обновлении источников: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 