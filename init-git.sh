#!/bin/bash
# Скрипт для инициализации Git-репозитория и настройки удаленного репозитория

set -euo pipefail

# Проверяем наличие .gitignore
if [ ! -f ".gitignore" ]; then
    echo "Ошибка: Файл .gitignore не найден"
    exit 1
fi

# Инициализируем Git-репозиторий, если он еще не инициализирован
if [ ! -d ".git" ]; then
    echo "Инициализация Git-репозитория..."
    git init
    
    # Добавляем все файлы в индекс
    echo "Добавление файлов в индекс..."
    git add .
    
    # Создаем первый коммит
    echo "Создание начального коммита..."
    git commit -m "Initial commit"
    
    echo "\n✅ Git-репозиторий успешно инициализирован"
else
    echo "Git-репозиторий уже инициализирован"
fi

# Запрашиваем URL удаленного репозитория
read -p "Хотите добавить удаленный репозиторий? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Введите URL удаленного репозитория: " remote_url
    
    # Проверяем, существует ли уже удаленный репозиторий
    if ! git remote | grep -q "origin"; then
        git remote add origin "$remote_url"
        echo "Удаленный репозиторий добавлен как origin"
    else
        read -p "Удаленный репозиторий уже существует. Хотите обновить URL? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git remote set-url origin "$remote_url"
            echo "URL удаленного репозитория обновлен"
        fi
    fi
    
    # Предлагаем отправить изменения в удаленный репозиторий
    read -p "Хотите отправить изменения в удаленный репозиторий? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push -u origin main
    fi
fi

echo "\n✅ Готово! Проект подготовлен для работы с Git"
