# src/parsers/rss_parser.py
import feedparser
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from .base_parser import BaseParser
import time
from newspaper import Article
import requests

logger = logging.getLogger(__name__)

class RssParser(BaseParser):
    """Парсер для источников с RSS-лентой"""
    
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.rss_url = source_config.get('rss_url')
        # По умолчанию всегда загружаем полный контент
        self.fetch_full_content = True
        
        if not self.rss_url:
            raise ValueError(f"Отсутствует RSS URL для источника {self.source_name}")
    
    def fetch_articles(self) -> List[Dict[str, Any]]:
        """
        Получение статей из RSS-ленты
        
        Returns:
            List[Dict[str, Any]]: Список статей
        """
        logger.info(f"Загрузка статей из RSS: {self.rss_url}")
        
        try:
            feed = feedparser.parse(self.rss_url)
            
            if feed.bozo and feed.bozo_exception:
                logger.error(f"Ошибка парсинга RSS {self.rss_url}: {feed.bozo_exception}")
            
            articles = []
            
            for entry in feed.entries:
                try:
                    article = self._parse_entry(entry)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"Ошибка обработки записи из {self.source_name}: {e}")
                    continue
            
            logger.info(f"Загружено {len(articles)} статей из {self.source_name}")
            return articles
        
        except Exception as e:
            logger.error(f"Ошибка загрузки RSS {self.rss_url}: {e}")
            return []
    
    def _fetch_full_content(self, url: str) -> str:
        """
        Загрузка полного контента статьи по URL
        
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
            
    def _parse_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Парсинг отдельной записи из RSS
        
        Args:
            entry: Запись из RSS-ленты
            
        Returns:
            Dict[str, Any]: Данные статьи
        """
        # Обязательные поля
        url = entry.get('link')
        if not url:
            logger.warning(f"Пропуск записи без URL в {self.source_name}")
            return None
        
        title = entry.get('title')
        if not title:
            logger.warning(f"Пропуск записи без заголовка: {url}")
            return None
        
        # Обработка даты публикации
        published_at = None
        if hasattr(entry, 'published'):
            published_at = self.normalize_date(entry.published)
        elif hasattr(entry, 'updated'):
            published_at = self.normalize_date(entry.updated)
        
        # Определение автора
        author = None
        if hasattr(entry, 'author'):
            author = entry.author
        elif hasattr(entry, 'author_detail') and hasattr(entry.author_detail, 'name'):
            author = entry.author_detail.name
        
        # Содержимое и описание
        content = ""
        if hasattr(entry, 'content'):
            # Некоторые RSS содержат полный контент
            content = entry.content[0].value if entry.content else ""
        
        description = ""
        if hasattr(entry, 'summary'):
            description = entry.summary
        
        # Если контент пустой, используем описание как контент
        if not content and description:
            content = description
            
        # Если указано, загружаем полный контент статьи
        if self.fetch_full_content:
            full_content = self._fetch_full_content(url)
            if full_content:
                content = full_content
            # Пауза для снижения нагрузки на сервер
            time.sleep(0.5)
        
        return {
            'title': self.clean_text(title),
            'url': url,
            'published_at': published_at,
            'source': self.source_name,
            'author': author,
            'description': self.clean_text(description),
            'content': content,
            'language': 'en',  # По умолчанию английский
            'is_translated': False,
            'is_published': False,
            'created_at': datetime.now()
        } 