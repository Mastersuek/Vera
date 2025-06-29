#!/bin/bash

# Генерация gRPC кода
python -m grpc_tools.protoc \
    --python_out=/app \
    --grpc_python_out=/app \
    --proto_path=/app/proto \
    /app/proto/model.proto
