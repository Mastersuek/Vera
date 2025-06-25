#!/bin/bash

# Создание директорий, если они не существуют
mkdir -p nginx/ssl/private nginx/ssl/certs

echo "🔐 Генерация закрытого ключа..."
# Генерация закрытого ключа
openssl genrsa -out nginx/ssl/private/nginx-selfsigned.key 2048

echo "📝 Создание запроса на подпись сертификата..."
# Создание запроса на подпись сертификата (CSR)
openssl req -new -key nginx/ssl/private/nginx-selfsigned.key -out nginx/ssl/certs/nginx-selfsigned.csr \
    -subj "/C=RU/ST=Москва/L=Москва/O=Vera/CN=localhost"

echo "🔄 Генерация самоподписанного сертификата..."
# Генерация самоподписанного сертификата
openssl x509 -req -days 365 -in nginx/ssl/certs/nginx-selfsigned.csr \
    -signkey nginx/ssl/private/nginx-selfsigned.key -out nginx/ssl/certs/nginx-selfsigned.crt

# Установка правильных прав доступа
echo "🔒 Настройка прав доступа к файлам..."
chmod 600 nginx/ssl/private/nginx-selfsigned.key
chmod 644 nginx/ssl/certs/nginx-selfsigned.crt

echo "✅ SSL-сертификаты успешно сгенерированы в директории nginx/ssl/"
echo "ℹ️  Для использования в браузере может потребоваться добавить сертификат в доверенные корневые центры сертификации."
echo "   Файл сертификата: nginx/ssl/certs/nginx-selfsigned.crt"
