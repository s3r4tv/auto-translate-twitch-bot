const { ipcRenderer } = require('electron');

class TwitchBotApp {
    constructor() {
        this.currentPage = 'main';
        this.statusUpdateInterval = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkSettings();
        this.updateBotStatus();
        
        // Периодическое обновление статуса каждые 2 секунды
        this.statusUpdateInterval = setInterval(() => {
            this.updateBotStatus();
        }, 2000);
    }
    
    destroy() {
        if (this.statusUpdateInterval) {
            clearInterval(this.statusUpdateInterval);
            this.statusUpdateInterval = null;
        }
    }

    setupEventListeners() {
        // Navigation
        document.getElementById('settings-btn').addEventListener('click', () => this.showPage('settings'));
        document.getElementById('back-btn').addEventListener('click', () => this.showPage('main'));

        // Bot controls
        document.getElementById('start-bot').addEventListener('click', () => this.startBot());
        document.getElementById('stop-bot').addEventListener('click', () => this.stopBot());

        // Log controls
        document.getElementById('clear-log').addEventListener('click', () => this.clearLog());

        // Settings
        document.getElementById('save-settings').addEventListener('click', () => this.saveSettings());

        // About modal
        document.getElementById('about-btn').addEventListener('click', () => this.showAboutModal());
        document.getElementById('close-about-modal').addEventListener('click', () => this.hideAboutModal());
        
        // Close modal when clicking outside
        document.getElementById('about-modal').addEventListener('click', (e) => {
            if (e.target.id === 'about-modal') {
                this.hideAboutModal();
            }
        });

        // Handle external links
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('link') || e.target.classList.contains('about-link')) {
                e.preventDefault();
                const { shell } = require('electron');
                shell.openExternal(e.target.href);
            }
        });

        // Handle copy commands
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('copy-command')) {
                e.preventDefault();
                const textToCopy = e.target.getAttribute('data-copy');
                if (textToCopy) {
                    this.copyToClipboard(textToCopy);
                }
            }
        });

        // Bot log events
        ipcRenderer.on('bot-log', (event, message) => {
            this.addLogEntry(message);
        });
        
        // Bot stopped event
        ipcRenderer.on('bot-stopped', () => {
            this.addLogEntry('🛑 Бот остановлен', 'warning');
            this.updateStatusIndicator('stopped');
        });
        
        // Handle Escape key for modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideAboutModal();
            }
        });
    }

    showPage(pageName) {
        // Hide all pages
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });

        // Show target page
        document.getElementById(`${pageName}-page`).classList.add('active');
        this.currentPage = pageName;

        // Update header based on page
        if (pageName === 'settings') {
            document.querySelector('.header h1').textContent = 'Настройки';
            // Загружаем настройки при переходе на страницу настроек
            this.loadSettingsToForm();
        } else {
            document.querySelector('.header h1').innerHTML = 'Twitch Translate Bot';
        }
    }

    async checkSettings() {
        try {
            const result = await ipcRenderer.invoke('check-settings');
            
            if (result.exists) {
                this.addLogEntry('✅ Настройки найдены. Бот готов к запуску.', 'success');
                this.updateStatusIndicator('ready');
                // Загружаем данные в форму настроек
                await this.loadSettingsToForm();
            } else {
                this.addLogEntry('⚠️ Отсутствуют настройки. Перейдите в настройки для конфигурации.', 'warning');
                this.updateStatusIndicator('not-configured');
            }
        } catch (error) {
            this.addLogEntry(`❌ Ошибка проверки настроек: ${error.message}`, 'error');
        }
    }

    async loadSettingsToForm() {
        try {
            const settings = await ipcRenderer.invoke('load-settings');
            if (settings.success) {
                document.getElementById('access-token').value = settings.data.accessToken || '';
                document.getElementById('client-id').value = settings.data.clientId || '';
                document.getElementById('nickname').value = settings.data.nickname || '';
                document.getElementById('channel').value = settings.data.channel || '';
            }
        } catch (error) {
            console.error('Error loading settings to form:', error);
        }
    }

    async startBot() {
        const startBtn = document.getElementById('start-bot');
        const stopBtn = document.getElementById('stop-bot');

        // Сначала проверяем настройки
        const settingsCheck = await ipcRenderer.invoke('check-settings');
        if (!settingsCheck.exists) {
            this.addLogEntry('❌ Невозможно запустить бота: отсутствуют настройки!', 'error');
            this.addLogEntry('⚙️ Перейдите в настройки и заполните все поля.', 'warning');
            return;
        }

        startBtn.disabled = true;
        startBtn.innerHTML = '<div class="loading"></div> Запуск...';

        try {
            this.addLogEntry('🚀 Запуск бота...', 'info');
            const result = await ipcRenderer.invoke('start-bot');

            if (result.success) {
                this.addLogEntry('✅ Бот успешно запущен!', 'success');
                this.updateStatusIndicator('running');
                startBtn.disabled = true;
                stopBtn.disabled = false;
            } else {
                this.addLogEntry(`❌ Ошибка запуска бота: ${result.error}`, 'error');
                startBtn.disabled = false;
            }
        } catch (error) {
            this.addLogEntry(`❌ Ошибка запуска бота: ${error.message}`, 'error');
            startBtn.disabled = false;
        } finally {
            startBtn.innerHTML = '<i class="fas fa-play"></i> Запустить бота';
        }
    }

    async stopBot() {
        const startBtn = document.getElementById('start-bot');
        const stopBtn = document.getElementById('stop-bot');

        stopBtn.disabled = true;
        stopBtn.innerHTML = '<div class="loading"></div> Остановка...';

        try {
            this.addLogEntry('🔄 Остановка бота...', 'info');
            const result = await ipcRenderer.invoke('stop-bot');

            if (result.success) {
                this.addLogEntry('⏹️ Бот остановлен', 'success');
                this.updateStatusIndicator('stopped');
                startBtn.disabled = false;
                stopBtn.disabled = true;
            } else {
                this.addLogEntry(`❌ Ошибка остановки бота: ${result.error}`, 'error');
                stopBtn.disabled = false;
            }
        } catch (error) {
            this.addLogEntry(`❌ Ошибка остановки бота: ${error.message}`, 'error');
            stopBtn.disabled = false;
        } finally {
            stopBtn.innerHTML = '<i class="fas fa-stop"></i> Остановить бота';
        }
    }

    async saveSettings() {
        const saveBtn = document.getElementById('save-settings');
        const originalText = saveBtn.innerHTML;

        saveBtn.disabled = true;
        saveBtn.innerHTML = '<div class="loading"></div> Сохранение...';

        try {
            const settings = {
                accessToken: document.getElementById('access-token').value.trim(),
                clientId: document.getElementById('client-id').value.trim(),
                nickname: document.getElementById('nickname').value.trim(),
                channel: document.getElementById('channel').value.trim()
            };

            // Validation
            if (!settings.accessToken || !settings.clientId || !settings.nickname || !settings.channel) {
                this.showSettingsNotification('❌ Все поля должны быть заполнены', 'error');
                return;
            }

            const result = await ipcRenderer.invoke('save-settings', settings);

            if (result.success) {
                this.showSettingsNotification('✅ Настройки успешно сохранены', 'success');
                this.addLogEntry('✅ Настройки успешно сохранены', 'success');
                setTimeout(() => {
                    this.showPage('main');
                    this.checkSettings();
                }, 1500);
            } else {
                this.showSettingsNotification(`❌ Ошибка сохранения: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showSettingsNotification(`❌ Ошибка сохранения: ${error.message}`, 'error');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        }
    }

    addLogEntry(message, type = 'info') {
        const logContent = document.getElementById('log-content');
        const timestamp = new Date().toLocaleTimeString();
        
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        logEntry.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
        
        logContent.appendChild(logEntry);
        logContent.scrollTop = logContent.scrollHeight;

        // Limit log entries to prevent memory issues
        const entries = logContent.querySelectorAll('.log-entry');
        if (entries.length > 1000) {
            entries[0].remove();
        }
    }

    clearLog() {
        const logContent = document.getElementById('log-content');
        logContent.innerHTML = '';
        this.addLogEntry('🗑️ Лог очищен', 'info');
    }

    copyToClipboard(text) {
        const { clipboard } = require('electron');
        clipboard.writeText(text);
        
        // Показываем уведомление об успешном копировании
        this.showSettingsNotification(`📋 Скопировано: "${text}"`, 'success');
    }

    updateStatusIndicator(status) {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');

        statusDot.className = 'status-dot';
        statusText.textContent = 'Не запущен';

        switch (status) {
            case 'running':
                statusDot.classList.add('running');
                statusText.textContent = 'Запущен';
                break;
            case 'ready':
                statusText.textContent = 'Готов к запуску';
                break;
            case 'not-configured':
                statusText.textContent = 'Требуется настройка';
                break;
            case 'stopped':
                statusText.textContent = 'Остановлен';
                break;
            case 'error':
                statusDot.style.background = '#ff6b6b';
                statusText.textContent = 'Ошибка';
                break;
        }
    }

    async updateBotStatus() {
        try {
            const status = await ipcRenderer.invoke('get-bot-status');
            
            const startBtn = document.getElementById('start-bot');
            const stopBtn = document.getElementById('stop-bot');

            // Update buttons
            if (status.running) {
                startBtn.disabled = true;
                stopBtn.disabled = false;
                this.updateStatusIndicator('running');
            } else {
                startBtn.disabled = false;
                stopBtn.disabled = true;
                this.updateStatusIndicator('ready');
            }
            
            // Update GUI status display
            this.updateGUIStatus(status);
        } catch (error) {
            console.error('Error updating bot status:', error);
            // Fallback status update
            this.updateStatusIndicator('error');
        }
    }
    
    updateGUIStatus(status) {
        // Update bot state
        const botState = document.getElementById('bot-state');
        if (botState) {
            botState.textContent = status.running ? 'Запущен' : 'Остановлен';
            botState.style.color = status.running ? '#2ed573' : '#ff4757';
        }
        
        // Update auto users count
        const autoUsersCount = document.getElementById('auto-users-count');
        if (autoUsersCount) {
            autoUsersCount.textContent = status.autoTranslateUsers?.length || 0;
        }
        
        // Update cache size
        const cacheSize = document.getElementById('cache-size');
        if (cacheSize) {
            cacheSize.textContent = status.cacheSize || 0;
        }
        
        // Update auto users list
        const autoUsersList = document.getElementById('auto-users-list');
        if (autoUsersList) {
            const users = status.autoTranslateUsers || [];
            autoUsersList.textContent = users.length > 0 ? users.join(', ') : 'Нет';
        }
        
        // Update active operations
        const activeOperations = document.getElementById('active-operations');
        if (activeOperations) {
            const operationsCount = status.operations?.active || 0;
            activeOperations.textContent = operationsCount;
            activeOperations.style.color = operationsCount > 3 ? '#ff6b6b' : '#00d4ff';
        }
        
        // Update error count
        const errorCount = document.getElementById('error-count');
        if (errorCount) {
            const errors = status.errors || 0;
            errorCount.textContent = errors;
            errorCount.style.color = errors > 5 ? '#ff6b6b' : errors > 0 ? '#ffa726' : '#2ed573';
        }
    }

    // Utility methods
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    showSettingsNotification(message, type = 'error') {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.settings-notification');
        existingNotifications.forEach(notification => notification.remove());

        // Create new notification
        const notification = document.createElement('div');
        notification.className = `settings-notification ${type === 'success' ? 'success' : ''}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remove after 4 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 4000);
    }
    
    showAboutModal() {
        const modal = document.getElementById('about-modal');
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }
    
    hideAboutModal() {
        const modal = document.getElementById('about-modal');
        modal.style.display = 'none';
        document.body.style.overflow = 'auto'; // Restore scrolling
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new TwitchBotApp();
});

// Handle window resize
window.addEventListener('resize', () => {
    // Adjust layout if needed
    const logContent = document.getElementById('log-content');
    if (logContent) {
        logContent.style.height = `${window.innerHeight - 400}px`;
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.app) {
        window.app.destroy();
    }
});
