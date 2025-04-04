#!/usr/bin/env python
# check_content.py
"""
Скрипт для проверки длины контента сохраненных статей
"""
import os
import sys
import argparse
from dotenv import load_dotenv
from datetime import datetime, timedelta
import statistics

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули проекта
from src.utils.logger import setup_logger
from src.db import SupabaseClient
from loguru import logger

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Проверка длины контента сохраненных статей')
    parser.add_argument('--limit', type=int, default=10, 
                        help='Максимальное количество статей для проверки (по умолчанию: 10)')
    parser.add_argument('--min-length', type=int, default=500,
                        help='Минимальная ожидаемая длина контента (по умолчанию: 500)')
    parser.add_argument('--source-id', type=str,
                        help='ID конкретного источника для проверки')
    parser.add_argument('--log-level', type=str, default='INFO', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Уровень логирования (по умолчанию: INFO)')
    
    return parser.parse_args()

def main():
    """Основная функция для проверки статей"""
    args = parse_args()
    
    # Загружаем переменные окружения из .env файла
    load_dotenv()
    
    # Настраиваем логгирование
    setup_logger(log_level=args.log_level)
    
    logger.info(f"Проверка длины контента статей: лимит={args.limit}, мин. длина={args.min_length}")
    
    try:
        # Инициализируем клиент Supabase
        db_client = SupabaseClient()
        
        # Формируем запрос
        query = db_client.client.table('content_items').select('*')
        
        # Если указан source_id, фильтруем по нему
        if args.source_id:
            response = db_client.client.table('sources').select('name').eq('id', args.source_id).execute()
            if response.data:
                source_name = response.data[0].get('name', 'Неизвестный источник')
                logger.info(f"Проверка статей источника: {source_name} (ID: {args.source_id})")
                query = query.eq('source', source_name)
            else:
                logger.error(f"Источник с ID {args.source_id} не найден")
                return 1
        
        # Получаем статьи с ограничением по количеству
        query = query.order('created_at', desc=True).limit(args.limit)
        response = query.execute()
        
        if not response.data:
            logger.warning("Не найдено статей для проверки")
            return 0
            
        # Анализируем длину контента
        articles = response.data
        content_lengths = []
        short_content_count = 0
        
        for article in articles:
            content = article.get('content', '')
            title = article.get('title', 'Без заголовка')
            source = article.get('source', 'Неизвестный источник')
            url = article.get('url', 'Без URL')
            
            content_length = len(content)
            content_lengths.append(content_length)
            
            if content_length < args.min_length:
                logger.warning(f"Статья имеет короткий контент ({content_length} символов): {title} из {source}")
                logger.debug(f"URL: {url}")
                short_content_count += 1
                # Вывод начала контента для отладки
                if content:
                    logger.debug(f"Начало контента: {content[:100]}...")
            else:
                logger.info(f"Статья имеет достаточный контент ({content_length} символов): {title} из {source}")
        
        # Выводим статистику
        if content_lengths:
            avg_length = sum(content_lengths) / len(content_lengths)
            min_length = min(content_lengths)
            max_length = max(content_lengths)
            median_length = statistics.median(content_lengths)
            
            logger.success(
                f"Статистика контента для {len(articles)} статей:\n"
                f"Средняя длина: {avg_length:.2f} символов\n"
                f"Минимальная длина: {min_length} символов\n"
                f"Максимальная длина: {max_length} символов\n"
                f"Медианная длина: {median_length} символов\n"
                f"Статей с коротким контентом (<{args.min_length} символов): {short_content_count}"
            )
        
    except Exception as e:
        logger.exception(f"Ошибка при проверке статей: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 