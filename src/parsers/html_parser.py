# src/parsers/html_parser.py
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from .base_parser import BaseParser

logger = logging.getLogger(__name__)

class HtmlParser(BaseParser):
    """Парсер для источников с HTML-страницами"""
    
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        
        # Получаем селекторы из конфигурации
        self.selectors = source_config.get('selectors', {})
        
        if not self.selectors:
            raise ValueError(f"Отсутствуют HTML селекторы для источника {self.source_name}")
            
        # Проверяем обязательные селекторы
        required_selectors = ['list_item', 'url', 'title']
        for selector in required_selectors:
            if selector not in self.selectors:
                raise ValueError(f"Отсутствует обязательный селектор '{selector}' для {self.source_name}")
    
    def fetch_articles(self) -> List[Dict[str, Any]]:
        """
        Получение статей из HTML-страницы
        
        Returns:
            List[Dict[str, Any]]: Список статей
        """
        logger.info(f"Загрузка статей с HTML: {self.source_url}")
        
        try:
            # Загружаем HTML-страницу
            response = requests.get(self.source_url, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            
            # Парсим содержимое
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Находим все элементы списка статей
            list_selector = self.selectors.get('list_item')
            items = soup.select(list_selector)
            
            logger.info(f"Найдено {len(items)} элементов на странице {self.source_url}")
            
            articles = []
            
            for item in items:
                try:
                    article = self._parse_item(item)
                    if article:
                        # Загружаем полное содержимое статьи, если есть селектор контента
                        if 'content' in self.selectors and article['url']:
                            self._fetch_article_content(article)
                        
                        articles.append(article)
                except Exception as e:
                    logger.error(f"Ошибка обработки элемента из {self.source_name}: {e}")
                    continue
            
            logger.info(f"Загружено {len(articles)} статей из {self.source_name}")
            return articles
            
        except Exception as e:
            logger.error(f"Ошибка загрузки HTML {self.source_url}: {e}")
            return []
    
    def _parse_item(self, item: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Парсинг отдельного элемента списка статей
        
        Args:
            item: Элемент BeautifulSoup
            
        Returns:
            Dict[str, Any]: Данные статьи
        """
        # Извлекаем URL
        url = None
        url_selector = self.selectors.get('url')
        if url_selector:
            url_element = item.select_one(url_selector)
            if url_element and url_element.has_attr('href'):
                url = url_element['href']
                # Если URL относительный, добавляем базовый URL
                if url.startswith('/'):
                    from urllib.parse import urljoin
                    url = urljoin(self.source_url, url)
        
        if not url:
            logger.warning(f"Пропуск элемента без URL в {self.source_name}")
            return None
        
        # Извлекаем заголовок
        title = None
        title_selector = self.selectors.get('title')
        if title_selector:
            title_element = item.select_one(title_selector)
            if title_element:
                title = title_element.get_text(strip=True)
        
        if not title:
            logger.warning(f"Пропуск элемента без заголовка: {url}")
            return None
        
        # Извлекаем описание (если есть селектор)
        description = None
        description_selector = self.selectors.get('description')
        if description_selector:
            desc_element = item.select_one(description_selector)
            if desc_element:
                description = desc_element.get_text(strip=True)
        
        # Извлекаем дату публикации (если есть селектор)
        published_at = None
        date_selector = self.selectors.get('date')
        if date_selector:
            date_element = item.select_one(date_selector)
            if date_element:
                date_str = date_element.get_text(strip=True)
                if date_str:
                    published_at = self.normalize_date(date_str)
        
        # Извлекаем автора (если есть селектор)
        author = None
        author_selector = self.selectors.get('author')
        if author_selector:
            author_element = item.select_one(author_selector)
            if author_element:
                author = author_element.get_text(strip=True)
        
        return {
            'title': self.clean_text(title),
            'url': url,
            'published_at': published_at,
            'source': self.source_name,
            'author': author,
            'description': self.clean_text(description),
            'content': '',  # Контент загрузим отдельно
            'language': 'en',  # По умолчанию английский
            'is_translated': False,
            'is_published': False,
            'created_at': datetime.now()
        }
    
    def _fetch_article_content(self, article: Dict[str, Any]) -> None:
        """
        Загрузка полного содержимого статьи
        
        Args:
            article: Данные статьи
        """
        content_selector = self.selectors.get('content')
        if not content_selector:
            return
            
        try:
            # Загружаем страницу статьи
            response = requests.get(article['url'], headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            
            # Парсим содержимое
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Извлекаем контент
            content_element = soup.select_one(content_selector)
            if content_element:
                # Сохраняем HTML-контент
                article['content'] = str(content_element)
                
                # Если в конфигурации есть селектор краткого описания и оно еще не заполнено
                meta_desc_selector = self.selectors.get('meta_description')
                if meta_desc_selector and not article['description']:
                    meta_desc = soup.select_one(meta_desc_selector)
                    if meta_desc:
                        article['description'] = self.clean_text(meta_desc.get_text(strip=True))
        
        except Exception as e:
            logger.error(f"Ошибка загрузки контента статьи {article['url']}: {e}")
            # Если не удалось загрузить контент, оставляем пустую строку 