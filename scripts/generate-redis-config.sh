#!/bin/bash

# Получаем значение переменной окружения
REDIS_PASSWORD=$(grep -Po '(?<=REDIS_PASSWORD=)[^\n]+' .env)

# Генерируем конфигурацию
CONFIG="{
  \"redis\": {
    \"servers\": [
      {
        \"host\": \"redis\",
        \"port\": 6379,
        \"db\": 0,
        \"name\": \"Redis\",
        \"password\": \"${REDIS_PASSWORD}\"
      }
    ]
  },
  \"server\": {
    \"port\": 8081
  }
}"

echo "$CONFIG" > config/redis-commander.json
