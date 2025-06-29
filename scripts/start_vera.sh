#!/bin/bash

# Настройка логирования
LOG_FILE="/home/uss/Vera/logs/vera.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# Функция для корректной остановки контейнеров
stop_containers() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Остановка контейнеров Vera..."
    cd /home/uss/Vera
    docker compose down
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Контейнеры остановлены"
}

# Обработка сигналов остановки
trap stop_containers SIGTERM SIGINT

# Проверяем, запущены ли контейнеры
if ! docker ps | grep -q vera-app; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Запускаем контейнеры Vera..."
    cd /home/uss/Vera
    docker compose up -d
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Контейнеры запущены"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Контейнеры уже запущены"
fi

# Ожидание завершения работы
while true; do
    sleep 1
    # Проверка состояния контейнеров каждые 5 минут
    if [ $(($(date +%s) % 300)) -eq 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] Проверка состояния контейнеров..."
        docker compose ps
    fi
done
