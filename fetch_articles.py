# fetch_articles.py
import os
import sys
import argparse
from dotenv import load_dotenv
from loguru import logger
from typing import Dict, List, Any
import time

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули проекта
from src.utils.logger import setup_logger, add_logging_args
from src.db import SupabaseClient
from src.parsers import RssParser, HtmlParser

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description='Скрипт для загрузки статей из различных источников',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--source-id', 
        help='ID конкретного источника для обработки (по умолчанию обрабатываются все активные источники)'
    )
    
    parser.add_argument(
        '--limit', 
        type=int, 
        default=0,
        help='Ограничение количества статей для загрузки из каждого источника (0 - без ограничений)'
    )
    
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Режим проверки без сохранения в базу данных'
    )
    
    parser.add_argument(
        '--no-delay', 
        action='store_true', 
        help='Отключить паузу между запросами к разным источникам'
    )
    
    # Добавляем аргументы для логирования
    parser = add_logging_args(parser)
    
    return parser.parse_args()

def main():
    """Основная функция скрипта"""
    # Парсим аргументы командной строки
    args = parse_args()
    
    # Загружаем переменные окружения из .env файла
    load_dotenv()
    
    # Настраиваем логгирование
    setup_logger(args.log_level, args.log_file)
    logger.info("Запуск скрипта загрузки статей")
    
    if args.dry_run:
        logger.info("Режим dry-run: статьи не будут сохраняться в базу данных")
    
    try:
        # Инициализируем клиент Supabase
        db_client = SupabaseClient()
        
        # Получаем активные источники
        if args.source_id:
            # Если указан ID источника, получаем только его
            response = db_client.client.table('sources').select('*').eq('id', args.source_id).execute()
            sources = response.data
            logger.info(f"Загружен источник с ID: {args.source_id}")
        else:
            # Иначе получаем все активные источники
            sources = db_client.get_active_sources()
            logger.info(f"Загружено {len(sources)} активных источников")
        
        if not sources:
            logger.warning("Активные источники не найдены")
            return
        
        # Статистика по загрузке
        total_stats = {
            "total_sources": len(sources),
            "processed_sources": 0,
            "total_articles": 0,
            "added_articles": 0,
            "skipped_articles": 0,
            "errors": 0
        }
        
        # Обрабатываем каждый источник
        for source in sources:
            source_id = source.get('id')
            source_name = source.get('name', 'Неизвестный источник')
            logger.info(f"Обработка источника: {source_name}")
            
            try:
                # Создаем соответствующий парсер
                parser_type = source.get('parser_type', '').lower()
                
                if parser_type == 'rss':
                    parser = RssParser(source)
                elif parser_type == 'html':
                    parser = HtmlParser(source)
                else:
                    logger.error(f"Неизвестный тип парсера: {parser_type} для источника {source_name}")
                    total_stats["errors"] += 1
                    continue
                
                # Получаем статьи
                start_time = time.time()
                articles = parser.fetch_articles()
                end_time = time.time()
                
                # Ограничиваем количество статей, если указан лимит
                if args.limit > 0 and len(articles) > args.limit:
                    logger.info(f"Применяем лимит в {args.limit} статей (всего найдено: {len(articles)})")
                    articles = articles[:args.limit]
                
                logger.info(f"Получено {len(articles)} статей из {source_name} за {end_time - start_time:.2f} сек")
                
                # Сохраняем статьи в базу данных, если не включен режим dry-run
                if articles and not args.dry_run:
                    stats = db_client.save_articles(articles)
                    
                    logger.info(f"Результат сохранения для {source_name}: добавлено {stats['added']}, пропущено {stats['skipped']}")
                    
                    # Обновляем общую статистику
                    total_stats["total_articles"] += len(articles)
                    total_stats["added_articles"] += stats["added"]
                    total_stats["skipped_articles"] += stats["skipped"]
                    
                    # Обновляем время последней загрузки для источника
                    if source_id:
                        db_client.update_source_last_fetch(source_id)
                elif articles and args.dry_run:
                    # В режиме dry-run просто обновляем статистику
                    total_stats["total_articles"] += len(articles)
                    logger.info(f"Dry-run: {len(articles)} статей могли бы быть сохранены")
                
                total_stats["processed_sources"] += 1
                
            except Exception as e:
                logger.exception(f"Ошибка при обработке источника {source_name}: {e}")
                total_stats["errors"] += 1
                continue
            
            # Пауза между запросами к разным источникам, если не отключена
            if not args.no_delay and not source == sources[-1]:
                delay = 1.0  # секунд
                logger.debug(f"Пауза {delay} сек перед следующим источником")
                time.sleep(delay)
        
        # Выводим итоговую статистику
        logger.success(f"Обработка завершена: "
                      f"Обработано {total_stats['processed_sources']}/{total_stats['total_sources']} источников, "
                      f"Найдено {total_stats['total_articles']} статей, "
                      f"Добавлено {total_stats['added_articles']}, "
                      f"Пропущено {total_stats['skipped_articles']}, "
                      f"Ошибок {total_stats['errors']}")
        
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 