#!/usr/bin/env python3
"""
Скрипт для настройки репозитория GitHub для интеграции с MCP.

Этот скрипт помогает настроить необходимые секреты и переменные
в репозитории GitHub для работы с Model Control Plane (MCP).
"""

import os
import sys
import json
import requests
from getpass import getpass
from typing import Dict, List, Optional

# Конфигурация по умолчанию
DEFAULT_CONFIG = {
    "secrets": [
        {"name": "MCP_API_KEY", "description": "API ключ для доступа к MCP", "required": True},
        {"name": "DOCKERHUB_TOKEN", "description": "Токен доступа к Docker Hub", "required": True},
        {"name": "DOCKERHUB_USERNAME", "description": "Имя пользователя Docker Hub", "required": True},
        {"name": "SSH_PRIVATE_KEY", "description": "Приватный ключ для доступа к серверам", "required": False},
        {"name": "DB_PASSWORD", "description": "Пароль базы данных", "required": True},
        {"name": "SLACK_WEBHOOK_URL", "description": "URL вебхука Slack для уведомлений", "required": False}
    ],
    "variables": [
        {"name": "ENVIRONMENT", "value": "dev", "description": "Окружение (dev/stage/prod)"},
        {"name": "DOCKER_IMAGE", "value": "vera/vera-core", "description": "Имя Docker-образа"},
        {"name": "MCP_API_URL", "value": "https://api.vera.example.com", "description": "Базовый URL MCP API"},
        {"name": "MAX_WORKERS", "value": "4", "description": "Максимальное количество воркеров"}
    ]
}

class GitHubConfigurator:
    def __init__(self, token: str, owner: str, repo: str):
        """Инициализация конфигуратора GitHub.
        
        Args:
            token: Персональный токен доступа GitHub с правами repo
            owner: Владелец репозитория
            repo: Имя репозитория
        """
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def _make_request(self, method: str, endpoint: str, data: Optional[dict] = None) -> dict:
        """Выполнить HTTP-запрос к GitHub API."""
        url = f"{self.base_url}{endpoint}"
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            json=data,
            timeout=30
        )
        
        try:
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при выполнении запроса к {url}: {e}")
            if response.content:
                print(f"Ответ сервера: {response.text}")
            sys.exit(1)

    def get_secret(self, secret_name: str) -> bool:
        """Проверить существование секрета."""
        endpoint = f"/actions/secrets/{secret_name}"
        response = self._make_request("GET", endpoint)
        return bool(response and 'name' in response)

    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Установить секрет."""
        from base64 import b64encode
        from nacl import encoding, public
        
        # Получить ключ шифрования
        key_data = self._make_request("GET", "/actions/secrets/public-key")
        public_key = public.PublicKey(key_data['key'].encode('utf-8'), encoding.Base64Encoder())
        
        # Зашифровать значение
        sealed_box = public.SealedBox(public_key)
        encrypted_value = sealed_box.encrypt(secret_value.encode('utf-8'))
        encrypted_value_b64 = b64encode(encrypted_value).decode('utf-8')
        
        # Установить секрет
        data = {
            "encrypted_value": encrypted_value_b64,
            "key_id": key_data['key_id']
        }
        
        response = self._make_request(
            "PUT", 
            f"/actions/secrets/{secret_name}",
            data
        )
        
        return response == {}

    def set_variable(self, variable_name: str, value: str) -> bool:
        """Установить переменную."""
        data = {
            "name": variable_name,
            "value": value
        }
        
        # Проверить существование переменной
        variables = self._make_request("GET", "/actions/variables")
        existing_var = next((v for v in variables.get('variables', []) 
                          if v['name'] == variable_name), None)
        
        if existing_var:
            # Обновить существующую переменную
            response = self._make_request(
                "PATCH",
                f"/actions/variables/{variable_name}",
                data
            )
        else:
            # Создать новую переменную
            response = self._make_request(
                "POST",
                "/actions/variables",
                data
            )
        
        return 'name' in response and response['name'] == variable_name

def get_input(prompt: str, default: str = "", required: bool = True) -> str:
    """Получить ввод от пользователя с подсказкой."""
    while True:
        value = input(f"{prompt} {f'[{default}]' if default else ''}: ").strip() or default
        if required and not value:
            print("Это поле обязательно для заполнения.")
            continue
        return value

def configure_secrets(configurator: GitHubConfigurator, secrets_config: List[dict]):
    """Настроить секреты репозитория."""
    print("\n=== Настройка секретов ===")
    for secret in secrets_config:
        name = secret['name']
        description = secret.get('description', '')
        required = secret.get('required', False)
        
        if configurator.get_secret(name):
            print(f"\nСекрет '{name}' уже существует. Пропускаем...")
            continue
            
        print(f"\n{description}")
        print(f"Имя: {name} (Обязательный: {'Да' if required else 'Нет'})")
        
        if not required:
            if input("Пропустить? (y/n): ").lower() == 'y':
                continue
                
        value = getpass(f"Введите значение для {name}: ")
        if configurator.set_secret(name, value):
            print(f"✅ Секрет '{name}' успешно установлен")
        else:
            print(f"❌ Ошибка при установке секрета '{name}'")  

def configure_variables(configurator: GitHubConfigurator, variables_config: List[dict]):
    """Настроить переменные репозитория."""
    print("\n=== Настройка переменных ===")
    for var in variables_config:
        name = var['name']
        default_value = var.get('value', '')
        description = var.get('description', '')
        
        print(f"\n{description}")
        print(f"Имя: {name}")
        print(f"Значение по умолчанию: {default_value}")
        
        value = input(f"Введите значение для {name} (нажмите Enter для значения по умолчанию): ").strip() or default_value
        if configurator.set_variable(name, value):
            print(f"✅ Переменная '{name}' успешно установлена")
        else:
            print(f"❌ Ошибка при установке переменной '{name}'")  

def main():
    """Основная функция настройки репозитория."""
    print("=== Настройка репозитория GitHub для MCP ===\n")
    
    # Получить данные от пользователя
    token = getpass("Введите персональный токен доступа GitHub (с правами repo): ")
    owner = get_input("Введите владельца репозитория:", "Mastersuek")
    repo = get_input("Введите имя репозитория:", "Vera")
    
    # Инициализировать конфигуратор
    try:
        configurator = GitHubConfigurator(token, owner, repo)
        print("\n✅ Успешное подключение к репозиторию")
    except Exception as e:
        print(f"❌ Ошибка при подключении к репозиторию: {e}")
        sys.exit(1)
    
    # Настроить секреты
    configure_secrets(configurator, DEFAULT_CONFIG["secrets"])
    
    # Настроить переменные
    configure_variables(configurator, DEFAULT_CONFIG["variables"])
    
    print("\n=== Настройка завершена успешно! ===")
    print("\nДалее необходимо:")
    print("1. Настроить вебхуки в настройках репозитория")
    print("2. Проверить настройки защиты веток")
    print("3. Настроить окружения (если требуется)")
    print("\nПодробнее в документации: docs/MCP_CONFIGURATION.md")

if __name__ == "__main__":
    main()
