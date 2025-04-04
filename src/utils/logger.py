# src/utils/logger.py
import logging
import os
import sys
from loguru import logger
import argparse
from typing import Optional

def setup_logger(log_level: Optional[str] = None, log_file: Optional[str] = None):
    """
    Настройка логирования с использованием loguru
    
    Args:
        log_level: Уровень логирования (по умолчанию берется из .env)
        log_file: Путь к файлу для логирования (по умолчанию logs/app.log)
    """
    # Получаем уровень логирования из параметров или из переменных окружения
    log_level = log_level or os.environ.get('LOG_LEVEL', 'INFO')
    
    # Определяем путь к файлу логов
    log_file = log_file or os.environ.get('LOG_FILE', 'logs/app.log')
    
    # Создаем директорию для логов, если ее нет
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Удаляем все обработчики логов по умолчанию
    logger.remove()
    
    # Формат сообщения для консоли (цветной, компактный)
    console_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    # Формат сообщения для файла (детальный, с трассировкой)
    file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}"
    
    # Добавляем обработчик для вывода в консоль
    logger.add(
        sys.stderr,
        format=console_format,
        level=log_level,
        colorize=True
    )
    
    # Добавляем обработчик для записи в файл с ротацией
    # Ротация происходит при достижении 10 МБ, хранится 5 архивных файлов
    logger.add(
        log_file,
        format=file_format,
        level=log_level,
        rotation="10 MB",
        compression="zip",
        retention=5,
        backtrace=True,
        diagnose=True
    )
    
    # Перехватываем логи из стандартного logging
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Получаем соответствующий уровень loguru
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            # Находим вызывающий код
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            
            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )
    
    # Настраиваем перехват для всех стандартных логов
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Логируем базовую информацию
    logger.info(f"Логирование настроено: уровень={log_level}, файл={log_file}")
    
    return logger

def add_logging_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Добавляет аргументы для логирования к парсеру аргументов командной строки
    
    Args:
        parser: Парсер аргументов
        
    Returns:
        argparse.ArgumentParser: Обновленный парсер аргументов
    """
    log_group = parser.add_argument_group('Параметры логирования')
    log_group.add_argument(
        '--log-level',
        choices=['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'],
        default=os.environ.get('LOG_LEVEL', 'INFO'),
        help='Уровень детализации логов (по умолчанию: INFO)'
    )
    log_group.add_argument(
        '--log-file',
        default=os.environ.get('LOG_FILE', 'logs/app.log'),
        help='Путь к файлу логов (по умолчанию: logs/app.log)'
    )
    return parser 