#!/usr/bin/env python
# setup_cron.py
"""
Скрипт для настройки регулярного запуска обновления базы данных через cron
"""
import os
import sys
import argparse
import subprocess
from crontab import CronTab
from pathlib import Path

def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Настройка регулярного обновления через cron')
    parser.add_argument('--time', type=str, default='0 8 * * *',
                      help='Время для запуска обновления в формате cron (по умолчанию: каждый день в 8:00)')
    parser.add_argument('--limit', type=int, default=10,
                      help='Максимальное количество статей для каждого источника')
    parser.add_argument('--remove', action='store_true',
                      help='Удаление задачи cron вместо добавления')
    return parser.parse_args()

def get_python_path():
    """Получение пути к текущему интерпретатору Python"""
    return sys.executable

def get_absolute_script_path(script_name):
    """Получение абсолютного пути к скрипту"""
    project_dir = Path(__file__).resolve().parent
    return project_dir / script_name

def setup_cron(cron_time, limit, remove=False):
    """
    Настройка задачи cron для регулярного запуска обновления
    
    Args:
        cron_time: Время в формате cron
        limit: Лимит статей
        remove: Удалить существующую задачу
    """
    try:
        # Получаем пути
        python_path = get_python_path()
        script_path = get_absolute_script_path('daily_update.py')
        
        # Инициализируем crontab текущего пользователя
        cron = CronTab(user=True)
        
        # Комментарий для идентификации нашей задачи
        comment = 'content_agent_daily_update'
        
        # Удаляем существующие задачи с таким комментарием
        existing_jobs = list(cron.find_comment(comment))
        for job in existing_jobs:
            cron.remove(job)
            print(f"Удалена существующая задача cron: {job}")
        
        # Если требуется только удаление, выходим
        if remove:
            cron.write()
            print("Задача cron успешно удалена")
            return
        
        # Создаем новую задачу
        job = cron.new(command=f"{python_path} {script_path} --limit {limit}", comment=comment)
        job.setall(cron_time)
        
        # Сохраняем изменения
        cron.write()
        
        print(f"Задача cron настроена: '{cron_time}' для команды '{python_path} {script_path} --limit {limit}'")
        next_run = job.schedule(date_from=job.next(return_datetime=True)).get_next()
        print(f"Следующий запуск: {next_run}")
        
    except Exception as e:
        print(f"Ошибка при настройке cron: {e}")
        return False
    
    return True

def check_crontab_availability():
    """Проверка доступности crontab"""
    try:
        subprocess.run(['crontab', '-l'], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def main():
    """Основная функция"""
    if not check_crontab_availability():
        print("Ошибка: crontab не доступен в системе")
        return 1
    
    args = parse_args()
    
    print(f"{'Удаление' if args.remove else 'Настройка'} задачи cron для ежедневного обновления...")
    
    success = setup_cron(args.time, args.limit, args.remove)
    
    if not success:
        print("Не удалось настроить задачу cron")
        return 1
        
    print("Готово!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 