#!/bin/bash
# Скрипт для запуска обработчика контента

# Получаем директорию, в которой находится скрипт
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Настройка логирования
LOGS_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOGS_DIR/content_processor_$(date +%Y%m%d_%H%M%S).log"

# Создаем директорию для логов, если она не существует
mkdir -p "$LOGS_DIR"

# Активируем виртуальное окружение, если оно существует
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
    echo "Виртуальное окружение активировано."
fi

# Запускаем обработчик контента
echo "Запуск обработчика контента $(date)"
echo "Логи сохраняются в $LOG_FILE"

# Запускаем новую версию обработчика (v2), который сохраняет переводы в JSON-формате
python "$SCRIPT_DIR/content_processor_v2.py" --limit 10 --hours 24 2>&1 | tee -a "$LOG_FILE"

# Проверяем статус выполнения
STATUS=${PIPESTATUS[0]}
if [ $STATUS -eq 0 ]; then
    echo "Обработчик контента успешно завершил работу $(date)" | tee -a "$LOG_FILE"
else
    echo "Ошибка при выполнении обработчика контента, код: $STATUS $(date)" | tee -a "$LOG_FILE"
fi

# Деактивируем виртуальное окружение, если оно было активировано
if [ -d "$SCRIPT_DIR/venv" ]; then
    deactivate
    echo "Виртуальное окружение деактивировано."
fi 