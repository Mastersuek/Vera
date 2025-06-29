# Фаза 1: Сборка и подготовка модели
FROM python:3.11-slim as builder

# Установка зависимостей и очистка кэша в одном слое
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка Python зависимостей в одном слое
RUN pip install --no-cache-dir \
    torch==2.1.0 \
    transformers==4.36.0 \
    safetensors==0.4.1 \
    grpcio-tools==1.64.1

# Создаем рабочую директорию с правильными правами
WORKDIR /app
RUN mkdir -p /app/model && chown -R 1000:1000 /app

# Копируем proto файлы
COPY proto/ ./proto/

# Скачиваем и оптимизируем модель
RUN python -c "from transformers import AutoModelForCausalLM, AutoTokenizer; import torch; model = AutoModelForCausalLM.from_pretrained('bigscience/bloom-560m', torch_dtype=torch.float16); tokenizer = AutoTokenizer.from_pretrained('bigscience/bloom-560m'); model.save_pretrained('/app/model'); tokenizer.save_pretrained('/app/model');"

# Генерация gRPC кода
RUN python -m grpc_tools.protoc \
    --python_out=/app \
    --grpc_python_out=/app \
    --proto_path=/app/proto \
    /app/proto/model.proto

# Фаза 2: Финальный образ
FROM python:3.11-slim

# Обновляем систему и устанавливаем минимальные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка Python зависимостей с оптимизациями
RUN pip install --no-cache-dir \
    torch==2.1.0 \
    transformers==4.36.0 \
    protobuf==4.25.2 \
    grpcio==1.64.1

# Создаем не-привилегированного пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Создаем рабочую директорию с правильными правами
WORKDIR /app
RUN mkdir -p /app/model && chown -R appuser:appuser /app

# Копируем файлы из builder
COPY --from=builder /app/model ./model
COPY --from=builder /app/model_pb2.py ./model_pb2.py
COPY --from=builder /app/model_pb2_grpc.py ./model_pb2_grpc.py

# Копируем сервисные файлы
COPY requirements.txt ./
COPY model.py ./
COPY service.py ./

# Копируем скрипты тестирования
COPY healthcheck.sh /usr/local/bin/healthcheck
COPY test.sh /usr/local/bin/test
RUN chmod +x /usr/local/bin/healthcheck /usr/local/bin/test

# Устанавливаем переменные окружения для безопасности
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_UID=1000 \
    APP_GID=1000 \
    APP_USER=appuser

# Установка SELinux контекста
LABEL security.selinux.type=container_file_t

# Установка метаданных
LABEL org.opencontainers.image.title="Vera LLM Model Service" \
      org.opencontainers.image.description="Service for running LLM model with gRPC interface" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Your Name <your@email.com>"

# Ограничения ресурсов
RUN echo "* soft nofile 10240" >> /etc/security/limits.conf \
    && echo "* hard nofile 10240" >> /etc/security/limits.conf

# Настройка healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/healthcheck

# Настройка статистики использования
VOLUME /var/log/app

# Экспонируем порты
EXPOSE 50051
EXPOSE 8000

# Переходим к не-привилегированному пользователю
USER appuser

# Запускаем сервис
CMD ["python", "service.py"]
