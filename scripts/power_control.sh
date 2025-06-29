#!/bin/bash

# Настройка логирования
LOG_FILE="/home/uss/Vera/logs/vera.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Скрипт управления питанием системы

# Проверяем права пользователя
if [ "$EUID" -ne 0 ]; then 
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] Для выполнения этого скрипта необходимы права суперпользователя"
    exit 1
fi

# Функция для безопасного выключения
safe_shutdown() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Выполнение безопасного выключения..."
    # Останавливаем контейнеры
    /home/uss/Vera/scripts/start_vera.sh
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Выключение системы..."
    # Выключаем систему
    shutdown -h now
}

# Функция для безопасного перезапуска
safe_restart() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Выполнение безопасного перезапуска..."
    # Останавливаем контейнеры
    /home/uss/Vera/scripts/start_vera.sh
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Перезапуск системы..."
    # Перезапускаем систему
    shutdown -r now
}

# Основной скрипт
while true; do
    # Проверяем наличие файла флага для выключения
    if [ -f "/home/uss/Vera/.shutdown_flag" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Обнаружен флаг выключения..."
        safe_shutdown
        exit 0
    fi
    
    # Проверяем наличие файла флага для перезапуска
    if [ -f "/home/uss/Vera/.restart_flag" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Обнаружен флаг перезапуска..."
        safe_restart
        exit 0
    fi
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Система работает нормально..."
    sleep 10

done
