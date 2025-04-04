# AI Content Aggregator

Система для парсинга и агрегации статей по теме ИИ и ИИ-агентов из открытых источников с последующим сохранением в Supabase.

## Описание

Проект представляет собой инструмент для автоматического сбора статей по теме искусственного интеллекта из различных интернет-источников. Система поддерживает два типа источников:

- RSS-ленты (через библиотеку feedparser)
- HTML-страницы (через requests + BeautifulSoup)

Собранные статьи сохраняются в базу данных Supabase для дальнейшей обработки, перевода и публикации.

## Структура проекта

```
├── fetch_articles.py     # Основной скрипт для загрузки статей
├── init_db.py            # Скрипт для инициализации базы данных
├── import_sources.py     # Скрипт для импорта источников из CSV/Excel
├── .env                  # Файл с переменными окружения (не включен в репозиторий)
├── .env.example          # Пример файла с переменными окружения
├── requirements.txt      # Зависимости проекта
├── examples/             # Примеры файлов
│   ├── sources.csv       # Пример CSV с источниками
│   ├── sources.xlsx      # Пример Excel с источниками
├── logs/                 # Директория для файлов логов
│   ├── app.log           # Основной файл логов
├── supabase/             # Файлы для Supabase
│   ├── migrations/       # SQL-миграции
│       ├── 20231101000000_create_content_tables.sql  # Создание таблиц
├── src/
│   ├── parsers/          # Модули для парсинга источников
│   │   ├── base_parser.py   # Базовый класс парсера
│   │   ├── rss_parser.py    # Парсер RSS-лент
│   │   ├── html_parser.py   # Парсер HTML-страниц
│   ├── db/               # Модули для работы с базой данных
│   │   ├── supabase_client.py  # Клиент для Supabase
│   ├── utils/            # Вспомогательные утилиты
│   │   ├── logger.py        # Настройка логирования
```

## Установка и настройка

1. Клонируйте репозиторий:

```bash
git clone <url-репозитория>
cd ai-content-aggregator
```

2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` на основе `.env.example` и укажите ваши параметры подключения к Supabase:

```
SUPABASE_URL=https://your-project-url.supabase.co
SUPABASE_KEY=your-supabase-key
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

4. Инициализируйте базу данных:

```bash
python init_db.py
```

Или выполните SQL-миграцию в Supabase:

```bash
supabase/migrations/20231101000000_create_content_tables.sql
```

## Использование

### Загрузка статей

Для запуска процесса загрузки статей выполните:

```bash
python fetch_articles.py
```

Доступные параметры:

```
usage: fetch_articles.py [-h] [--source-id SOURCE_ID] [--limit LIMIT] [--dry-run] [--no-delay]
                         [--log-level {TRACE,DEBUG,INFO,SUCCESS,WARNING,ERROR,CRITICAL}] [--log-file LOG_FILE]

Скрипт для загрузки статей из различных источников

options:
  -h, --help            показать это сообщение и выйти
  --source-id SOURCE_ID
                        ID конкретного источника для обработки (по умолчанию обрабатываются все активные источники)
  --limit LIMIT         Ограничение количества статей для загрузки из каждого источника (0 - без ограничений) (по умолчанию: 0)
  --dry-run             Режим проверки без сохранения в базу данных
  --no-delay            Отключить паузу между запросами к разным источникам

Параметры логирования:
  --log-level {TRACE,DEBUG,INFO,SUCCESS,WARNING,ERROR,CRITICAL}
                        Уровень детализации логов (по умолчанию: INFO)
  --log-file LOG_FILE   Путь к файлу логов (по умолчанию: logs/app.log)
```

Примеры:

```bash
# Загрузка статей только из одного источника
python fetch_articles.py --source-id 123e4567-e89b-12d3-a456-426614174000

# Ограничение количества статей до 5 на источник
python fetch_articles.py --limit 5

# Запуск в режиме проверки без записи в базу
python fetch_articles.py --dry-run

# Более подробное логирование
python fetch_articles.py --log-level DEBUG
```

### Импорт источников из CSV/Excel

Вы можете импортировать источники из CSV или Excel файла:

```bash
python import_sources.py examples/sources.csv
```

Доступные параметры:

```
usage: import_sources.py [-h] [--dry-run] [--no-update]
                         [--log-level {TRACE,DEBUG,INFO,SUCCESS,WARNING,ERROR,CRITICAL}] [--log-file LOG_FILE]
                         file

Импорт источников из CSV/Excel в базу данных Supabase

positional arguments:
  file                  Путь к CSV/Excel файлу с источниками

options:
  -h, --help            показать это сообщение и выйти
  --dry-run             Режим проверки без записи в базу данных
  --no-update           Не обновлять существующие источники

Параметры логирования:
  --log-level {TRACE,DEBUG,INFO,SUCCESS,WARNING,ERROR,CRITICAL}
                        Уровень детализации логов (по умолчанию: INFO)
  --log-file LOG_FILE   Путь к файлу логов (по умолчанию: logs/app.log)
```

Примеры:

```bash
# Проверка файла без сохранения в базу данных
python import_sources.py examples/sources.xlsx --dry-run

# Импорт без обновления существующих источников
python import_sources.py examples/sources.csv --no-update

# Подробное логирование в отдельный файл
python import_sources.py examples/sources.csv --log-level DEBUG --log-file logs/import.log
```

#### Формат CSV/Excel файла

Файл должен содержать следующие колонки:

