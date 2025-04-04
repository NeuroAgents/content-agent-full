# create_excel_example.py
import os
import pandas as pd
import json

# Создаем директорию examples, если её нет
os.makedirs('examples', exist_ok=True)

# Данные для файла
data = [
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/",
        "parser_type": "rss",
        "rss_url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "selectors": None,
        "active": True
    },
    {
        "name": "AI News",
        "url": "https://www.artificialintelligence-news.com/",
        "parser_type": "rss",
        "rss_url": "https://www.artificialintelligence-news.com/news/feed/",
        "selectors": None,
        "active": True
    },
    {
        "name": "Wired AI",
        "url": "https://www.wired.com/tag/artificial-intelligence/",
        "parser_type": "rss",
        "rss_url": "https://www.wired.com/feed/tag/artificial-intelligence/rss",
        "selectors": None,
        "active": True
    },
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/",
        "parser_type": "html",
        "rss_url": None,
        "selectors": json.dumps({
            "list_item": "article.card", 
            "title": "h3", 
            "url": "a.card-hed-link", 
            "description": "div.card-description", 
            "date": "time.card-date", 
            "author": "span.card-author", 
            "content": "div.article-main-component"
        }),
        "active": True
    },
    {
        "name": "AI Agents Blog",
        "url": "https://example.com/ai-agents-blog",
        "parser_type": "html",
        "rss_url": None,
        "selectors": json.dumps({
            "list_item": ".blog-post", 
            "title": "h2.title", 
            "url": "a.post-link", 
            "description": ".excerpt", 
            "date": ".post-date", 
            "author": ".author-name", 
            "content": "article.post-content"
        }),
        "active": False
    }
]

# Создаем DataFrame
df = pd.DataFrame(data)

# Сохраняем в Excel
df.to_excel('examples/sources.xlsx', index=False)

print(f"Файл примера Excel создан: examples/sources.xlsx")