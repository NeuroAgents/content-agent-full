#!/usr/bin/env python
# daily_update.py
import os
import sys
import argparse
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули проекта
from src.utils.logger import setup_logger
from src.db import SupabaseClient
from update_content import fetch_full_content

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Ежедневное обновление статей из источников')
    parser.add_argument('--limit', type=int, default=10, 
                        help='Максимальное количество статей для каждого источника (по умолчанию: 10)')
    parser.add_argument('--age', type=int, default=1,
                        help='Максимальный возраст статей в днях (по умолчанию: 1)')
    parser.add_argument('--log-level', type=str, default='INFO', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Уровень логирования (по умолчанию: INFO)')
    parser.add_argument('--all-sources', action='store_true',
                        help='Обрабатывать все источники, игнорируя дату последнего обновления')
    parser.add_argument('--dry-run', action='store_true',
                        help='Запуск без фактического сохранения в базу данных')
    parser.add_argument('--source-id', type=str,
                        help='ID конкретного источника для обработки')
    
    return parser.parse_args()

def get_sources_to_update(db_client, force_all=False, source_id=None):
    """
    Получение списка источников для обновления
    
    Args:
        db_client: Клиент базы данных
        force_all: Обновлять все источники независимо от last_fetch_at
        source_id: ID конкретного источника для обработки
        
    Returns:
        list: Список источников для обновления
    """
    try:
        # Если указан конкретный source_id, получаем только его
        if source_id:
            response = db_client.client.table('sources').select('*').eq('id', source_id).execute()
            if response.data:
                logger.info(f"Получен источник с ID {source_id}")
                return response.data
            else:
                logger.error(f"Источник с ID {source_id} не найден")
                return []
        
        # Получаем все активные источники
        if force_all:
            response = db_client.client.table('sources').select('*').eq('active', True).execute()
            logger.info(f"Получено {len(response.data)} активных источников (force_all=True)")
            return response.data
        
        # Или только те, которые нужно обновить (последнее обновление более 12 часов назад)
        cutoff_time = (datetime.now() - timedelta(hours=12)).isoformat()
        
        # Получаем источники, которые никогда не обновлялись
        null_response = db_client.client.table('sources').select('*')\
            .eq('active', True)\
            .is_('last_fetch_at', 'null')\
            .execute()
            
        # Получаем источники, которые обновлялись давно
        old_response = db_client.client.table('sources').select('*')\
            .eq('active', True)\
            .lt('last_fetch_at', cutoff_time)\
            .execute()
        
        # Объединяем результаты
        sources = null_response.data + old_response.data
        
        # Удаляем дубликаты, если есть
        unique_sources = []
        source_ids = set()
        
        for source in sources:
            if source['id'] not in source_ids:
                source_ids.add(source['id'])
                unique_sources.append(source)
        
        logger.info(f"Получено {len(unique_sources)} источников для обновления")
        return unique_sources
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка источников: {e}")
        return []

def main():
    """Основная функция для обновления статей"""
    args = parse_args()
    
    # Загружаем переменные окружения из .env файла
    load_dotenv()
    
    # Настраиваем логгирование
    setup_logger(log_level=args.log_level)
    
    start_time = time.time()
    logger.info(f"Запуск ежедневного обновления статей: лимит={args.limit}, возраст={args.age} дней")
    
    try:
        # Инициализируем клиент Supabase
        db_client = SupabaseClient()
        
        # Получаем источники для обновления
        sources = get_sources_to_update(db_client, args.all_sources, args.source_id)
        
        if not sources:
            logger.warning("Нет источников для обновления")
            return 0
        
        # Импортируем парсеры здесь, чтобы избежать циклических импортов
        from src.parsers import get_parser_for_source
        
        # Статистика
        total_sources = len(sources)
        processed_sources = 0
        total_found = 0
        total_added = 0
        total_skipped = 0
        error_count = 0
        
        # Обрабатываем каждый источник
        for source in sources:
            source_name = source.get('name', 'Неизвестный источник')
            logger.info(f"Обработка источника: {source_name}")
            
            try:
                # Получаем подходящий парсер для источника
                parser = get_parser_for_source(source)
                
                if not parser:
                    logger.error(f"Не удалось создать парсер для источника {source_name}")
                    error_count += 1
                    continue
                
                # Получаем статьи
                articles = parser.fetch_articles()
                
                # Фильтруем статьи по возрасту
                if args.age > 0 and articles:
                    cutoff_date = datetime.now() - timedelta(days=args.age)
                    filtered_articles = []
                    
                    for article in articles:
                        pub_date = article.get('published_at')
                        if pub_date and isinstance(pub_date, datetime):
                            # Преобразуем обе даты к timezone-naive формату для корректного сравнения
                            if pub_date.tzinfo is not None:
                                # Если дата timezone-aware, конвертируем в timezone-naive
                                pub_date = pub_date.replace(tzinfo=None)
                            
                            if pub_date >= cutoff_date:
                                filtered_articles.append(article)
                    
                    if len(filtered_articles) < len(articles):
                        logger.info(f"Отфильтровано {len(articles) - len(filtered_articles)} устаревших статей")
                        articles = filtered_articles
                
                # Применяем лимит, если указан
                if args.limit > 0 and len(articles) > args.limit:
                    logger.info(f"Применяем лимит в {args.limit} статей (всего найдено: {len(articles)})")
                    articles = articles[:args.limit]
                
                # Сохраняем статистику по количеству статей
                found_count = len(articles)
                total_found += found_count
                
                logger.info(f"Получено {found_count} статей из {source_name}")
                
                # Для каждой статьи загружаем полный контент, если он слишком короткий
                if not args.dry_run and articles:
                    for i, article in enumerate(articles):
                        content = article.get('content', '')
                        # Если контент слишком короткий, загружаем полный
                        if len(content) < 500:
                            url = article.get('url')
                            if url:
                                logger.info(f"Загрузка полного контента для статьи: {article.get('title')} (текущая длина: {len(content)})")
                                full_content = fetch_full_content(url)
                                if full_content:
                                    articles[i]['content'] = full_content
                                    logger.info(f"Загружен полный контент ({len(full_content)} символов)")
                                # Небольшая пауза между запросами
                                if i < len(articles) - 1:
                                    time.sleep(0.5)
                
                # Сохраняем статьи, если это не dry-run
                if not args.dry_run and articles:
                    result = db_client.save_articles(articles)
                    added = result.get('added', 0)
                    skipped = result.get('skipped', 0)
                    
                    total_added += added
                    total_skipped += skipped
                    
                    logger.info(f"Результат сохранения для {source_name}: добавлено {added}, пропущено {skipped}")
                    
                    # Обновляем время последнего обновления источника
                    db_client.update_source_last_fetch(source['id'])
                else:
                    logger.info(f"Dry run: найдено {found_count} статей из {source_name}")
                
                processed_sources += 1
                
                # Пауза между источниками для снижения нагрузки
                if processed_sources < total_sources:
                    time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Ошибка при обработке источника {source_name}: {e}")
                error_count += 1
        
        # Выводим итоговую статистику
        elapsed_time = time.time() - start_time
        logger.success(
            f"Обработка завершена за {elapsed_time:.2f} сек: "
            f"Обработано {processed_sources}/{total_sources} источников, "
            f"Найдено {total_found} статей, "
            f"Добавлено {total_added}, "
            f"Пропущено {total_skipped}, "
            f"Ошибок {error_count}"
        )
        
    except Exception as e:
        logger.exception(f"Ошибка при выполнении обновления: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 