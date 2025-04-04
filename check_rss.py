#!/usr/bin/env python
# check_rss.py
import requests
import feedparser
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем список источников
SOURCES = [
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/",
        "rss_url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "parser_type": "rss",
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/ai-artificial-intelligence",
        "rss_url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        "parser_type": "rss",
        "alt_rss_urls": [
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            "https://www.theverge.com/rss/index.xml"
        ]
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/",
        "rss_url": "https://venturebeat.com/category/ai/feed/",
        "parser_type": "rss",
    },
    {
        "name": "AI News",
        "url": "https://www.artificialintelligence-news.com/",
        "rss_url": "https://www.artificialintelligence-news.com/news/feed/",
        "parser_type": "rss",
        "alt_rss_urls": [
            "https://www.artificialintelligence-news.com/feed/",
            "https://artificialintelligence-news.com/feed/"
        ]
    }
]

def check_url(url):
    """Проверка доступности URL и заголовков ответа"""
    try:
        response = requests.head(url, timeout=10)
        return {
            "status": response.status_code,
            "content_type": response.headers.get("Content-Type", ""),
            "success": 200 <= response.status_code < 300
        }
    except Exception as e:
        return {
            "status": "Error",
            "content_type": "",
            "success": False,
            "error": str(e)
        }

def check_rss(url):
    """Проверка доступности RSS и парсинг содержимого"""
    try:
        feed = feedparser.parse(url)
        
        # Проверяем наличие ошибок при парсинге
        if feed.bozo and feed.bozo_exception:
            return {
                "success": False,
                "error": str(feed.bozo_exception),
                "entries": 0
            }
        
        return {
            "success": True,
            "entries": len(feed.entries),
            "feed_title": feed.feed.get("title", "Неизвестно") if hasattr(feed, 'feed') else "Нет данных"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "entries": 0
        }

def main():
    print("Проверка RSS-лент источников")
    print("-" * 80)
    
    for source in SOURCES:
        print(f"\nИсточник: {source['name']}")
        print(f"URL сайта: {source['url']}")
        
        # Проверяем основной RSS URL
        print(f"\nОсновной RSS URL: {source['rss_url']}")
        http_result = check_url(source['rss_url'])
        print(f"HTTP Статус: {http_result['status']}, Content-Type: {http_result['content_type']}")
        
        rss_result = check_rss(source['rss_url'])
        if rss_result['success']:
            print(f"RSS статус: Успешно, Название ленты: {rss_result['feed_title']}, Статей: {rss_result['entries']}")
        else:
            print(f"RSS статус: Ошибка, {rss_result['error']}")
        
        # Проверяем альтернативные RSS URL, если есть и если основной не работает
        if not rss_result['success'] and 'alt_rss_urls' in source:
            print("\nПроверка альтернативных RSS URL:")
            for alt_url in source['alt_rss_urls']:
                print(f"\nАльтернативный RSS URL: {alt_url}")
                alt_http_result = check_url(alt_url)
                print(f"HTTP Статус: {alt_http_result['status']}, Content-Type: {alt_http_result['content_type']}")
                
                alt_rss_result = check_rss(alt_url)
                if alt_rss_result['success']:
                    print(f"RSS статус: Успешно, Название ленты: {alt_rss_result['feed_title']}, Статей: {alt_rss_result['entries']}")
                else:
                    print(f"RSS статус: Ошибка, {alt_rss_result['error']}")
        
        print("-" * 80)

if __name__ == "__main__":
    main() 