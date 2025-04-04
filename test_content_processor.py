#!/usr/bin/env python
# test_content_processor.py - Unit-тесты для микросервиса обработки контента

import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import json

from content_processor import ContentProcessor, ProcessingResult


class TestContentProcessor(unittest.TestCase):
    """Тесты для класса ContentProcessor."""
    
    def setUp(self):
        """Настройка окружения перед каждым тестом."""
        # Мокаем переменные окружения
        self.env_patcher = patch.dict('os.environ', {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_KEY': 'test_key',
            'GEMINI_API_KEY': 'test_gemini_key'
        })
        self.env_patcher.start()
        
        # Мокаем Supabase клиент
        self.mock_supabase = MagicMock()
        self.create_client_patcher = patch('content_processor.create_client', 
                                         return_value=self.mock_supabase)
        self.mock_create_client = self.create_client_patcher.start()
        
        # Мокаем Gemini API
        self.mock_genai = MagicMock()
        self.genai_patcher = patch('content_processor.genai', self.mock_genai)
        self.mock_genai_module = self.genai_patcher.start()
        
        # Мокаем модель Gemini
        self.mock_model = MagicMock()
        self.mock_genai_module.GenerativeModel.return_value = self.mock_model
        
        # Создаем экземпляр процессора
        self.processor = ContentProcessor()
    
    def tearDown(self):
        """Очистка после каждого теста."""
        self.env_patcher.stop()
        self.create_client_patcher.stop()
        self.genai_patcher.stop()
    
    def test_init(self):
        """Тест инициализации ContentProcessor."""
        self.assertEqual(self.processor.db_client, self.mock_supabase)
        self.mock_genai_module.configure.assert_called_once_with(api_key='test_gemini_key')
        self.mock_genai_module.GenerativeModel.assert_called_once_with('gemini-pro')
    
    def test_clean_html(self):
        """Тест очистки HTML контента."""
        # Тестовый HTML
        html_content = """
        <html>
            <head>
                <title>Тестовая статья</title>
                <script>alert('test');</script>
                <style>body { color: red; }</style>
            </head>
            <body>
                <h1>Заголовок</h1>
                <p>Параграф 1</p>
                <!-- Комментарий -->
                <p>Параграф 2</p>
            </body>
        </html>
        """
        
        result = self.processor.clean_html(html_content)
        
        # Проверяем что скрипты, стили и комментарии удалены
        self.assertNotIn('script', result)
        self.assertNotIn('style', result)
        self.assertNotIn('Комментарий', result)
        
        # Проверяем, что текст сохранен
        self.assertIn('Заголовок', result)
        self.assertIn('Параграф 1', result)
        self.assertIn('Параграф 2', result)
    
    def test_clean_html_empty_content(self):
        """Тест очистки пустого HTML контента."""
        result = self.processor.clean_html("")
        self.assertEqual(result, "")
        
        result = self.processor.clean_html(None)
        self.assertEqual(result, "")
    
    def test_rewrite_content(self):
        """Тест переписывания контента."""
        content = "Тестовый контент для переписывания."
        
        # Мокаем ответ от Gemini API
        mock_response = MagicMock()
        mock_response.text = "Переписанный тестовый контент."
        self.mock_model.generate_content.return_value = mock_response
        
        result = self.processor.rewrite_content(content)
        
        # Проверяем что был вызван нужный метод с правильным промптом
        self.mock_model.generate_content.assert_called_once()
        call_args = self.mock_model.generate_content.call_args[0][0]
        self.assertIn(content, call_args)
        
        # Проверяем результат
        self.assertEqual(result, "Переписанный тестовый контент.")
    
    def test_rewrite_content_empty(self):
        """Тест переписывания пустого контента."""
        result = self.processor.rewrite_content("")
        self.assertIsNone(result)
        
        result = self.processor.rewrite_content(None)
        self.assertIsNone(result)
    
    def test_translate_content(self):
        """Тест перевода контента."""
        content = "Test content for translation."
        
        # Мокаем ответ от Gemini API
        mock_response = MagicMock()
        mock_response.text = "Тестовый контент для перевода."
        self.mock_model.generate_content.return_value = mock_response
        
        result = self.processor.translate_content(content)
        
        # Проверяем что был вызван нужный метод с правильным промптом
        self.mock_model.generate_content.assert_called_once()
        call_args = self.mock_model.generate_content.call_args[0][0]
        self.assertIn(content, call_args)
        
        # Проверяем результат
        self.assertEqual(result, "Тестовый контент для перевода.")
    
    def test_translate_content_empty(self):
        """Тест перевода пустого контента."""
        result = self.processor.translate_content("")
        self.assertIsNone(result)
        
        result = self.processor.translate_content(None)
        self.assertIsNone(result)
    
    def test_update_article(self):
        """Тест обновления статьи в базе данных."""
        article_id = "test-id"
        result = ProcessingResult(
            clean_content="Очищенный контент",
            rewritten_content="Переписанный контент",
            translated_content="Переведенный контент",
            success=True
        )
        
        # Настраиваем мок для Supabase
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq = MagicMock()
        mock_update.eq.return_value = mock_eq
        
        # Вызываем метод
        success = self.processor.update_article(article_id, result)
        
        # Проверяем, что нужные методы были вызваны
        self.mock_supabase.table.assert_called_with('content_items')
        mock_table.update.assert_called_once()
        mock_update.eq.assert_called_with('id', article_id)
        mock_eq.execute.assert_called_once()
        
        # Проверяем, что обновление прошло успешно
        self.assertTrue(success)
        
        # Проверяем переданные данные
        update_data = mock_table.update.call_args[0][0]
        self.assertEqual(update_data['clean_content'], "Очищенный контент")
        self.assertEqual(update_data['rewritten_content'], "Переписанный контент")
        self.assertEqual(update_data['translated_content'], "Переведенный контент")
        self.assertTrue(update_data['is_cleaned'])
        self.assertTrue(update_data['is_translated'])
    
    def test_process_article(self):
        """Тест полного процесса обработки статьи."""
        # Создаем тестовую статью
        article = {
            'id': 'test-id',
            'title': 'Тестовая статья',
            'content': '<p>Тестовый контент</p>'
        }
        
        # Мокаем методы для очистки, переписывания и перевода
        with patch.object(self.processor, 'clean_html', 
                         return_value="Очищенный контент") as mock_clean, \
             patch.object(self.processor, 'rewrite_content', 
                         return_value="Переписанный контент") as mock_rewrite, \
             patch.object(self.processor, 'translate_content', 
                         return_value="Переведенный контент") as mock_translate:
            
            # Вызываем метод обработки
            result = self.processor.process_article(article)
            
            # Проверяем, что все методы были вызваны с правильными параметрами
            mock_clean.assert_called_with(article['content'])
            mock_rewrite.assert_called_with("Очищенный контент")
            mock_translate.assert_called_with("Переписанный контент")
            
            # Проверяем результат
            self.assertTrue(result.success)
            self.assertEqual(result.clean_content, "Очищенный контент")
            self.assertEqual(result.rewritten_content, "Переписанный контент")
            self.assertEqual(result.translated_content, "Переведенный контент")
    
    def test_process_article_no_content(self):
        """Тест обработки статьи без контента."""
        article = {
            'id': 'test-id',
            'title': 'Тестовая статья без контента'
        }
        
        result = self.processor.process_article(article)
        
        self.assertFalse(result.success)
        self.assertIn("не имеет контента", result.error_message)
    
    def test_get_unprocessed_articles(self):
        """Тест получения необработанных статей."""
        # Мокаем ответ от Supabase
        mock_response = MagicMock()
        mock_articles = [
            {'id': 'id1', 'title': 'Статья 1', 'content': 'Контент 1'},
            {'id': 'id2', 'title': 'Статья 2', 'content': 'Контент 2'}
        ]
        mock_response.data = mock_articles
        
        # Настраиваем мок для Supabase
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_not_is = MagicMock()
        mock_eq.not_.is_.return_value = mock_not_is
        mock_limit = MagicMock()
        mock_not_is.limit.return_value = mock_limit
        mock_limit.execute.return_value = mock_response
        
        # Вызываем метод
        articles = self.processor.get_unprocessed_articles(2)
        
        # Проверяем, что нужные методы были вызваны
        self.mock_supabase.table.assert_called_with('content_items')
        mock_table.select.assert_called_with('*')
        mock_select.eq.assert_called_with('is_cleaned', False)
        mock_not_is.limit.assert_called_with(2)
        mock_limit.execute.assert_called_once()
        
        # Проверяем результат
        self.assertEqual(articles, mock_articles)


if __name__ == '__main__':
    unittest.main() 