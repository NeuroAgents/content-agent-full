#!/usr/bin/env python
# import_all_sources.py
import os
import sys
import csv
import time
import feedparser
import requests
import concurrent.futures
from dotenv import load_dotenv
from loguru import logger
from urllib.parse import urlparse

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули проекта
from src.utils.logger import setup_logger
from src.db import SupabaseClient

# Путь к CSV файлу с источниками
CSV_FILE_PATH = "/Users/maks/Desktop/Content Agent/источники статей.csv"

def get_rss_url(site_url):
    """
    Пытается обнаружить RSS URL на основе основного URL сайта
    
    Args:
        site_url: Основной URL сайта
        
    Returns:
        str: Обнаруженный RSS URL или None
    """
    possible_rss_paths = [
        "/feed", "/feed/", "/rss", "/rss/", 
        "/feed.xml", "/rss.xml", "/atom.xml",
        "/index.xml", "/feeds/posts/default"
    ]
    
    # Для .com/blog и подобных адресов
    parsed_url = urlparse(site_url)
    domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    path = parsed_url.path
    
    # Проверяем, если URL оканчивается на / и удаляем, если нужно
    if site_url.endswith('/'):
        site_url = site_url[:-1]
        
    potential_urls = []
    
    # Проверяем URLs на уровне domain + RSS path
    for rss_path in possible_rss_paths:
        potential_urls.append(f"{domain}{rss_path}")
    
    # Проверяем URLs на уровне полного пути + RSS path
    for rss_path in possible_rss_paths:
        potential_urls.append(f"{site_url}{rss_path}")
    
    # Если путь содержит подпапки, проверяем RSS для них
    path_parts = path.strip('/').split('/')
    if len(path_parts) > 1:
        for i in range(1, len(path_parts)):
            partial_path = '/'.join(path_parts[:i])
            if partial_path:
                for rss_path in possible_rss_paths:
                    potential_urls.append(f"{domain}/{partial_path}{rss_path}")
    
    # Специальные случаи для известных сайтов
    if "techcrunch.com" in site_url:
        if "tag" in site_url or "category" in site_url:
            potential_urls.append(f"{site_url}/feed")
    
    elif "theverge.com" in site_url:
        if "/ai-artificial-intelligence" in site_url:
            potential_urls.append("https://www.theverge.com/rss/ai-artificial-intelligence/index.xml")
    
    elif "artificialintelligence-news.com" in site_url:
        potential_urls.append("https://www.artificialintelligence-news.com/feed/")
    
    elif "venturebeat.com" in site_url:
        if "category" in site_url:
            potential_urls.append(f"{site_url}/feed")
    
    # Удаляем дубликаты
    potential_urls = list(set(potential_urls))
    
    # Проверяем каждый потенциальный URL
    for rss_url in potential_urls:
        try:
            response = requests.head(rss_url, timeout=5)
            if 200 <= response.status_code < 300:
                content_type = response.headers.get('Content-Type', '').lower()
                if any(media_type in content_type for media_type in 
                      ['rss', 'xml', 'atom', 'feed', 'application/xml', 'text/xml']):
                    # Дополнительная проверка с feedparser
                    feed = feedparser.parse(rss_url)
                    if not (feed.bozo and feed.bozo_exception) and len(feed.entries) > 0:
                        return rss_url
        except Exception:
            continue
    
    return None

def check_source(source):
    """
    Проверяет источник и пытается найти RSS URL
    
    Args:
        source: Словарь с информацией об источнике
        
    Returns:
        dict: Словарь с обновленной информацией об источнике
    """
    try:
        name = source['name']
        url = source['url']
        logger.info(f"Проверка источника: {name}")
        
        # Пытаемся обнаружить RSS URL
        rss_url = get_rss_url(url)
        
        if rss_url:
            logger.success(f"Найден RSS URL для {name}: {rss_url}")
            source['rss_url'] = rss_url
            source['parser_type'] = 'rss'
            source['active'] = True
        else:
            logger.warning(f"RSS URL не найден для {name}")
            source['rss_url'] = None
            source['parser_type'] = 'html'  # Для будущей реализации HTML-парсера
            source['active'] = False  # Пока деактивируем источники без RSS
        
        return source
    except Exception as e:
        logger.error(f"Ошибка при проверке источника {source.get('name', 'Неизвестно')}: {e}")
        return source

def read_sources_from_csv(file_path):
    """
    Чтение источников из CSV файла
    
    Args:
        file_path: Путь к CSV файлу
        
    Returns:
        list: Список словарей с информацией об источниках
    """
    sources = []
    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Создаем словарь для каждого источника
                source = {
                    'name': row['Название'],
                    'description': row['Краткое описание'],
                    'url': row['Ссылка'],
                    'active': False  # По умолчанию источник неактивен, пока не найдем RSS
                }
                sources.append(source)
                
        logger.info(f"Загружено {len(sources)} источников из CSV")
        return sources
    except Exception as e:
        logger.error(f"Ошибка при чтении CSV файла: {e}")
        return []

def main():
    """Основная функция для импорта источников"""
    # Загружаем переменные окружения из .env файла
    load_dotenv()
    
    # Настраиваем логгирование
    setup_logger()
    logger.info("Запуск скрипта импорта всех источников")
    
    # Читаем источники из CSV
    sources = read_sources_from_csv(CSV_FILE_PATH)
    if not sources:
        logger.error("Не удалось загрузить источники из CSV")
        return 1
    
    # Проверяем источники и ищем RSS URLs
    logger.info("Проверка источников и поиск RSS URLs...")
    
    # Используем многопоточность для ускорения проверки
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        updated_sources = list(executor.map(check_source, sources))
    
    # Подсчитываем статистику
    total_sources = len(updated_sources)
    rss_found = sum(1 for source in updated_sources if source.get('rss_url'))
    logger.info(f"Всего источников: {total_sources}, Найдены RSS URLs: {rss_found}")
    
    # Если RSS URLs найдены, можем импортировать в базу данных
    if rss_found > 0:
        try:
            # Инициализируем клиент Supabase
            db_client = SupabaseClient()
            client = db_client.client
            
            # Получаем список существующих источников
            existing_response = client.table('sources').select('name').execute()
            existing_names = [source['name'] for source in existing_response.data]
            
            # Добавляем новые источники
            added_count = 0
            skipped_count = 0
            
            for source in updated_sources:
                if source['name'] in existing_names:
                    logger.info(f"Источник '{source['name']}' уже существует, пропускаем")
                    skipped_count += 1
                    continue
                
                if source.get('rss_url'):  # Добавляем только источники с RSS
                    try:
                        client.table('sources').insert({
                            'name': source['name'],
                            'url': source['url'],
                            'rss_url': source['rss_url'],
                            'parser_type': source['parser_type'],
                            'active': source['active']
                        }).execute()
                        
                        logger.success(f"Источник '{source['name']}' успешно добавлен")
                        added_count += 1
                        
                        # Пауза между запросами
                        time.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении источника '{source['name']}': {e}")
            
            logger.success(f"Импорт завершен. Добавлено: {added_count}, Пропущено: {skipped_count}")
            
        except Exception as e:
            logger.exception(f"Ошибка при импорте источников в базу данных: {e}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 