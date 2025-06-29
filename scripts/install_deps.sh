#!/bin/bash

# Установка pip если его нет
if ! command -v pip &> /dev/null; then
    echo "Installing pip..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py
    rm get-pip.py
fi

# Установка зависимостей
pip install -r requirements-automation.txt
