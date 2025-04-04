-- Добавление новых полей для обработки контента с помощью Gemini API

-- Добавляем поле для флага очистки HTML
ALTER TABLE content_items 
ADD COLUMN IF NOT EXISTS is_cleaned BOOLEAN DEFAULT false;

-- Добавляем поле для очищенного контента
ALTER TABLE content_items 
ADD COLUMN IF NOT EXISTS clean_content TEXT;

-- Добавляем поле для переписанного контента
ALTER TABLE content_items 
ADD COLUMN IF NOT EXISTS rewritten_content TEXT;

-- Добавляем поле для переведенного контента
ALTER TABLE content_items 
ADD COLUMN IF NOT EXISTS translated_content TEXT;

-- Добавляем индекс для поля is_cleaned
CREATE INDEX IF NOT EXISTS idx_content_items_is_cleaned ON content_items(is_cleaned);

-- Добавляем комментарии к новым колонкам
COMMENT ON COLUMN content_items.is_cleaned IS 'Флаг очистки и переписывания контента';
COMMENT ON COLUMN content_items.clean_content IS 'Очищенный HTML-контент статьи';
COMMENT ON COLUMN content_items.rewritten_content IS 'Переписанный HTML-контент статьи на английском';
COMMENT ON COLUMN content_items.translated_content IS 'Переведенный HTML-контент статьи на русском'; 