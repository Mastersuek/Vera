#!/bin/bash

set -e

echo "🚀 Настройка окружения разработки Vera Platform..."

# Проверка установки Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Пожалуйста, установите Docker."
    echo "📖 Инструкция: https://docs.docker.com/get-docker/"
    exit 1
fi

# Проверка установки Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Пожалуйста, установите Docker Compose."
    echo "📖 Инструкция: https://docs.docker.com/compose/install/"
    exit 1
fi

# Создание файла .env, если его нет
if [ ! -f .env ]; then
    echo "📄 Создание файла .env из .env.example..."
    cp .env.example .env
    echo "✅ Файл .env создан. Пожалуйста, проверьте и обновите настройки при необходимости."
else
    echo "ℹ️  Файл .env уже существует. Пропускаем создание."
fi

# Генерация SSL-сертификатов
if [ ! -f "nginx/ssl/certs/nginx-selfsigned.crt" ] || [ ! -f "nginx/ssl/private/nginx-selfsigned.key" ]; then
    echo "🔐 Генерация SSL-сертификатов..."
    mkdir -p nginx/ssl/private nginx/ssl/certs
    ./scripts/generate_ssl.sh
    echo "✅ SSL-сертификаты успешно сгенерированы."
else
    echo "ℹ️  SSL-сертификаты уже существуют. Пропускаем генерацию."
fi

# Сборка и запуск контейнеров
echo "🐳 Сборка и запуск Docker-контейнеров..."
docker-compose up -d --build

echo "
🎉 Настройка завершена! Vera Platform успешно запущена."
echo "
📋 Доступные сервисы:"
echo "  - API: https://localhost/api/"
echo "  - Документация API: https://localhost/api/docs"
echo "  - Консоль MinIO: http://localhost:9001"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3000"
echo "
📝 Примечание: Возможно, потребуется добавить самоподписанный сертификат в доверенные корневые сертификаты вашей системы."
