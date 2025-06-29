// Конфигурация API
const API_BASE_URL = 'http://localhost:5000';

// Функции для работы с API
const api = {
    init: () => {
        // Проверяем соединение с сервером
        fetch(`${API_BASE_URL}/api/v1/health`).then(response => {
            if (!response.ok) {
                console.error('Не удалось подключиться к API');
            }
        });
    },

    getHealth: async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/health`);
            const data = await response.json();
            
            // Преобразуем статус в формат для светофора
            switch (data.status) {
                case 'error':
                    return { status: 'error', message: 'Система не работает' };
                case 'warning':
                case 'calculating':
                    return { status: 'warning', message: 'Выполняются вычисления' };
                case 'ok':
                case 'ready':
                    return { status: 'ready', message: 'Система готова к работе' };
                default:
                    return { status: 'error', message: 'Неизвестный статус' };
            }
        } catch (error) {
            console.error('Ошибка при получении статуса:', error);
            return { status: 'error', message: 'Не удалось получить статус' };
        }
    },

    getSystemMetrics: async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/metrics`);
            return await response.json();
        } catch (error) {
            console.error('Ошибка при получении метрик:', error);
            return {};
        }
    },

    getEvents: async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/events`);
            return await response.json();
        } catch (error) {
            console.error('Ошибка при получении событий:', error);
            return [];
        }
    },

    uploadFile: async (file) => {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/upload`, {
                method: 'POST',
                body: formData,
                headers: {
                    'Accept': 'application/json'
                }
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || 'Ошибка загрузки файла');
            }
            return data;
        } catch (error) {
            console.error('Ошибка при загрузке файла:', error);
            throw error;
        }
    },

    // Задачи
    getTasks: async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/tasks`);
            return await response.json();
        } catch (error) {
            console.error('Ошибка при получении задач:', error);
            throw error;
        }
    },

    createTask: async (taskData) => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/tasks`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(taskData)
            });
            return await response.json();
        } catch (error) {
            console.error('Ошибка при создании задачи:', error);
            throw error;
        }
    },

    // Семантический анализ
    analyzeText: async (text) => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/semantic/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text })
            });
            return await response.json();
        } catch (error) {
            console.error('Ошибка при анализе текста:', error);
            throw error;
        }
    },

    // Мониторинг
    getSystemLogs: async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/logs`);
            return await response.json();
        } catch (error) {
            console.error('Ошибка при получении логов:', error);
            throw error;
        }
    },

    // Администрирование
    getSystemSettings: async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/settings`);
            return await response.json();
        } catch (error) {
            console.error('Ошибка при получении настроек:', error);
            throw error;
        }
    },

    updateSetting: async (key, value) => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/settings/${key}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ value })
            });
            return await response.json();
        } catch (error) {
            console.error('Ошибка при обновлении настройки:', error);
            throw error;
        }
    },

    getUsers: async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/users`);
            return await response.json();
        } catch (error) {
            console.error('Ошибка при получении пользователей:', error);
            throw error;
        }
    },

    updateUser: async (userId, userData) => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/users/${userId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(userData)
            });
            return await response.json();
        } catch (error) {
            console.error('Ошибка при обновлении пользователя:', error);
            throw error;
        }
    },

    deleteUser: async (userId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/users/${userId}`, {
                method: 'DELETE'
            });
            return await response.json();
        } catch (error) {
            console.error('Ошибка при удалении пользователя:', error);
            throw error;
        }
    }
};

// Обновление статуса системы
async function updateSystemStatus() {
    try {
        const status = await api.getHealth();
        const errorLight = document.getElementById('error-light');
        const warningLight = document.getElementById('warning-light');
        const readyLight = document.getElementById('ready-light');

        // Сначала убираем активность со всех ламп
        errorLight.classList.remove('active');
        warningLight.classList.remove('active');
        readyLight.classList.remove('active');

        // Определяем текущий статус
        if (status.status === 'error') {
            errorLight.classList.add('active');
        } else if (status.status === 'warning' || status.status === 'calculating') {
            warningLight.classList.add('active');
        } else if (status.status === 'ok' || status.status === 'ready') {
            readyLight.classList.add('active');
        }

    } catch (error) {
        console.error('Ошибка при получении статуса:', error);
        // При ошибке показываем красный свет
        const errorLight = document.getElementById('error-light');
        errorLight.classList.add('active');
    }
}

// Обновление метрик
async function updateMetrics() {
    const metrics = await api.getSystemMetrics();
    
    // Обновление карточек статистики
    document.querySelector('.stat-number[data-metric="cpu"]')?.textContent = `${metrics.cpu_usage || 0}%`;
    document.querySelector('.stat-number[data-metric="memory"]')?.textContent = `${metrics.memory_usage || 0}%`;
    document.querySelector('.stat-number[data-metric="disk"]')?.textContent = `${metrics.disk_usage || 0}%`;
    document.querySelector('.stat-number[data-metric="tasks"]')?.textContent = metrics.active_tasks || 0;
}

// Обновление событий
async function updateEvents() {
    const events = await api.getEvents();
    const eventsList = document.getElementById('events-list');
    
    eventsList.innerHTML = events.map(event => `
        <div class="event-item">
            <span class="event-time">${new Date(event.timestamp).toLocaleTimeString()}</span>
            <div class="event-content">
                <span class="event-type">${event.type}</span>
                <span class="event-message">${event.message}</span>
            </div>
        </div>
    `).join('');
}

// Инициализация обновлений
function initDashboardUpdates() {
    updateSystemStatus();
    updateMetrics();
    updateEvents();

    // Периодическое обновление
    setInterval(updateSystemStatus, 5000);
    setInterval(updateMetrics, 10000);
    setInterval(updateEvents, 30000);
}
