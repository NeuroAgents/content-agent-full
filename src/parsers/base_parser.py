# src/parsers/base_parser.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """Базовый класс для всех парсеров статей"""
    
    def __init__(self, source_config: Dict[str, Any]):
        """
        Инициализация парсера
        
        Args:
            source_config: Конфигурация источника из базы данных
        """
        self.source_config = source_config
        self.source_name = source_config.get('name')
        self.source_url = source_config.get('url')
    
    @abstractmethod
    def fetch_articles(self) -> List[Dict[str, Any]]:
        """
        Получение статей из источника
        
        Returns:
            List[Dict[str, Any]]: Список статей
        """
        pass
    
    def normalize_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Нормализация строки даты в объект datetime
        
        Args:
            date_str: Строка с датой
            
        Returns:
            datetime: Объект datetime или None
        """
        if not date_str:
            return None
        
        try:
            # Попытка разобрать различные форматы дат
            from dateutil import parser
            return parser.parse(date_str)
        except Exception as e:
            logger.warning(f"Ошибка парсинга даты '{date_str}': {e}")
            return None
    
    def clean_text(self, text: Optional[str]) -> Optional[str]:
        """
        Очистка текста от лишних пробелов и переносов строк
        
        Args:
            text: Исходный текст
            
        Returns:
            str: Очищенный текст
        """
        if not text:
            return None
            
        return ' '.join(text.split()) 