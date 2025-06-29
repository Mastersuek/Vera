// Класс для управления диалоговым окном отладки
class DebugWindow {
    constructor() {
        this.modal = document.getElementById('debug-modal');
        this.logContainer = document.getElementById('debug-log');
        this.runTestsBtn = document.getElementById('run-tests');
        this.clearLogBtn = document.getElementById('clear-log');
        this.closeBtn = document.querySelector('.close-modal');

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        this.runTestsBtn.addEventListener('click', () => this.runTests());
        this.clearLogBtn.addEventListener('click', () => this.clearLog());
        this.closeBtn.addEventListener('click', () => this.close());
        
        // Добавляем кнопку просмотра истории
        const viewHistoryBtn = document.createElement('button');
        viewHistoryBtn.className = 'btn-secondary';
        viewHistoryBtn.textContent = 'История тестов';
        viewHistoryBtn.addEventListener('click', () => this.showTestHistory());
        this.debugActions.appendChild(viewHistoryBtn);

        document.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.close();
            }
        });
    }

    // Показ истории тестов
    showTestHistory() {
        this.addLogEntry('Просмотр истории тестов...', 'info');
        
        try {
            const testHistory = JSON.parse(localStorage.getItem('testHistory') || '[]');
            if (testHistory.length === 0) {
                this.addLogEntry('История тестов пуста', 'info');
                return;
            }

            this.addLogEntry('История тестов:', 'info');
            testHistory.forEach((test, index) => {
                const status = test.status === 'error' ? '❌' : test.status === 'warning' ? '⚠️' : '✅';
                this.addLogEntry(`
                    Тест ${index + 1} (${new Date(test.timestamp).toLocaleString()}):
                    Статус: ${status}
                    Ошибок: ${test.errors}
                    Предупреждений: ${test.warnings}
                    Метрики:
                    - CPU: ${test.metrics.cpu}%
                    - Память: ${test.metrics.memory}%
                    - Диск: ${test.metrics.disk}%
                    - Время отклика: ${test.metrics.responseTime}мс
                    - Уровень ошибок: ${test.metrics.errorRate*100}%
                `, test.status);
            });
        } catch (error) {
            this.addLogEntry(`Ошибка при просмотре истории: ${error.message}`, 'error');
        }
    }

    show() {
        this.modal.style.display = 'block';
        document.body.style.overflow = 'hidden';
    }

    close() {
        this.modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    addLogEntry(message, type = 'info') {
        const entry = document.createElement('div');
        entry.className = `log-entry log-${type}`;
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        this.logContainer.appendChild(entry);
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
    }

    clearLog() {
        this.logContainer.innerHTML = '';
    }

    async runTests() {
        this.addLogEntry('Запуск тестов системы...', 'info');

        try {
            // Проверка доступности API
            this.addLogEntry('Проверка доступности API...', 'info');
            const healthCheck = await api.getHealth();
            if (healthCheck.status === 'ok') {
                this.addLogEntry('API доступен и работает корректно', 'success');
            } else {
                this.addLogEntry('API недоступен или работает некорректно', 'error');
                return;
            }

            // Проверка системных ресурсов
            this.addLogEntry('Проверка системных ресурсов...', 'info');
            const systemStatus = await api.getSystemStatus();
            
            // Проверка загрузки CPU
            if (systemStatus.cpu.load > 80) {
                this.addLogEntry(`Предупреждение: Высокая загрузка CPU (${systemStatus.cpu.load}%)`, 'warning');
            } else {
                this.addLogEntry(`CPU загрузка: ${systemStatus.cpu.load}%`, 'info');
            }

            // Проверка памяти
            if (systemStatus.memory.usage > 80) {
                this.addLogEntry(`Предупреждение: Высокое использование памяти (${systemStatus.memory.usage}%)`, 'warning');
            } else {
                this.addLogEntry(`Использование памяти: ${systemStatus.memory.usage}%`, 'info');
            }

            // Проверка дискового пространства
            if (systemStatus.disk.free < 10) {
                this.addLogEntry(`Предупреждение: Низкое свободное пространство на диске (${systemStatus.disk.free}%)`, 'warning');
            } else {
                this.addLogEntry(`Свободное пространство: ${systemStatus.disk.free}%`, 'info');
            }

            // Проверка состояния сервисов
            this.addLogEntry('Проверка состояния сервисов...', 'info');
            const servicesStatus = await api.getServicesStatus();
            
            servicesStatus.forEach(service => {
                if (service.status === 'running') {
                    this.addLogEntry(`Сервис ${service.name} работает корректно`, 'success');
                } else {
                    this.addLogEntry(`Сервис ${service.name} не работает (${service.status})`, 'error');
                }
            });

            // Проверка интеграций
            this.addLogEntry('Проверка интеграций...', 'info');
            const integrationsStatus = await api.getIntegrationsStatus();
            
            integrationsStatus.forEach(integration => {
                if (integration.status === 'connected') {
                    this.addLogEntry(`Интеграция ${integration.name} подключена`, 'success');
                } else {
                    this.addLogEntry(`Интеграция ${integration.name} не подключена (${integration.status})`, 'error');
                }
            });

            // Проверка безопасности
            this.addLogEntry('Проверка безопасности...', 'info');
            const securityStatus = await api.getSecurityStatus();
            
            if (securityStatus.updatesAvailable) {
                this.addLogEntry(`Доступны обновления безопасности: ${securityStatus.updatesAvailable}`, 'warning');
            }

            if (securityStatus.vulnerabilities) {
                this.addLogEntry(`Обнаружены уязвимости: ${securityStatus.vulnerabilities.length}`, 'error');
            }

            // Проверка производительности
            this.addLogEntry('Проверка производительности...', 'info');
            const performanceMetrics = await api.getPerformanceMetrics();
            
            if (performanceMetrics.responseTime > 500) {
                this.addLogEntry(`Предупреждение: Высокое время отклика (${performanceMetrics.responseTime}мс)`, 'warning');
            }

            if (performanceMetrics.errorRate > 0.01) {
                this.addLogEntry(`Предупреждение: Высокий уровень ошибок (${performanceMetrics.errorRate*100}%)`, 'warning');
            }

            // Итоговый статус
            const errors = document.querySelectorAll('.log-error').length;
            const warnings = document.querySelectorAll('.log-warning').length;
            
            let finalStatus;
            if (errors > 0) {
                finalStatus = 'error';
                this.addLogEntry(`Тестирование завершено с ошибками: ${errors} ошибок, ${warnings} предупреждений`, 'error');
            } else if (warnings > 0) {
                finalStatus = 'warning';
                this.addLogEntry(`Тестирование завершено с предупреждениями: ${warnings} предупреждений`, 'warning');
            } else {
                finalStatus = 'success';
                this.addLogEntry('Тестирование успешно завершено. Система готова к работе', 'success');
            }

            // Сохраняем результаты теста
            this.saveTestResults({
                timestamp: new Date().toISOString(),
                status: finalStatus,
                errors: errors,
                warnings: warnings,
                metrics: {
                    cpu: systemStatus.cpu.load,
                    memory: systemStatus.memory.usage,
                    disk: systemStatus.disk.free,
                    responseTime: performanceMetrics.responseTime,
                    errorRate: performanceMetrics.errorRate
                }
            });

        } catch (error) {
            this.addLogEntry(`Ошибка при выполнении тестов: ${error.message}`, 'error');
        }
    }

    // Сохранение результатов теста
    saveTestResults(results) {
        try {
            const testHistory = JSON.parse(localStorage.getItem('testHistory') || '[]');
            testHistory.push(results);
            localStorage.setItem('testHistory', JSON.stringify(testHistory));
            this.addLogEntry('Результаты теста сохранены в историю', 'info');
        } catch (error) {
            this.addLogEntry(`Ошибка при сохранении результатов: ${error.message}`, 'error');
        }
    }
}

// Инициализация диалогового окна
const debugWindow = new DebugWindow();

// Добавляем кнопку отладки в сайдбар
document.querySelector('.nav-menu').insertAdjacentHTML('beforeend', `
    <a href="#" onclick="debugWindow.show()" class="debug-link">
        <i class="icon-debug"></i> Отладка
    </a>
`);
