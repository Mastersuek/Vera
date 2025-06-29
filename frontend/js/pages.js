class PagesManager {
    constructor() {
        this.currentPage = 'dashboard';
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Обработка навигации
        document.querySelectorAll('.nav-menu a').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const pageId = link.getAttribute('href').substring(1);
                this.switchPage(pageId);
            });
        });

        // Инициализация страниц
        this.initPages();
    }

    switchPage(pageId) {
        // Предотвращаем перезагрузку страницы
        event.preventDefault();
        
        // Обновляем активную вкладку в навигации
        const links = document.querySelectorAll('.nav-menu a');
        links.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href').substring(1) === pageId) {
                link.classList.add('active');
            }
        });

        // Обновляем заголовок страницы
        document.querySelector('.page-title').textContent = 
            pageId.charAt(0).toUpperCase() + pageId.slice(1);

        // Показываем/скрываем страницы
        const pages = document.querySelectorAll('.page');
        pages.forEach(page => {
            page.classList.remove('active');
            if (page.id === pageId) {
                page.classList.add('active');
                // Инициализируем контент для активной страницы
                this.initPageContent(pageId);
            }
        });

        // Обновляем текущую страницу
        this.currentPage = pageId;
    }

    initPageContent(pageId) {
        switch (pageId) {
            case 'dashboard':
                // Инициализация монитора и загрузки файлов
                if (!document.getElementById('cpu-canvas').getContext('2d').hasChart) {
                    startMonitorUpdates();
                }
                break;
            case 'tasks':
                // Инициализация списка задач
                this.initTasksPage();
                break;
            case 'semantic':
                // Инициализация семантического анализа
                this.initSemanticPage();
                break;
            case 'monitoring':
                // Инициализация мониторинга
                this.initMonitoringPage();
                break;
            case 'admin':
                // Инициализация администрирования
                this.initAdminPage();
                break;
        }
    }

    async initPages() {
        // Инициализация страницы задач
        if (document.getElementById('tasks')) {
            await this.initTasksPage();
        }

        // Инициализация страницы семантики
        if (document.getElementById('semantic')) {
            await this.initSemanticPage();
        }

        // Инициализация страницы мониторинга
        if (document.getElementById('monitoring')) {
            await this.initMonitoringPage();
        }

        // Инициализация страницы администрирования
        if (document.getElementById('admin')) {
            await this.initAdminPage();
        }
    }

    async initTasksPage() {
        const tasksList = document.getElementById('tasks-list');
        try {
            const tasks = await api.getTasks();
            this.renderTasks(tasksList, tasks);
        } catch (error) {
            console.error('Ошибка при загрузке задач:', error);
        }
    }

    async initSemanticPage() {
        const analyzeButton = document.getElementById('analyze-text');
        analyzeButton.addEventListener('click', async () => {
            const text = document.getElementById('semantic-text').value;
            try {
                const analysis = await api.analyzeText(text);
                this.renderSemanticResults(analysis);
            } catch (error) {
                console.error('Ошибка при анализе текста:', error);
            }
        });
    }

    async initMonitoringPage() {
        const logsContainer = document.getElementById('logs-container');
        try {
            const logs = await api.getSystemLogs();
            this.renderLogs(logsContainer, logs);
        } catch (error) {
            console.error('Ошибка при загрузке логов:', error);
        }
    }

    async initAdminPage() {
        try {
            const settings = await api.getSystemSettings();
            this.renderAdminSettings(settings);
            
            const users = await api.getUsers();
            this.renderUserManagement(users);
        } catch (error) {
            console.error('Ошибка при загрузке настроек:', error);
        }
    }

    renderTasks(container, tasks) {
        container.innerHTML = tasks.map(task => `
            <div class="task-item ${task.status}">
                <div class="task-info">
                    <h3>${task.name}</h3>
                    <p>${task.description}</p>
                </div>
                <div class="task-status">
                    <span class="status-dot ${task.status}"></span>
                    <span>${task.status}</span>
                </div>
            </div>
        `).join('');
    }

    renderSemanticResults(analysis) {
        const visualization = document.querySelector('.semantic-visualization');
        const metrics = document.querySelector('.semantic-metrics');

        // Очищаем предыдущие результаты
        visualization.innerHTML = '';
        metrics.innerHTML = '';

        // Добавляем визуализацию
        visualization.innerHTML = `
            <div class="visualization-chart">
                <!-- Визуализация будет добавлена здесь -->
            </div>
        `;

        // Добавляем метрики
        metrics.innerHTML = `
            <div class="metrics-list">
                ${Object.entries(analysis.metrics).map(([key, value]) => `
                    <div class="metric-item">
                        <span class="metric-name">${key}</span>
                        <span class="metric-value">${value}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    renderLogs(container, logs) {
        container.innerHTML = logs.map(log => `
            <div class="log-item ${log.level}">
                <div class="log-time">${log.timestamp}</div>
                <div class="log-message">${log.message}</div>
                <div class="log-level">${log.level}</div>
            </div>
        `).join('');
    }

    renderAdminSettings(settings) {
        const settingsContainer = document.querySelector('.admin-settings');
        settingsContainer.innerHTML = `
            <div class="settings-list">
                ${Object.entries(settings).map(([key, value]) => `
                    <div class="setting-item">
                        <label>${key}</label>
                        <input type="text" value="${value}" data-setting="${key}">
                    </div>
                `).join('')}
            </div>
        `;

        // Добавляем обработчики изменений
        settingsContainer.querySelectorAll('input').forEach(input => {
            input.addEventListener('change', async () => {
                try {
                    await api.updateSetting(input.dataset.setting, input.value);
                } catch (error) {
                    console.error('Ошибка при обновлении настройки:', error);
                }
            });
        });
    }

    renderUserManagement(users) {
        const usersContainer = document.querySelector('.user-management');
        usersContainer.innerHTML = `
            <div class="users-list">
                ${users.map(user => `
                    <div class="user-item">
                        <div class="user-info">
                            <h3>${user.name}</h3>
                            <p>${user.role}</p>
                        </div>
                        <div class="user-actions">
                            <button class="edit-user">Изменить</button>
                            <button class="delete-user">Удалить</button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        // Добавляем обработчики действий с пользователями
        usersContainer.querySelectorAll('.edit-user').forEach(button => {
            button.addEventListener('click', () => {
                // Реализация редактирования пользователя
            });
        });

        usersContainer.querySelectorAll('.delete-user').forEach(button => {
            button.addEventListener('click', () => {
                // Реализация удаления пользователя
            });
        });
    }
}

// Инициализация менеджера страниц при загрузке документа
document.addEventListener('DOMContentLoaded', () => {
    new PagesManager();
});
