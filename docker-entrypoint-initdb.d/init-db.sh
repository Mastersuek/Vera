#!/bin/bash

# Создаем суперпользователя postgres
psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" <<-EOSQL
    CREATE ROLE vera SUPERUSER LOGIN PASSWORD '${POSTGRES_PASSWORD}';
    CREATE DATABASE veradb;
    GRANT ALL PRIVILEGES ON DATABASE veradb TO vera;
EOSQL
