#!/bin/bash

# Создаем виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# Устанавливаем pip
python3 -m pip install --upgrade pip

# Устанавливаем зависимости
pip install docker python-dotenv aiohttp asyncio pytest

# Устанавливаем uv
pip install uv

# Проверяем установку
python3 -c "import docker; print('Docker module installed successfully')"
python3 -c "import uv; print('UV installed successfully')"
