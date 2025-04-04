#!/bin/bash
# run_content_processor.sh - Скрипт для запуска обработчика контента по расписанию

# Переменные
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
LOG_DIR="${SCRIPT_DIR}/logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${LOG_DIR}/content_processor_${TIMESTAMP}.log"

# Создаем директорию для логов, если её нет
mkdir -p "${LOG_DIR}"

# Переходим в директорию скрипта
cd "${SCRIPT_DIR}"

# Проверяем наличие виртуального окружения
if [ -d "venv" ]; then
    echo "Активируем виртуальное окружение..."
    source venv/bin/activate
fi

# Запускаем обработчик контента и записываем вывод в лог
echo "Запуск обработчика контента ($(date))" | tee -a "${LOG_FILE}"
python content_processor.py --limit 10 2>&1 | tee -a "${LOG_FILE}"

# Проверяем статус выполнения
if [ $? -eq 0 ]; then
    echo "Обработчик контента успешно завершил работу ($(date))" | tee -a "${LOG_FILE}"
    EXIT_CODE=0
else
    echo "Произошла ошибка при выполнении обработчика контента ($(date))" | tee -a "${LOG_FILE}"
    EXIT_CODE=1
fi

# Если использовалось виртуальное окружение, деактивируем его
if [ -d "venv" ]; then
    deactivate
fi

exit ${EXIT_CODE} 