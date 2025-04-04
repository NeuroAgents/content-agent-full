# import_sources.py
import os
import sys
import csv
import json
import pandas as pd
from dotenv import load_dotenv
from loguru import logger
import time
import argparse
from typing import Dict, List, Any, Optional

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули проекта
from src.utils.logger import setup_logger, add_logging_args
from src.db import SupabaseClient

# Обязательные поля для источников
REQUIRED_FIELDS = ["name", "url", "parser_type"]

# Правильные значения для parser_type
VALID_PARSER_TYPES = ["rss", "html"]

def validate_source(source: Dict[str, Any]) -> List[str]:
    """
    Валидация источника
    
    Args:
        source: Данные источника
    
    Returns:
        List[str]: Список ошибок (пустой, если ошибок нет)
    """
    errors = []
    
    # Проверяем обязательные поля
    for field in REQUIRED_FIELDS:
        if field not in source or not source[field]:
            errors.append(f"Отсутствует обязательное поле: {field}")
    
    # Проверяем тип парсера
    if "parser_type" in source:
        parser_type = source["parser_type"].lower()
        if parser_type not in VALID_PARSER_TYPES:
            errors.append(f"Некорректный тип парсера: {parser_type}. Допустимые значения: {', '.join(VALID_PARSER_TYPES)}")
        
        # Если парсер RSS, проверяем наличие RSS URL
        if parser_type == "rss" and ("rss_url" not in source or not source["rss_url"]):
            errors.append("Для RSS парсера необходимо указать поле rss_url")
        
        # Если парсер HTML, проверяем наличие селекторов
        if parser_type == "html" and ("selectors" not in source or not source["selectors"]):
            errors.append("Для HTML парсера необходимо указать JSON-объект selectors с CSS селекторами")
    
    return errors

