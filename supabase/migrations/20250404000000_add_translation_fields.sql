-- Миграция для добавления полей переведенного контента на русский язык
-- (title_ru, description_ru, content_ru)

-- Добавляем новые колонки в таблицу content_items
ALTER TABLE content_items 
ADD COLUMN IF NOT EXISTS title_ru TEXT,
ADD COLUMN IF NOT EXISTS description_ru TEXT,
ADD COLUMN IF NOT EXISTS content_ru TEXT;

-- Добавляем комментарии к новым колонкам
COMMENT ON COLUMN content_items.title_ru IS 'Переведенный на русский язык заголовок статьи';
COMMENT ON COLUMN content_items.description_ru IS 'Переведенное на русский язык краткое описание статьи';
COMMENT ON COLUMN content_items.content_ru IS 'Переведенный на русский язык полный контент статьи';

-- Создаем индексы для поиска по русскоязычному контенту
CREATE INDEX IF NOT EXISTS idx_content_items_title_ru ON content_items USING gin(to_tsvector('russian', title_ru));
CREATE INDEX IF NOT EXISTS idx_content_items_content_ru ON content_items USING gin(to_tsvector('russian', content_ru)); 