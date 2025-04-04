#!/usr/bin/env python
# update_content.py
"""
Скрипт для обновления контента существующих статей с загрузкой полного текста
"""
import os
import sys
import argparse
from dotenv import load_dotenv
import time
from loguru import logger
from newspaper import Article

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем модули проекта
from src.utils.logger import setup_logger
from src.db import SupabaseClient
from newspaper import Article

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Обновление контента существующих статей')
    parser.add_argument('--limit', type=int, default=10, 
                        help='Максимальное количество статей для обновления (по умолчанию: 10)')
    parser.add_argument('--min-length', type=int, default=500,
                        help='Минимальная длина контента, ниже которой статьи будут обновлены (по умолчанию: 500)')
    parser.add_argument('--source-id', type=str,
                        help='ID конкретного источника для обновления')
    parser.add_argument('--dry-run', action='store_true',
                        help='Запуск без фактического сохранения в базу данных')
    parser.add_argument('--log-level', type=str, default='INFO', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Уровень логирования (по умолчанию: INFO)')
    
    return parser.parse_args()

def fetch_full_content(url):
    """
    Загрузка полного контента статьи по URL с использованием newspaper3k
    
    Args:
        url: URL статьи
        
    Returns:
        str: Полный текст статьи
    """
    try:
        article = Article(url)
        article.download()
        article.parse()
        
        if article.text:
            logger.debug(f"Получен полный контент для статьи {url} ({len(article.text)} символов)")
            return article.text
        else:
            logger.warning(f"Не удалось извлечь текст из статьи {url}")
            return ""
                
    except Exception as e:
        logger.error(f"Ошибка при загрузке полного контента статьи {url}: {e}")
        return ""

def update_article_content(db_client, article, dry_run=False):
    """
    Обновление контента статьи с загрузкой полного текста
    
    Args:
        db_client: Клиент базы данных
        article: Данные статьи
        dry_run: Запуск без фактического сохранения
        
    Returns:
        tuple: (успех, новая длина контента)
    """
    url = article.get('url')
    if not url:
        logger.error(f"Статья без URL: {article.get('title', 'Без заголовка')}")
        return False, 0
    
    try:
        # Загружаем полный контент статьи
        full_content = fetch_full_content(url)
        
        if not full_content:
            logger.warning(f"Не удалось загрузить контент для {url}")
            return False, 0
            
        # Обновляем статью в базе данных
        if not dry_run:
            result = db_client.client.table('content_items').update(
                {"content": full_content}
            ).eq('id', article['id']).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"Ошибка обновления статьи: {result.error}")
                return False, 0
        
        logger.info(f"Статья обновлена: {article.get('title', 'Без заголовка')}, новая длина: {len(full_content)}")
        return True, len(full_content)
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении контента статьи {url}: {e}")
        return False, 0

def main():
    """Основная функция для обновления контента статей"""
    args = parse_args()
    
    # Загружаем переменные окружения из .env файла
    load_dotenv()
    
    # Настраиваем логгирование
    setup_logger(log_level=args.log_level)
    
    logger.info(f"Обновление контента статей: лимит={args.limit}, мин. длина={args.min_length}")
    
    if args.dry_run:
        logger.info("Режим проверки: изменения НЕ будут сохранены в базу данных")
    
    try:
        # Инициализируем клиент Supabase
        db_client = SupabaseClient()
        
        # Формируем запрос для получения статей с коротким контентом
        query = db_client.client.table('content_items').select('*')
        
        # Если указан source_id, фильтруем по нему
        if args.source_id:
            response = db_client.client.table('sources').select('name').eq('id', args.source_id).execute()
            if response.data:
                source_name = response.data[0].get('name', 'Неизвестный источник')
                logger.info(f"Обновление статей источника: {source_name} (ID: {args.source_id})")
                query = query.eq('source', source_name)
            else:
                logger.error(f"Источник с ID {args.source_id} не найден")
                return 1
        
        # Получаем статьи с ограничением по количеству
        # Сортируем по длине контента (чтобы обновить сначала самые короткие)
        query = query.order('created_at', desc=True).limit(100)  # Получаем больше, чтобы потом отфильтровать
        response = query.execute()
        
        if not response.data:
            logger.warning("Не найдено статей для обновления")
            return 0
            
        # Отбираем статьи с коротким контентом
        articles = response.data
        filtered_articles = []
        
        for article in articles:
            content = article.get('content', '')
            if len(content) < args.min_length:
                filtered_articles.append(article)
                
                if len(filtered_articles) >= args.limit:
                    break
        
        if not filtered_articles:
            logger.info(f"Не найдено статей с контентом короче {args.min_length} символов")
            return 0
            
        logger.info(f"Найдено {len(filtered_articles)} статей для обновления")
        
        # Обновляем каждую статью
        success_count = 0
        total_old_length = 0
        total_new_length = 0
        
        for article in filtered_articles:
            content = article.get('content', '')
            title = article.get('title', 'Без заголовка')
            old_length = len(content)
            total_old_length += old_length
            
            logger.info(f"Обновление статьи: {title} (длина контента: {old_length} символов)")
            
            success, new_length = update_article_content(db_client, article, args.dry_run)
            
            if success:
                success_count += 1
                total_new_length += new_length
                
                if success_count < len(filtered_articles):
                    # Пауза для снижения нагрузки
                    time.sleep(1.0)
        
        # Выводим итоговую статистику
        logger.success(
            f"Обновление завершено: {success_count}/{len(filtered_articles)} статей\n"
            f"Средняя длина до: {total_old_length / len(filtered_articles):.2f} символов\n"
            f"Средняя длина после: {total_new_length / len(filtered_articles):.2f} символов\n"
            f"Увеличение: {(total_new_length - total_old_length) / len(filtered_articles):.2f} символов на статью"
        )
        
    except Exception as e:
        logger.exception(f"Ошибка при обновлении контента статей: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 