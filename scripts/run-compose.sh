#!/bin/bash

# Генерируем конфигурацию Redis Commander
./scripts/generate-redis-config.sh

# Запускаем docker-compose
docker-compose up -d
