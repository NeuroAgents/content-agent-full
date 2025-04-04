# src/parsers/__init__.py
from .rss_parser import RssParser
from .html_parser import HtmlParser

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def get_parser_for_source(source: Dict[str, Any]) -> Optional[RssParser]:
    """
    Создает и возвращает подходящий парсер для источника
    
    Args:
        source: Словарь с информацией об источнике
        
    Returns:
        BaseParser: Экземпляр парсера или None в случае ошибки
    """
    try:
        parser_type = source.get('parser_type', '').lower()
        
        if parser_type == 'rss':
            return RssParser(source)
        elif parser_type == 'html':
            # В будущем можно добавить поддержку HTML-парсера
            logger.warning(f"HTML-парсер пока не реализован полностью: {source.get('name')}")
            return None
        else:
            logger.error(f"Неизвестный тип парсера: {parser_type}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при создании парсера для источника {source.get('name')}: {e}")
        return None 