- `name`: Название источника (обязательно)
- `url`: URL страницы источника (обязательно)
- `parser_type`: Тип парсера - "rss" или "html" (обязательно)
- `rss_url`: URL RSS-ленты (обязательно для типа "rss")
- `selectors`: JSON строка с CSS селекторами (обязательно для типа "html")
- `active`: Флаг активности источника (true/false)

Пример содержимого CSV:

```csv
name,url,parser_type,rss_url,selectors,active
TechCrunch AI,https://techcrunch.com/category/artificial-intelligence/,rss,https://techcrunch.com/category/artificial-intelligence/feed/,,true
MIT Tech Review,https://www.technologyreview.com/topic/artificial-intelligence/,html,,"{'list_item': 'article.card', 'title': 'h3'}",true
```

### Логирование

Система логирования настроена на сохранение сообщений в консоль и файл. Файлы логов хранятся в директории `logs/` и автоматически ротируются при достижении размера 10 МБ.

Уровни логирования:

- `TRACE`: Самый подробный уровень
- `DEBUG`: Для отладочной информации
- `INFO`: Стандартный уровень (по умолчанию)
- `SUCCESS`: Успешные операции
- `WARNING`: Предупреждения
- `ERROR`: Ошибки
- `CRITICAL`: Критические ошибки

Для изменения уровня логирования можно:

1. Передать параметр `--log-level` при запуске скрипта
2. Указать уровень в файле `.env` через переменную `LOG_LEVEL`

Для изменения пути к файлу логов можно:

1. Передать параметр `--log-file` при запуске скрипта
2. Указать путь в файле `.env` через переменную `LOG_FILE`

### Добавление новых источников вручную

Источники также можно добавлять непосредственно в базу данных Supabase в таблицу `sources`.

#### Пример для RSS-источника:

```json
{
  "name": "TechCrunch AI",
  "url": "https://techcrunch.com/category/artificial-intelligence/",
  "rss_url": "https://techcrunch.com/category/artificial-intelligence/feed/",
  "parser_type": "rss",
  "active": true
}
```

#### Пример для HTML-источника:

```json
{
  "name": "Example AI Blog",
  "url": "https://example.com/ai-blog",
  "parser_type": "html",
  "selectors": {
    "list_item": ".article-item",
    "title": "h2.title",
    "url": "a.article-link",
    "description": ".article-summary",
    "date": ".publish-date",
    "author": ".author-name",
    "content": "article.content"
  },
  "active": true
}
```

## Схема базы данных

### Таблица `content_items`

- `id`: UUID PRIMARY KEY
- `title`: TEXT
- `url`: TEXT UNIQUE
- `published_at`: TIMESTAMP
- `source`: TEXT
- `author`: TEXT
- `description`: TEXT
- `content`: TEXT
- `language`: TEXT DEFAULT 'en'
- `is_translated`: BOOLEAN DEFAULT false
- `is_published`: BOOLEAN DEFAULT false
- `keywords`: TEXT[]
- `category`: TEXT
- `created_at`: TIMESTAMP DEFAULT now()
- `updated_at`: TIMESTAMP DEFAULT now()

### Таблица `sources`

- `id`: UUID PRIMARY KEY
- `name`: TEXT
- `url`: TEXT
- `rss_url`: TEXT NULL
- `parser_type`: TEXT ('rss' | 'html')
- `selectors`: JSONB NULL
- `active`: BOOLEAN DEFAULT true
- `last_fetch_at`: TIMESTAMP
- `fetch_frequency`: INTERVAL DEFAULT '1 day'
- `created_at`: TIMESTAMP DEFAULT now()
- `updated_at`: TIMESTAMP DEFAULT now()

## Лицензия

MIT

# Content Agent

Система для сбора и агрегации статей по AI.

## Установка

1. Клонировать репозиторий
2. Установить зависимости: `pip install -r requirements.txt`
3. Создать файл `.env` с настройками Supabase:

```
SUPABASE_URL=https://your-supabase-url.supabase.co
SUPABASE_KEY=your-supabase-key
```

4. Создать таблицы в Supabase через SQL Editor, используя файл `supabase/migrations/20231101000000_create_content_tables.sql`
5. Инициализировать базу данных: `python init_db.py`

## Команды

### Инициализация базы данных

```bash
python init_db.py
```

### Загрузка статей из источников

```bash
python fetch_articles.py --limit 10
```

### Ежедневное обновление статей

Для автоматизации процесса сбора статей можно использовать скрипт ежедневного обновления:

```bash
python daily_update.py --limit 10 --age 1
```

Параметры:

- `--limit`: максимальное количество статей для каждого источника
- `--age`: максимальный возраст статей в днях
- `--log-level`: уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--all-sources`: обрабатывать все источники, игнорируя дату последнего обновления
- `--dry-run`: запуск без фактического сохранения в базу данных

## Настройка регулярного запуска

### Linux/macOS (Cron)

Для настройки ежедневного запуска в 9:00 утра:

```bash
crontab -e
```

Добавить строку:

```
0 9 * * * cd /path/to/content-agent && /path/to/python daily_update.py --limit 20
```

### Windows (Task Scheduler)

1. Откройте "Планировщик заданий" (Task Scheduler)
2. Создайте новую задачу:
   - Триггер: Ежедневно в 9:00
   - Действие: Запуск программы
   - Программа: путь к исполняемому файлу Python
   - Аргументы: `daily_update.py --limit 20`
   - Начальная папка: путь к директории проекта

### Автоматическая настройка cron (Linux/macOS)

Если crontab доступен, можно использовать скрипт:

```bash
python setup_cron.py --time "0 9 * * *" --limit 20
```

Для удаления задачи:

```bash
python setup_cron.py --remove
```
