class FileUploader {
    constructor() {
        this.uploadArea = document.getElementById('upload-area');
        this.fileInput = document.getElementById('file-input');
        this.uploadedFiles = document.getElementById('uploaded-files');
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Обработка перетаскивания файлов
        this.uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        this.uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        
        // Обработка выбора файлов
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // Клик по области загрузки
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
    }

    handleDragOver(event) {
        event.preventDefault();
        this.uploadArea.classList.add('active');
    }

    handleDragLeave(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('active');
    }

    handleDrop(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('active');
        const files = event.dataTransfer.files;
        this.processFiles(files);
    }

    handleFileSelect(event) {
        const files = event.target.files;
        this.processFiles(files);
    }

    async processFiles(files) {
        for (const file of files) {
            if (!this.isValidFileType(file)) continue;
            
            const fileItem = this.createFileItem(file);
            this.uploadedFiles.appendChild(fileItem);
            
            try {
                await this.uploadFile(file, fileItem);
            } catch (error) {
                this.showError(fileItem, error.message);
            }
        }
    }

    isValidFileType(file) {
        const allowedTypes = ['text/plain', 'application/pdf', 'image/jpeg', 'image/png', 
                            'audio/mpeg', 'audio/wav', 'video/mp4'];
        return allowedTypes.includes(file.type);
    }

    createFileItem(file) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        
        const icon = this.getFileIcon(file);
        const fileInfo = this.createFileInfo(file);
        const progressBar = this.createProgressBar();
        
        fileItem.appendChild(icon);
        fileItem.appendChild(fileInfo);
        fileItem.appendChild(progressBar);
        
        return fileItem;
    }

    getFileIcon(file) {
        const icon = document.createElement('div');
        icon.className = 'file-icon';
        
        let type = 'file';
        if (file.type.startsWith('image')) type = 'image';
        else if (file.type.startsWith('audio')) type = 'audio';
        else if (file.type.startsWith('video')) type = 'video';
        else if (file.type === 'application/pdf') type = 'pdf';
        
        icon.innerHTML = `<i class="icon-${type}"></i>`;
        return icon;
    }

    createFileInfo(file) {
        const fileInfo = document.createElement('div');
        fileInfo.className = 'file-info';
        
        const fileName = document.createElement('div');
        fileName.className = 'file-name';
        fileName.textContent = file.name;
        
        const fileSize = document.createElement('div');
        fileSize.className = 'file-size';
        fileSize.textContent = this.formatFileSize(file.size);
        
        fileInfo.appendChild(fileName);
        fileInfo.appendChild(fileSize);
        return fileInfo;
    }

    createProgressBar() {
        const progressBar = document.createElement('div');
        progressBar.className = 'file-progress';
        
        const bar = document.createElement('div');
        bar.className = 'progress-bar';
        progressBar.appendChild(bar);
        
        return progressBar;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async uploadFile(file, fileItem) {
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/upload`, {
                method: 'POST',
                body: formData,
            });
            
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || 'Ошибка загрузки файла');
            }
            
            // Обновляем прогресс до 100%
            const progressBar = fileItem.querySelector('.progress-bar');
            progressBar.style.width = '100%';
            
            // Добавляем информацию о успешной загрузке
            const status = document.createElement('div');
            status.className = 'upload-status';
            status.textContent = '✓ Загружен успешно';
            fileItem.appendChild(status);
            
        } catch (error) {
            throw error;
        }
    }

    showError(fileItem, message) {
        const progressBar = fileItem.querySelector('.progress-bar');
        progressBar.style.width = '100%';
        progressBar.style.background = '#e74c3c';
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'upload-error';
        errorDiv.textContent = `✗ Ошибка: ${message}`;
        fileItem.appendChild(errorDiv);
    }
}

// Инициализация загрузчика файлов при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new FileUploader();
});
