#!/bin/bash

# Функция для мониторинга контейнеров
display_container_stats() {
    echo "\n=== Container Statistics ==="
    docker stats --no-stream
    echo "\n=== Redis Stats ==="
    docker exec vera-redis redis-cli info | grep -E "used_memory|connected_clients|keyspace_hits|keyspace_misses"
    echo "\n=== PostgreSQL Stats ==="
    docker exec vera-postgres psql -U postgres -c "SELECT pid, usename, state, query FROM pg_stat_activity;"
    echo "\n=== Qdrant Stats ==="
    curl -s http://localhost:6333/health | jq '.'
}

# Основной цикл мониторинга
while true; do
    clear
    display_container_stats
    echo "\nPress Ctrl+C to exit..."
    sleep 10
done