def prepare_source(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Подготовка источника для сохранения в базе данных
    
    Args:
        source: Данные источника
    
    Returns:
        Dict[str, Any]: Подготовленный источник
    """
    prepared = source.copy()
    
    # Нормализуем тип парсера
    if "parser_type" in prepared:
        prepared["parser_type"] = prepared["parser_type"].lower()
    
    # Преобразуем строку с селекторами в JSON объект, если это строка
    if "selectors" in prepared and isinstance(prepared["selectors"], str):
        try:
            prepared["selectors"] = json.loads(prepared["selectors"])
        except json.JSONDecodeError:
            logger.warning(f"Не удалось преобразовать селекторы в JSON для {prepared.get('name')}: {prepared['selectors']}")
            # Сброс селекторов, если они невалидные
            prepared["selectors"] = {}
    
    # Активен по умолчанию
    if "active" not in prepared:
        prepared["active"] = True
    elif isinstance(prepared["active"], str):
        # Преобразуем строковое значение в булево
        prepared["active"] = prepared["active"].lower() in ["true", "1", "yes", "y", "да"]
    
    return prepared

def read_csv_sources(file_path: str) -> List[Dict[str, Any]]:
    """
    Чтение источников из CSV-файла
    
    Args:
        file_path: Путь к CSV-файлу
    
    Returns:
        List[Dict[str, Any]]: Список источников
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл не найден: {file_path}")
    
    sources = []
    
    # Определяем расширение файла
    _, ext = os.path.splitext(file_path)
    
    # Если это Excel файл
    if ext.lower() in ['.xlsx', '.xls']:
        try:
            df = pd.read_excel(file_path)
            # Преобразуем DataFrame в список словарей
            raw_sources = df.to_dict(orient='records')
        except Exception as e:
            logger.error(f"Ошибка чтения Excel файла: {e}")
            return []
    # Иначе считаем, что это CSV
    else:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                raw_sources = list(reader)
        except Exception as e:
            logger.error(f"Ошибка чтения CSV файла: {e}")
            return []
    
    # Обрабатываем каждый источник
    for source in raw_sources:
        # Удаляем пустые строки и пробелы
        cleaned_source = {k: v.strip() if isinstance(v, str) else v for k, v in source.items() if v is not None}
        sources.append(cleaned_source)
    
    return sources

def import_sources(file_path: str, dry_run: bool = False, update_existing: bool = True) -> Dict[str, int]:
    """
    Импорт источников из CSV-файла
    
    Args:
        file_path: Путь к CSV-файлу
        dry_run: Режим проверки без записи в базу данных
        update_existing: Обновлять существующие источники
    
    Returns:
        Dict[str, int]: Статистика импорта
    """
    # Статистика импорта
    stats = {
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "added": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0
    }
    
    # Читаем источники из CSV
    try:
        sources = read_csv_sources(file_path)
        stats["total"] = len(sources)
        logger.info(f"Прочитано {len(sources)} источников из файла {file_path}")
    except Exception as e:
        logger.error(f"Ошибка чтения файла: {e}")
        return stats
    
    # Валидируем и подготавливаем источники
    valid_sources = []
    for source in sources:
        errors = validate_source(source)
        
        if errors:
            stats["invalid"] += 1
            logger.warning(f"Невалидный источник {source.get('name', '')}: {', '.join(errors)}")
            continue
        
        prepared_source = prepare_source(source)
        valid_sources.append(prepared_source)
        stats["valid"] += 1
    
    logger.info(f"Валидных источников: {stats['valid']}, невалидных: {stats['invalid']}")
    
    # Если режим проверки, не сохраняем источники
    if dry_run:
        logger.info("Dry run: источники не будут сохранены в базе данных")
        return stats
    
    # Инициализируем клиент Supabase
    try:
        db_client = SupabaseClient()
        client = db_client.client
    except Exception as e:
        logger.error(f"Ошибка подключения к Supabase: {e}")
        stats["errors"] += 1
        return stats
    
    # Сохраняем источники
    for source in valid_sources:
        try:
            # Проверяем, существует ли источник с таким именем
            check = client.table('sources').select('id, name').eq('name', source['name']).execute()
            
            if check.data:
                # Если источник существует, обновляем его (если включено update_existing)
                if update_existing:
                    source_id = check.data[0]['id']
                    logger.info(f"Обновление источника: {source['name']}")
                    
                    client.table('sources').update(source).eq('id', source_id).execute()
                    stats["updated"] += 1
                else:
                    logger.info(f"Пропуск существующего источника: {source['name']}")
                    stats["skipped"] += 1
            else:
                # Иначе добавляем новый
                logger.info(f"Добавление нового источника: {source['name']}")
                
                client.table('sources').insert(source).execute()
                stats["added"] += 1
                
            # Пауза между запросами
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении источника {source.get('name', '')}: {e}")
            stats["errors"] += 1
            stats["skipped"] += 1
    
    return stats

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description='Импорт источников из CSV/Excel в базу данных Supabase',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        'file', 
        help='Путь к CSV/Excel файлу с источниками'
    )
    
    parser.add_argument(
        '--dry-run', 
        action='store_true', 
        help='Режим проверки без записи в базу данных'
    )
    
    parser.add_argument(
        '--no-update', 
        action='store_true', 
        help='Не обновлять существующие источники'
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
    logger.info("Запуск скрипта импорта источников из CSV")
    
    try:
        # Импортируем источники
        stats = import_sources(args.file, args.dry_run, not args.no_update)
        
        # Выводим статистику
        logger.success(f"Импорт завершен: "
                      f"Всего источников: {stats['total']}, "
                      f"Валидных: {stats['valid']}, "
                      f"Невалидных: {stats['invalid']}, "
                      f"Добавлено: {stats['added']}, "
                      f"Обновлено: {stats['updated']}, "
                      f"Пропущено: {stats['skipped']}, "
                      f"Ошибок: {stats['errors']}")
        
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 