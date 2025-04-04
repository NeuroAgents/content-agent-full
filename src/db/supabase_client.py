from supabase import create_client, Client
from typing import Dict, List, Any, Optional
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Клиент для работы с Supabase"""
    
    def __init__(self, url: str = None, key: str = None):
        """
        Инициализация клиента Supabase
        
        Args:
            url: URL проекта Supabase
            key: Ключ доступа к API Supabase
        """
        self.url = url or os.environ.get('SUPABASE_URL')
        self.key = key or os.environ.get('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("Необходимо указать SUPABASE_URL и SUPABASE_KEY")
            
        self.client: Client = create_client(self.url, self.key)
        logger.info("Supabase клиент инициализирован")
    
    def get_active_sources(self) -> List[Dict[str, Any]]:
        """
        Получение всех активных источников
        
        Returns:
            List[Dict[str, Any]]: Список активных источников
        """
        try:
            response = self.client.table('sources').select('*').eq('active', True).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Ошибка получения источников: {response.error}")
                return []
            
            return response.data
        
        except Exception as e:
            logger.error(f"Ошибка при получении активных источников: {e}")
            return []
    
    def save_articles(self, articles: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Сохранение статей в базу данных
        
        Args:
            articles: Список статей для сохранения
            
        Returns:
            Dict[str, int]: Статистика сохранения (добавлено, пропущено)
        """
        if not articles:
            return {"added": 0, "skipped": 0}
        
        stats = {"added": 0, "skipped": 0}
        
        # Преобразуем datetime объекты в строки ISO для JSON
        prepared_articles = []
        for article in articles:
            article_copy = article.copy()
            
            # Преобразуем даты в строки ISO
            if article_copy.get('published_at') and isinstance(article_copy['published_at'], datetime):
                article_copy['published_at'] = article_copy['published_at'].isoformat()
                
            if article_copy.get('created_at') and isinstance(article_copy['created_at'], datetime):
                article_copy['created_at'] = article_copy['created_at'].isoformat()
                
            prepared_articles.append(article_copy)
        
        # Сохраняем каждую статью, игнорируя дубликаты по URL
        for article in prepared_articles:
            try:
                # Проверяем, существует ли статья с таким URL
                check_response = self.client.table('content_items').select('id').eq('url', article['url']).execute()
                
                if hasattr(check_response, 'error') and check_response.error:
                    logger.error(f"Ошибка проверки дубликата: {check_response.error}")
                    stats["skipped"] += 1
                    continue
                
                # Если статья уже существует, пропускаем
                if check_response.data:
                    logger.debug(f"Статья уже существует: {article['url']}")
                    stats["skipped"] += 1
                    continue
                
                # Добавляем новую статью
                insert_response = self.client.table('content_items').insert(article).execute()
                
                if hasattr(insert_response, 'error') and insert_response.error:
                    logger.error(f"Ошибка сохранения статьи: {insert_response.error}")
                    stats["skipped"] += 1
                else:
                    logger.debug(f"Статья сохранена: {article['title']}")
                    stats["added"] += 1
                    
            except Exception as e:
                logger.error(f"Ошибка при сохранении статьи {article.get('url', '')}: {e}")
                stats["skipped"] += 1
        
        return stats
    
    def update_source_last_fetch(self, source_id: str) -> bool:
        """
        Обновление времени последней загрузки для источника
        
        Args:
            source_id: ID источника
            
        Returns:
            bool: Успешность операции
        """
        try:
            self.client.table('sources').update(
                {"last_fetch_at": datetime.now().isoformat()}
            ).eq('id', source_id).execute()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления last_fetch_at для источника {source_id}: {e}")
            return False
    
    def get_content_item_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Получение статьи по URL
        
        Args:
            url: URL статьи
            
        Returns:
            Dict[str, Any]: Данные статьи или None
        """
        try:
            response = self.client.table('content_items').select('*').eq('url', url).execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Ошибка получения статьи: {response.error}")
                return None
            
            if not response.data:
                return None
                
            return response.data[0]
        except Exception as e:
            logger.error(f"Ошибка при получении статьи по URL {url}: {e}")
            return None
    
    def get_content_items(self, 
                          limit: int = 100, 
                          offset: int = 0, 
                          is_translated: bool = None, 
                          is_published: bool = None,
                          language: str = None,
                          source: str = None) -> List[Dict[str, Any]]:
        """
        Получение списка статей с фильтрацией
        
        Args:
            limit: Лимит выборки
            offset: Смещение выборки
            is_translated: Фильтр по переводу
            is_published: Фильтр по публикации
            language: Фильтр по языку
            source: Фильтр по источнику
            
        Returns:
            List[Dict[str, Any]]: Список статей
        """
        try:
            query = self.client.table('content_items').select('*').order('published_at', desc=True)
            
            # Применяем фильтры
            if is_translated is not None:
                query = query.eq('is_translated', is_translated)
                
            if is_published is not None:
                query = query.eq('is_published', is_published)
            
            if language:
                query = query.eq('language', language)
                
            if source:
                query = query.eq('source', source)
            
            # Применяем пагинацию
            query = query.range(offset, offset + limit - 1)
            
            response = query.execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Ошибка получения списка статей: {response.error}")
                return []
            
            return response.data
        except Exception as e:
            logger.error(f"Ошибка при получении списка статей: {e}")
            return [] 