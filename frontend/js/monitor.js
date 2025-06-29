class SystemMonitor {
    constructor(canvasId, maxValue = 100) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.maxValue = maxValue;
        this.currentValue = 0;
        this.peakValue = 0;
        this.history = [];
        this.historyLength = 100;
        this.updateInterval = 1000; // 1 секунда
        this.colors = {
            line: '#2c3e50',
            peak: '#e74c3c',
            background: '#f8f9fa',
            grid: '#ddd'
        };
    }

    update(value) {
        // Обновляем текущее значение
        this.currentValue = Math.min(value, this.maxValue);
        
        // Обновляем пик
        this.peakValue = Math.max(this.peakValue, this.currentValue);
        
        // Добавляем значение в историю
        this.history.push(this.currentValue);
        if (this.history.length > this.historyLength) {
            this.history.shift();
        }
        
        // Обновляем отображение
        this.updateDisplay();
    }

    updateDisplay() {
        // Получаем размеры канваса
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        // Очищаем канвас
        this.ctx.clearRect(0, 0, width, height);
        
        // Рисуем сетку
        this.drawGrid(width, height);
        
        // Рисуем линию графика
        this.drawLineGraph(width, height);
        
        // Рисуем пик
        this.drawPeak(width, height);
    }

    drawGrid(width, height) {
        // Рисуем горизонтальные линии
        for (let i = 0; i <= this.maxValue; i += 20) {
            const y = height - (i / this.maxValue) * height;
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(width, y);
            this.ctx.strokeStyle = this.colors.grid;
            this.ctx.lineWidth = 1;
            this.ctx.stroke();
        }
    }

    drawLineGraph(width, height) {
        if (this.history.length < 2) return;
        
        this.ctx.beginPath();
        this.ctx.strokeStyle = this.colors.line;
        this.ctx.lineWidth = 2;
        
        // Начальная точка
        const startX = 0;
        const startY = height - (this.history[0] / this.maxValue) * height;
        this.ctx.moveTo(startX, startY);
        
        // Остальные точки
        for (let i = 1; i < this.history.length; i++) {
            const x = (i / (this.history.length - 1)) * width;
            const y = height - (this.history[i] / this.maxValue) * height;
            this.ctx.lineTo(x, y);
        }
        
        this.ctx.stroke();
    }

    drawPeak(width, height) {
        const peakY = height - (this.peakValue / this.maxValue) * height;
        this.ctx.beginPath();
        this.ctx.moveTo(0, peakY);
        this.ctx.lineTo(width, peakY);
        this.ctx.strokeStyle = this.colors.peak;
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
    }
}

// Инициализация мониторов
let cpuMonitor, memoryMonitor, diskMonitor;

function initMonitors() {
    cpuMonitor = new SystemMonitor('cpu-canvas');
    memoryMonitor = new SystemMonitor('memory-canvas');
    diskMonitor = new SystemMonitor('disk-canvas');
}

// Обновление мониторов
async function updateMonitors() {
    try {
        const metrics = await api.getSystemMetrics();
        
        // Обновляем значения
        cpuMonitor.update(metrics.cpu_usage || 0);
        memoryMonitor.update(metrics.memory_usage || 0);
        diskMonitor.update(metrics.disk_usage || 0);
        
        // Обновляем значения в UI
        document.getElementById('cpu-monitor').querySelector('.chart-value').textContent = `${metrics.cpu_usage || 0}%`;
        document.getElementById('memory-monitor').querySelector('.chart-value').textContent = `${metrics.memory_usage || 0}%`;
        document.getElementById('disk-monitor').querySelector('.chart-value').textContent = `${metrics.disk_usage || 0}%`;
        
        // Обновляем пиковые значения
        document.getElementById('cpu-monitor').querySelector('.chart-peak').textContent = `Пик: ${cpuMonitor.peakValue}%`;
        document.getElementById('memory-monitor').querySelector('.chart-peak').textContent = `Пик: ${memoryMonitor.peakValue}%`;
        document.getElementById('disk-monitor').querySelector('.chart-peak').textContent = `Пик: ${diskMonitor.peakValue}%`;
    } catch (error) {
        console.error('Ошибка при обновлении мониторов:', error);
    }
}

// Запуск обновления мониторов
function startMonitorUpdates() {
    initMonitors();
    updateMonitors();
    setInterval(updateMonitors, 1000); // Обновление каждую секунду
}
