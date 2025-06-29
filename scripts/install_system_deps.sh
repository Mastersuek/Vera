#!/bin/bash

# Обновляем список пакетов
sudo apt-get update

# Устанавливаем python3-pip
sudo apt-get install -y python3-pip python3-venv python3-dev build-essential

# Устанавливаем uv
pip3 install uv

# Проверяем установку
python3 -m pip list | grep -E "uv|pip"
