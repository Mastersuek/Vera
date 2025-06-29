#!/bin/bash

# Проверяем, запущены ли контейнеры
if ! docker ps | grep -q vera-app; then
    echo "Запускаем контейнеры Vera..."
    cd /home/uss/Vera
    docker compose up -d
    echo "Контейнеры запущены"
else
    echo "Контейнеры уже запущены"
fi
