#!/usr/bin/env python
# content_processor.py - Микросервис для обработки, переписывания и перевода контента

import os
import argparse
import logging
import time
from datetime import datetime
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
    
    return logger

# Инициализация логгера
logger = setup_logger()

@dataclass
class ProcessingResult:
    """Класс для хранения результатов обработки контента."""
    clean_content: Optional[str] = None
    rewritten_content: Optional[str] = None
    translated_content: Optional[str] = None
    success: bool = False
    error_message: Optional[str] = None

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
        
        # Создаем генеративную модель
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Шаблоны промптов для переписывания и перевода текста
        self.rewrite_prompt_template = """
        Rewrite the following article in a professional, journalistic style,
        maintaining the technical accuracy and important information.
        Focus on clarity, professionalism, and engagement while keeping the original meaning intact.
        Format the content with HTML paragraphs using <p> tags for proper structure.
        
        Original article:
        {content}
        """
        
        self.translate_prompt_template = """
        Translate the following English article into Russian.
        Maintain the professional tone and ensure technical terms are translated appropriately.
        Preserve any HTML formatting present in the original text.
        
        English article:
        {content}
        """
    
    def get_unprocessed_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получаем неопубликованные статьи из базы данных."""
        try:
            response = self.db_client.table('content_items') \
                .select('*') \
                .eq('is_cleaned', False) \
                .not_.is_('content', 'null') \
                .limit(limit) \
                .execute()
            
            articles = response.data
            logger.info(f"Найдено {len(articles)} необработанных статей")
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
            return None
    
    def translate_content(self, content: str) -> Optional[str]:
        """Перевод контента на русский язык с помощью Gemini API."""
        if not content:
            return None
        
        try:
            prompt = self.translate_prompt_template.format(content=content)
            response = self.model.generate_content(prompt)
            
            if response.text:
                return response.text
            return None
        except Exception as e:
            logger.error(f"Ошибка при переводе контента: {e}")
            return None
    
    def update_article(self, article_id: str, result: ProcessingResult) -> bool:
        """Обновление статьи в базе данных с обработанным контентом."""
        try:
            update_data = {
                'updated_at': datetime.now().isoformat(),
                'is_cleaned': True
            }
            
            if result.clean_content:
                update_data['clean_content'] = result.clean_content
            
            if result.rewritten_content:
                update_data['rewritten_content'] = result.rewritten_content
            
            if result.translated_content:
                update_data['translated_content'] = result.translated_content
                update_data['is_translated'] = True
            
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
        content = article.get('content')
        
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
            rewritten_content = self.rewrite_content(clean_content)
            
            if not rewritten_content:
                return ProcessingResult(
                    clean_content=clean_content,
                    success=False, 
                    error_message=f"Не удалось переписать контент для статьи {article_id}"
                )
            
            # Шаг 3: Перевод контента
            logger.info(f"Перевод контента для статьи {article_id}")
            translated_content = self.translate_content(rewritten_content)
            
            return ProcessingResult(
                clean_content=clean_content,
                rewritten_content=rewritten_content,
                translated_content=translated_content,
                success=bool(translated_content)
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке статьи {article_id}: {e}")
            return ProcessingResult(
                success=False, 
                error_message=f"Ошибка при обработке статьи {article_id}: {e}"
            )
    
    def run(self, limit: int = 5, dry_run: bool = False) -> Tuple[int, int]:
        """Основной метод для обработки статей."""
        # Получаем необработанные статьи
        articles = self.get_unprocessed_articles(limit)
        
        if not articles:
            logger.info("Нет необработанных статей для обработки")
            return (0, 0)
        
        success_count = 0
        error_count = 0
        
        for article in articles:
            article_id = article.get('id')
            title = article.get('title', 'Без названия')
            
            logger.info(f"Обработка статьи: {title} (ID: {article_id})")
            
            # Обрабатываем статью
            result = self.process_article(article)
            
            if not result.success:
                logger.error(f"Ошибка при обработке статьи {article_id}: {result.error_message}")
                error_count += 1
                continue
            
            # В режиме dry run не обновляем базу данных
            if not dry_run:
                if self.update_article(article_id, result):
                    success_count += 1
                else:
                    error_count += 1
            else:
                logger.info(f"Режим dry run: статья {article_id} успешно обработана, но не обновлена в БД")
                success_count += 1
            
            # Небольшая задержка между запросами к API, чтобы избежать ограничений
            time.sleep(2)
        
        return (success_count, error_count)

def parse_args():
    """Парсинг аргументов командной строки."""
    parser = argparse.ArgumentParser(description='Процессор контента для очистки, переписывания и перевода статей')
    parser.add_argument('--limit', type=int, default=5, help='Максимальное количество статей для обработки')
    parser.add_argument('--dry-run', action='store_true', help='Режим без внесения изменений в базу данных')
    return parser.parse_args()

def main():
    """Основная функция программы."""
    args = parse_args()
    
    logger.info("Запуск обработчика контента")
    logger.info(f"Ограничение: {args.limit} статей")
    logger.info(f"Dry run: {args.dry_run}")
    
    try:
        processor = ContentProcessor()
        success_count, error_count = processor.run(args.limit, args.dry_run)
        
        logger.info(f"Обработка завершена. Успешно: {success_count}, Ошибок: {error_count}")
    except Exception as e:
        logger.error(f"Ошибка при выполнении обработчика контента: {e}")

if __name__ == "__main__":
    main() 