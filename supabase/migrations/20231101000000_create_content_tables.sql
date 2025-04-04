-- Расширение для генерации UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Таблица content_items для хранения собранных статей
CREATE TABLE IF NOT EXISTS content_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    published_at TIMESTAMP,
    source TEXT,
    author TEXT,
    description TEXT,
    content TEXT,
    language TEXT DEFAULT 'en',
    is_translated BOOLEAN DEFAULT false,
    is_published BOOLEAN DEFAULT false,
    keywords TEXT[],
    category TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Таблица sources для хранения конфигурации источников
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    rss_url TEXT,
    parser_type TEXT NOT NULL,
    selectors JSONB,
    active BOOLEAN DEFAULT true,
    last_fetch_at TIMESTAMP,
    fetch_frequency INTERVAL DEFAULT '1 day'::INTERVAL,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Создаем индексы для часто используемых полей в content_items
CREATE INDEX IF NOT EXISTS idx_content_items_source ON content_items(source);
CREATE INDEX IF NOT EXISTS idx_content_items_language ON content_items(language);
CREATE INDEX IF NOT EXISTS idx_content_items_is_translated ON content_items(is_translated);
CREATE INDEX IF NOT EXISTS idx_content_items_is_published ON content_items(is_published);
CREATE INDEX IF NOT EXISTS idx_content_items_published_at ON content_items(published_at);
CREATE INDEX IF NOT EXISTS idx_content_items_keywords ON content_items USING GIN(keywords);

-- Создаем индексы для часто используемых полей в sources
CREATE INDEX IF NOT EXISTS idx_sources_active ON sources(active);
CREATE INDEX IF NOT EXISTS idx_sources_parser_type ON sources(parser_type);
CREATE INDEX IF NOT EXISTS idx_sources_last_fetch_at ON sources(last_fetch_at);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = now();
   RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для content_items
CREATE TRIGGER update_content_items_updated_at
BEFORE UPDATE ON content_items
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();

-- Триггер для sources
CREATE TRIGGER update_sources_updated_at
BEFORE UPDATE ON sources
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();

-- Добавляем комментарии к таблицам
COMMENT ON TABLE content_items IS 'Собранные статьи по теме ИИ из различных источников';
COMMENT ON TABLE sources IS 'Конфигурация источников для сбора статей';

-- Добавляем комментарии к колонкам content_items
COMMENT ON COLUMN content_items.id IS 'Уникальный идентификатор';
COMMENT ON COLUMN content_items.title IS 'Заголовок статьи';
COMMENT ON COLUMN content_items.url IS 'URL статьи (уникальный)';
COMMENT ON COLUMN content_items.published_at IS 'Дата публикации статьи';
COMMENT ON COLUMN content_items.source IS 'Идентификатор источника';
COMMENT ON COLUMN content_items.author IS 'Автор статьи';
COMMENT ON COLUMN content_items.description IS 'Краткое описание статьи';
COMMENT ON COLUMN content_items.content IS 'Полный HTML-контент статьи';
COMMENT ON COLUMN content_items.language IS 'Язык статьи (по умолчанию английский)';
COMMENT ON COLUMN content_items.is_translated IS 'Флаг перевода статьи';
COMMENT ON COLUMN content_items.is_published IS 'Флаг публикации статьи';
COMMENT ON COLUMN content_items.keywords IS 'Ключевые слова статьи';
COMMENT ON COLUMN content_items.category IS 'Категория статьи';
COMMENT ON COLUMN content_items.created_at IS 'Дата сохранения в базу';
COMMENT ON COLUMN content_items.updated_at IS 'Дата последнего обновления';

-- Добавляем комментарии к колонкам sources
COMMENT ON COLUMN sources.id IS 'Уникальный идентификатор';
COMMENT ON COLUMN sources.name IS 'Название источника';
COMMENT ON COLUMN sources.url IS 'URL страницы источника';
COMMENT ON COLUMN sources.rss_url IS 'URL RSS-ленты (для RSS-источников)';
COMMENT ON COLUMN sources.parser_type IS 'Тип парсера (rss или html)';
COMMENT ON COLUMN sources.selectors IS 'JSON с CSS-селекторами (для HTML-источников)';
COMMENT ON COLUMN sources.active IS 'Флаг активности источника';
COMMENT ON COLUMN sources.last_fetch_at IS 'Время последней загрузки статей';
COMMENT ON COLUMN sources.fetch_frequency IS 'Частота загрузки статей';
COMMENT ON COLUMN sources.created_at IS 'Дата создания записи';
COMMENT ON COLUMN sources.updated_at IS 'Дата последнего обновления'; 