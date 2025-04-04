#!/usr/bin/env python
# content_processor_direct.py - Микросервис для обработки и перевода контента для существующей структуры таблицы

import os
import argparse
import logging
import time
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client as SupabaseClient

# Настройка логирования
def setup_logger() -> logging.Logger:
    """Инициализация и настройка логгера."""
    logger = logging.getLogger("content_processor")
    logger.setLevel(logging.INFO)
    
    # Создаем обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Задаем формат логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчик к логгеру
    logger.addHandler(console_handler)
    
    # Создаем обработчик для записи в файл, если указан LOG_FILE
    log_file = os.environ.get('LOG_FILE')
    if log_file:
        # Создаем директорию для логов, если она не существует
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Инициализация логгера
logger = setup_logger()

@dataclass
class ProcessingResult:
    """Класс для хранения результатов обработки контента."""
    clean_content: Optional[str] = None
    rewritten_content: Optional[str] = None
    translated_title: Optional[str] = None
    translated_description: Optional[str] = None
    translated_content: Optional[str] = None
    success: bool = False
    error_message: Optional[str] = None

def retry_with_exponential_backoff(max_retries=5, initial_delay=5, max_delay=60):
    """Декоратор для повторных попыток с экспоненциальной задержкой."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_message = str(e)
                    
                    # Если это ошибка превышения квоты
                    if "429" in error_message and "quota" in error_message:
                        retries += 1
                        
                        if retries > max_retries:
                            logger.error(f"Превышено максимальное количество попыток ({max_retries})")
                            raise
                        
                        # Добавляем случайность к задержке (jitter)
                        jitter = random.uniform(0.5, 1.5)
                        wait_time = min(delay * jitter, max_delay)
                        
                        logger.warning(f"Превышена квота API. Повторная попытка {retries}/{max_retries} через {wait_time:.1f} секунд...")
                        time.sleep(wait_time)
                        
                        # Увеличиваем задержку экспоненциально
                        delay *= 2
                    else:
                        # Если это другая ошибка, пробрасываем ее дальше
                        raise
            
            # Если мы дошли сюда, значит все попытки исчерпаны
            raise Exception(f"Превышено максимальное количество попыток ({max_retries})")
        
        return wrapper
    return decorator

class ContentProcessor:
    """Класс для обработки контента статей."""
    
    def __init__(self):
        # Загружаем переменные окружения из .env файла
        load_dotenv()
        
        # Инициализируем Supabase клиент
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL и SUPABASE_KEY должны быть установлены в .env файле")
        
        self.db_client = create_client(supabase_url, supabase_key)
        
        # Инициализируем Gemini API
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY должен быть установлен в .env файле")
        
        genai.configure(api_key=gemini_api_key)
        
        # Создаем генеративную модель (исправлено название модели)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Шаблоны промптов для переписывания и перевода текста
        self.rewrite_prompt_template = """
        Rewrite the following article in a professional, journalistic style,
        maintaining the technical accuracy and important information.
        Focus on clarity, professionalism, and engagement while keeping the original meaning intact.
        Format the content with HTML paragraphs using <p> tags for proper structure.
        
        Original article:
        {content}
        """
        
        self.translate_content_prompt_template = """
        Translate the following English article into Russian.
        Maintain the professional tone and ensure technical terms are translated appropriately.
        Preserve any HTML formatting present in the original text.
        
        English article:
        {content}
        """
        
        self.translate_title_prompt_template = """
        Translate the following English article title into Russian.
        Maintain the professional tone and ensure technical terms are translated appropriately.
        
        English title:
        {title}
        """
        
        self.translate_description_prompt_template = """
        Translate the following English article description into Russian.
        Maintain the professional tone and ensure technical terms are translated appropriately.
        
        English description:
        {description}
        """
    
    def get_unprocessed_articles(self, limit: int = 10, hours_ago: int = 24) -> List[Dict[str, Any]]:
        """Получаем недавно добавленные необработанные статьи из базы данных."""
        try:
            # Создаем фильтр для недавно добавленных статей
            time_threshold = datetime.now() - timedelta(hours=hours_ago)
            time_threshold_str = time_threshold.isoformat()
            
            # Выбираем статьи, которые не переведены и имеют контент
            response = self.db_client.table('content_items') \
                .select('*') \
                .eq('is_translated', False) \
                .not_.is_('content', 'null') \
                .gte('created_at', time_threshold_str) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            articles = response.data
            logger.info(f"Найдено {len(articles)} непереведенных статей за последние {hours_ago} часов")
            
            return articles
        except Exception as e:
            logger.error(f"Ошибка при получении необработанных статей: {e}")
            return []
    
    def clean_html(self, content: str) -> str:
        """Очистка HTML контента от ненужных элементов."""
        if not content:
            return ""
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Удаляем скрипты и стили
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Удаляем комментарии
            for comment in soup.find_all(string=lambda text: isinstance(text, (type(soup.Comment)))):
                comment.extract()
            
            # Получаем текст статьи
            clean_text = soup.get_text(separator='\n')
            
            # Форматируем текст
            lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
            clean_content = "\n".join(lines)
            
            return clean_content
        except Exception as e:
            logger.error(f"Ошибка при очистке HTML: {e}")
            return content
    
    @retry_with_exponential_backoff(max_retries=3, initial_delay=15, max_delay=120)
    def rewrite_content(self, content: str) -> Optional[str]:
        """Переписывание контента с помощью Gemini API."""
        if not content:
            return None
        
        try:
            prompt = self.rewrite_prompt_template.format(content=content)
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text
            return None
        except Exception as e:
            logger.error(f"Ошибка при переписывании контента: {e}")
            raise
    
    @retry_with_exponential_backoff(max_retries=3, initial_delay=15, max_delay=120)
    def translate_content(self, content: str) -> Optional[str]:
        """Перевод контента на русский язык с помощью Gemini API."""
        if not content:
            return None
        
        try:
            prompt = self.translate_content_prompt_template.format(content=content)
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text
            return None
        except Exception as e:
            logger.error(f"Ошибка при переводе контента: {e}")
            raise
    
    @retry_with_exponential_backoff(max_retries=3, initial_delay=10, max_delay=60)
    def translate_title(self, title: str) -> Optional[str]:
        """Перевод заголовка на русский язык с помощью Gemini API."""
        if not title:
            return None
        
        try:
            prompt = self.translate_title_prompt_template.format(title=title)
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text
            return None
        except Exception as e:
            logger.error(f"Ошибка при переводе заголовка: {e}")
            raise
    
    @retry_with_exponential_backoff(max_retries=3, initial_delay=10, max_delay=60)
    def translate_description(self, description: str) -> Optional[str]:
        """Перевод описания на русский язык с помощью Gemini API."""
        if not description:
            return None
        
        try:
            prompt = self.translate_description_prompt_template.format(description=description)
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text
            return None
        except Exception as e:
            logger.error(f"Ошибка при переводе описания: {e}")
            raise
    
    def update_article(self, article_id: str, result: ProcessingResult) -> bool:
        """Обновление статьи в базе данных с обработанным контентом."""
        try:
            # Создаем словарь для обновления
            update_data = {
                'updated_at': datetime.now().isoformat(),
                'is_translated': True
            }
            
            # Добавляем поля для обновления, только если они не None
            if result.clean_content:
                update_data['description'] = result.clean_content[:500]
                
            if result.translated_title:
                update_data['title_ru'] = result.translated_title
                
            if result.translated_description:
                update_data['description_ru'] = result.translated_description
                
            if result.translated_content:
                update_data['content_ru'] = result.translated_content
            
            # Обновляем запись в базе данных
            self.db_client.table('content_items') \
                .update(update_data) \
                .eq('id', article_id) \
                .execute()
            
            logger.info(f"Статья с ID {article_id} успешно обновлена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении статьи {article_id}: {e}")
            return False
    
    def process_article(self, article: Dict[str, Any]) -> ProcessingResult:
        """Полная обработка статьи: очистка, переписывание и перевод."""
        article_id = article.get('id')
        title = article.get('title', 'Без названия')
        content = article.get('content')
        description = article.get('description', '')
        
        logger.info(f"Обработка статьи: {title} (ID: {article_id})")
        
        if not content:
            return ProcessingResult(
                success=False, 
                error_message=f"Статья {article_id} не имеет контента"
            )
        
        try:
            # Шаг 1: Очистка HTML
            logger.info(f"Очистка HTML для статьи {article_id}")
            clean_content = self.clean_html(content)
            
            if not clean_content:
                return ProcessingResult(
                    success=False, 
                    error_message=f"Не удалось очистить HTML для статьи {article_id}"
                )
            
            # Шаг 2: Переписывание контента
            logger.info(f"Переписывание контента для статьи {article_id}")
            try:
                rewritten_content = self.rewrite_content(clean_content)
            except Exception as e:
                return ProcessingResult(
                    clean_content=clean_content,
                    success=False, 
                    error_message=f"Не удалось переписать контент для статьи {article_id}: {e}"
                )
            
            if not rewritten_content:
                return ProcessingResult(
                    clean_content=clean_content,
                    success=False, 
                    error_message=f"Не удалось переписать контент для статьи {article_id}"
                )
            
            # Шаг 3: Перевод заголовка
            logger.info(f"Перевод заголовка для статьи {article_id}")
            try:
                translated_title = self.translate_title(title)
            except Exception as e:
                logger.warning(f"Не удалось перевести заголовок для статьи {article_id}: {e}")
                translated_title = None
            
            # Шаг 4: Перевод описания, если оно есть
            translated_description = None
            if description:
                logger.info(f"Перевод описания для статьи {article_id}")
                try:
                    translated_description = self.translate_description(description)
                except Exception as e:
                    logger.warning(f"Не удалось перевести описание для статьи {article_id}: {e}")
            
            # Шаг 5: Перевод контента
            logger.info(f"Перевод контента для статьи {article_id}")
            try:
                translated_content = self.translate_content(rewritten_content)
            except Exception as e:
                return ProcessingResult(
                    clean_content=clean_content,
                    rewritten_content=rewritten_content,
                    translated_title=translated_title,
                    translated_description=translated_description,
                    success=False, 
                    error_message=f"Не удалось перевести контент для статьи {article_id}: {e}"
                )
            
            return ProcessingResult(
                clean_content=clean_content,
                rewritten_content=rewritten_content,
                translated_title=translated_title,
                translated_description=translated_description,
                translated_content=translated_content,
                success=bool(translated_content)
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке статьи {article_id}: {e}")
            return ProcessingResult(
                success=False, 
                error_message=f"Ошибка при обработке статьи {article_id}: {e}"
            )
    
    def check_translation_fields_exist(self) -> bool:
        """Проверка наличия необходимых полей в таблице content_items."""
        try:
            # Выполняем запрос, который попытается получить одну строку с полем title_ru
            query = "SELECT title_ru FROM content_items LIMIT 1"
            response = self.db_client.rpc('execute_sql', {'query': query})
            
            # Если запрос выполнен без ошибок, значит поле существует
            logger.info("Поля для переводов существуют в базе данных")
            return True
        except Exception as e:
            # Если возникла ошибка, значит поля может не быть
            logger.warning(f"Ошибка при проверке полей для переводов: {e}")
            logger.warning("Необходимо выполнить миграцию для добавления полей переводов")
            return False
    
    def run(self, limit: int = 5, hours_ago: int = 24, dry_run: bool = False) -> Tuple[int, int]:
        """Основной метод для обработки статей."""
        # Проверяем наличие необходимых полей в таблице
        fields_exist = self.check_translation_fields_exist()
        
        if not fields_exist and not dry_run:
            logger.error("Необходимые поля для переводов отсутствуют в базе данных. Пожалуйста, выполните миграцию.")
            return (0, 0)
        
        # Получаем необработанные статьи
        articles = self.get_unprocessed_articles(limit, hours_ago)
        
        if not articles:
            logger.info(f"Нет необработанных статей за последние {hours_ago} часов")
            return (0, 0)
        
        success_count = 0
        error_count = 0
        
        for article in articles:
            # Обрабатываем статью
            result = self.process_article(article)
            
            if not result.success:
                article_id = article.get('id')
                logger.error(f"Ошибка при обработке статьи {article_id}: {result.error_message}")
                error_count += 1
                continue
            
            # В режиме dry run не обновляем базу данных
            if not dry_run:
                if self.update_article(article.get('id'), result):
                    success_count += 1
                else:
                    error_count += 1
            else:
                article_id = article.get('id')
                logger.info(f"Режим dry run: статья {article_id} успешно обработана, но не обновлена в БД")
                logger.info(f"Переведенный заголовок: {result.translated_title}")
                logger.info(f"Переведенное описание: {result.translated_description[:100] if result.translated_description else 'Нет'}")
                logger.info(f"Переведенный контент (первые 100 символов): {result.translated_content[:100] if result.translated_content else 'Нет'}")
                success_count += 1
            
            # Небольшая задержка между запросами к API, чтобы избежать ограничений
            time.sleep(2)
        
        return (success_count, error_count)

def parse_args():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(description='Процессор контента для очистки, переписывания и перевода статей')
    parser.add_argument('--limit', type=int, default=5, help='Максимальное количество статей для обработки')
    parser.add_argument('--hours', type=int, default=24, help='Обрабатывать статьи, добавленные за последние N часов')
    parser.add_argument('--dry-run', action='store_true', help='Режим без внесения изменений в базу данных')
    return parser.parse_args()

def main():
    """Основная функция программы."""
    args = parse_args()
    
    logger.info("Запуск обработчика контента")
    logger.info(f"Ограничение: {args.limit} статей")
    logger.info(f"Временной интервал: последние {args.hours} часов")
    logger.info(f"Dry run: {args.dry_run}")
    
    try:
        processor = ContentProcessor()
        success_count, error_count = processor.run(args.limit, args.hours, args.dry_run)
        
        logger.info(f"Обработка завершена. Успешно: {success_count}, Ошибок: {error_count}")
    except Exception as e:
        logger.error(f"Ошибка при выполнении обработчика контента: {e}")

if __name__ == "__main__":
    main() 