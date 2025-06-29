#!/bin/bash

# Функция для просмотра логов конкретного сервиса
show_service_logs() {
    echo "=== Logs for $1 ==="
    docker-compose logs $1
    echo "\n=== End of logs for $1 ===\n"
}

# Просмотр логов всех сервисов
show_all_logs() {
    echo "=== All Service Logs ==="
    docker-compose logs
    echo "\n=== End of all logs ===\n"
}

# Просмотр последних логов
show_recent_logs() {
    echo "=== Recent Logs ==="
    docker-compose logs --tail=100
    echo "\n=== End of recent logs ===\n"
}

# Основное меню
while true; do
    echo "\n=== Log Viewer Menu ==="
    echo "1. View all service logs"
    echo "2. View recent logs (last 100 lines)"
    echo "3. View logs for specific service"
    echo "4. Exit"
    echo -n "\nEnter your choice: "
    read choice

    case $choice in
        1) show_all_logs ;;
        2) show_recent_logs ;;
        3) 
            echo -n "Enter service name (app, postgres, redis, etc.): "
            read service_name
            show_service_logs $service_name
            ;;
        4) exit 0 ;;
        *) echo "Invalid choice! Please try again." ;;
    esac
done
