#!/bin/bash

# Проверка состояния сервисов
check_services() {
    echo "Проверка состояния сервисов..."
    docker ps
    echo ""
    
    # Проверка доступности API
    echo "Проверка доступности API..."
    curl -s http://localhost:8000/health
    echo ""
}

# Основной цикл тестирования
for i in {1..3}; do
    echo "=== Тест $i ==="
    
    # Выключаем сервисы
    echo "Выключение сервисов..."
    docker compose down
    sleep 5
    
    # Проверяем, что сервисы остановлены
    echo "Проверка после остановки..."
    docker ps
    echo ""
    
    # Запускаем сервисы
    echo "Запуск сервисов..."
    docker compose up -d
    sleep 10
    
    # Проверяем состояние после запуска
    check_services
    
    # Ждем между тестами
    echo "Пауза между тестами..."
    sleep 10
    
    echo "=== Конец теста $i ==="
    echo ""
done
