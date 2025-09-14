const tmi = require('tmi.js');
const { AdvancedTranslationService } = require('./translator_advanced.js');
const EventEmitter = require('events');
const fs = require('fs');
const path = require('path');

class TranslateBot extends EventEmitter {
    constructor(accessToken, clientId, nickname, channel) {
        super();
        
        this.accessToken = accessToken;
        this.clientId = clientId;
        this.nickname = nickname;
        this.channel = channel;
        
        this.translator = new AdvancedTranslationService();
        this.autoTranslateUsers = new Set();
        this.translationCache = new Map();
        
        this.client = null;
        this.isRunning = false;
        
        // Error handling
        this.errorCount = 0;
        this.maxErrors = 10;
        this.errorResetInterval = 1000 * 60 * 10; // 10 минут
        this.lastErrorReset = Date.now();
        
        // Retry logic
        this.maxRetries = 3;
        this.retryDelay = 2000;
        
        // Concurrency control
        this.activeOperations = new Map();
        this.operationQueue = [];
        this.maxConcurrentOperations = 5;
        
        // Загружаем сохраненные настройки автоперевода
        this.loadAutoTranslateSettings();
        
        this.log('Бот инициализирован для канала: ' + channel);
    }

    log(message, type = 'info') {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] ${message}`;
        
        // Emit log event for renderer
        this.emit('log', message);
        
        // Also log to console
        console.log(logMessage);
    }
    
    handleError(error, context = '', isCritical = false) {
        this.errorCount++;
        this.log(`❌ Ошибка [${context}]: ${error.message}`, 'error');
        
        // Сброс счетчика ошибок через интервал
        if (Date.now() - this.lastErrorReset > this.errorResetInterval) {
            this.errorCount = 0;
            this.lastErrorReset = Date.now();
        }
        
        // Критические ошибки или слишком много ошибок
        if (isCritical || this.errorCount > this.maxErrors) {
            this.log(`🚨 Критическая ситуация: ${this.errorCount} ошибок за ${this.errorResetInterval/1000/60} минут`, 'error');
            
            if (this.isRunning) {
                this.handleCriticalError(error, context);
            }
        }
        
        return !isCritical && this.errorCount <= this.maxErrors;
    }
    
    async handleCriticalError(error, context) {
        this.log('🔄 Попытка восстановления после критической ошибки...', 'warning');
        
        try {
            // Отправляем уведомление в чат
            if (this.client && this.isRunning) {
                await this.sendMessage('⚠️ Обнаружена проблема с ботом. Попытка восстановления...');
            }
            
            // Перезапуск соединения
            await this.reconnect();
            
        } catch (reconnectError) {
            this.log(`❌ Не удалось восстановить соединение: ${reconnectError.message}`, 'error');
            if (this.isRunning) {
                await this.stop();
            }
        }
    }
    
    async reconnect() {
        this.log('🔄 Переподключение к Twitch...', 'info');
        
        if (this.client) {
            this.client.disconnect();
            this.client = null;
        }
        
        // Задержка перед переподключением
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Попытка переподключения
        await this.start();
    }
    
    async safeExecute(operation, context, retries = this.maxRetries) {
        for (let attempt = 1; attempt <= retries; attempt++) {
            try {
                return await operation();
            } catch (error) {
                const isLastAttempt = attempt === retries;
                
                if (isLastAttempt) {
                    if (!this.handleError(error, context)) {
                        throw error; // Пробрасываем критические ошибки
                    }
                    return null; // Возвращаем null для некритических ошибок
                }
                
                this.log(`⚠️ Попытка ${attempt}/${retries} неудачна [${context}]: ${error.message}`, 'warning');
                await new Promise(resolve => setTimeout(resolve, this.retryDelay * attempt));
            }
        }
    }
    
    async handleMessageSafely(messageObj) {
        // Валидация входных данных
        if (!messageObj || !messageObj.author || !messageObj.author.username || !messageObj.content) {
            this.log('⚠️ Получено некорректное сообщение', 'warning');
            return;
        }
        
        const operationId = `${messageObj.author.username}_${Date.now()}`;
        
        // Проверяем лимит concurrent операций
        if (this.activeOperations.size >= this.maxConcurrentOperations) {
            this.log(`⚠️ Максимум операций достигнут, сообщение в очередь от ${messageObj.author.username}`, 'warning');
            this.operationQueue.push({ messageObj, operationId });
            return;
        }
        
        // Добавляем операцию в активные
        this.activeOperations.set(operationId, {
            username: messageObj.author.username,
            startTime: Date.now(),
            type: messageObj.content.startsWith('!') ? 'command' : 'auto_translate'
        });
        
        try {
            await this.safeExecute(async () => {
                if (messageObj.content.startsWith('!')) {
                    await this.handleCommands(messageObj);
                } else {
                    await this.handleAutoTranslate(messageObj);
                }
            }, `message_processing_${messageObj.author.username}`);
        } finally {
            // Удаляем операцию из активных
            this.activeOperations.delete(operationId);
            
            // Обрабатываем очередь
            this.processOperationQueue();
        }
    }
    
    processOperationQueue() {
        while (this.operationQueue.length > 0 && this.activeOperations.size < this.maxConcurrentOperations) {
            const { messageObj, operationId } = this.operationQueue.shift();
            
            // Проверяем, не устарело ли сообщение (более 30 секунд)
            const messageAge = Date.now() - parseInt(operationId.split('_')[1]);
            if (messageAge > 30000) {
                this.log(`⚠️ Пропуск устаревшего сообщения от ${messageObj.author.username}`, 'warning');
                continue; // Пропускаем и проверяем следующее
            }
            
            // Асинхронно обрабатываем сообщение из очереди
            setImmediate(() => this.handleMessageSafely(messageObj));
        }
    }
    
    // Метод для получения статистики операций
    getOperationStats() {
        const now = Date.now();
        const stats = {
            active: this.activeOperations.size,
            queued: this.operationQueue.length,
            details: []
        };
        
        for (const [id, operation] of this.activeOperations.entries()) {
            stats.details.push({
                id,
                username: operation.username,
                type: operation.type,
                duration: now - operation.startTime
            });
        }
        
        return stats;
    }

    hasModeratorPrivileges(user) {
        // Check if user is moderator or channel owner
        return user.mod || user['user-type'] === 'mod' || user.username.toLowerCase() === this.channel.toLowerCase();
    }

    shouldAutoTranslateMessage(content) {
        if (content.length < 3) return false;
        
        const latinChars = (content.match(/[a-zA-Z]/g) || []).length;
        const cyrillicChars = (content.match(/[а-яё]/gi) || []).length;
        const totalChars = latinChars + cyrillicChars;
        
        if (totalChars === 0) return false;
        
        const latinPercent = (latinChars / totalChars) * 100;
        
        // For auto-detection: translate only English to Russian
        return latinPercent > 50;
    }

    shouldTranslateForAutoUser(content) {
        if (content.length < 3) return false;
        
        const latinChars = (content.match(/[a-zA-Z]/g) || []).length;
        const cyrillicChars = (content.match(/[а-яё]/gi) || []).length;
        const spanishChars = (content.match(/[ñáéíóúü¿¡]/gi) || []).length;
        const totalChars = latinChars + cyrillicChars;
        
        if (totalChars === 0) return false;
        
        const latinPercent = (latinChars / totalChars) * 100;
        const cyrillicPercent = (cyrillicChars / totalChars) * 100;
        const spanishPercent = (spanishChars / totalChars) * 100;
        
        // Translate only if one language is > 50% and the other is < 50%
        return (latinPercent > 50 && cyrillicPercent < 50) || (cyrillicPercent > 50 && latinPercent < 50) || (spanishPercent > 10);
    }
    
    detectLanguage(text) {
        if (!text || text.length < 2) return null;
        
        const latinChars = (text.match(/[a-zA-Z]/g) || []).length;
        const cyrillicChars = (text.match(/[а-яё]/gi) || []).length;
        const spanishChars = (text.match(/[ñáéíóúü¿¡]/gi) || []).length;
        const totalChars = latinChars + cyrillicChars;
        
        if (totalChars === 0) return null;
        
        const latinPercent = (latinChars / totalChars) * 100;
        const cyrillicPercent = (cyrillicChars / totalChars) * 100;
        const spanishPercent = (spanishChars / totalChars) * 100;
        
        if (cyrillicPercent > 50) return 'ru';
        if (spanishPercent > 10) return 'es'; // Испанский если есть испанские символы
        if (latinPercent > 50) return 'en';
        
        return null; // Mixed language
    }

    async handleAutoTranslate(message) {
        const author = message.author.username.toLowerCase();
        const content = message.content.trim();
        
        // Проверяем длину сообщения
        if (content.length > 300) {
            this.log(`⚠️ Слишком длинное сообщение для автоперевода от ${message.author.username}: ${content.length} символов`);
            return;
        }
        
        const userInAutoList = this.autoTranslateUsers.has(author);
        
        // Переводим только для пользователей в списке !auto
        if (!userInAutoList) {
            return;
        }
        
        const shouldTranslate = this.shouldTranslateForAutoUser(content);
        
        if (shouldTranslate && content) {
            this.log(`🔍 Проверка автоперевода для ${message.author.username}: user_in_auto_list=${userInAutoList}`);
            
            const latinChars = (content.match(/[a-zA-Z]/g) || []).length;
            const cyrillicChars = (content.match(/[а-яё]/gi) || []).length;
            const spanishChars = (content.match(/[ñáéíóúü¿¡]/gi) || []).length;
            const totalChars = latinChars + cyrillicChars;
            
            if (totalChars > 0) {
                const latinPercent = (latinChars / totalChars) * 100;
                const cyrillicPercent = (cyrillicChars / totalChars) * 100;
                const spanishPercent = (spanishChars / totalChars) * 100;
                
                this.log(`🔍 Анализ языка для '${content}': латиница ${latinPercent.toFixed(1)}%, кириллица ${cyrillicPercent.toFixed(1)}%, испанский ${spanishPercent.toFixed(1)}%`);
                
                if (userInAutoList) {
                    // For users in auto-translate list - translate to opposite language
                    if (cyrillicPercent > 50 && latinPercent < 50) {
                        // Russian predominates - translate to English
                        const translatedText = await this.translator.translateToEnglish(content);
                        const targetLang = "английский";
                        this.log(`🔄 Автоперевод для ${message.author.username}: русский -> английский`);
                        
                        if (translatedText && translatedText !== content) {
                            await this.sendMessage(`@${message.author.username} write: ${translatedText}`);
                            this.log(`🔄 Авто-перевод для ${message.author.username} на ${targetLang}: ${content} -> ${translatedText}`);
                        }
                    } else if (latinPercent > 50 && cyrillicPercent < 50 && spanishPercent < 10) {
                        // English predominates - translate to Russian
                        const translatedText = await this.translator.translateToRussian(content);
                        const targetLang = "русский";
                        this.log(`🔄 Автоперевод для ${message.author.username}: английский -> русский`);
                        
                        if (translatedText && translatedText !== content) {
                            await this.sendMessage(`@${message.author.username} пишет: ${translatedText}`);
                            this.log(`🔄 Авто-перевод для ${message.author.username} на ${targetLang}: ${content} -> ${translatedText}`);
                        }
                    } else if (spanishPercent > 10) {
                        // Spanish predominates - translate to English
                        const translatedText = await this.translator.translateToEnglish(content);
                        const targetLang = "английский";
                        this.log(`🔄 Автоперевод для ${message.author.username}: испанский -> английский`);
                        
                        if (translatedText && translatedText !== content) {
                            await this.sendMessage(`@${message.author.username} write: ${translatedText}`);
                            this.log(`🔄 Авто-перевод для ${message.author.username} на ${targetLang}: ${content} -> ${translatedText}`);
                        }
                    } else {
                        // Mixed language - don't translate
                        this.log(`⏭️ Смешанный язык для ${message.author.username} - пропускаем`);
                    }
                }
            } else {
                this.log(`⏭️ Нет букв для анализа в сообщении: '${content}'`);
            }
        }
    }

    async handleCommands(message) {
        const content = message.content.toLowerCase().trim();
        const author = message.author.username;
        
        // !ru command
        if (content.startsWith('!ru ')) {
            const text = message.content.substring(4).trim();
            if (text) {
                await this.handleTranslateCommand(message, text, 'ru');
            } else {
                await this.sendMessage(`@${author} ❌ Укажите текст для перевода! Использование: !ru <текст>`);
            }
        }
        // !en command
        else if (content.startsWith('!en ')) {
            const text = message.content.substring(4).trim();
            if (text) {
                await this.handleTranslateCommand(message, text, 'en');
            } else {
                await this.sendMessage(`@${author} ❌ Укажите текст для перевода! Использование: !en <текст>`);
            }
        }
        // !es command
        else if (content.startsWith('!es ')) {
            const text = message.content.substring(4).trim();
            if (text) {
                await this.handleTranslateCommand(message, text, 'es');
            } else {
                await this.sendMessage(`@${author} ❌ Укажите текст для перевода! Использование: !es <текст>`);
            }
        }
        // !auto command
        else if (content.startsWith('!auto ')) {
            await this.handleAutoCommand(message);
        }

        // !tstatus command
        else if (content === '!tstatus') {
            await this.handleStatusCommand(message);
        }
    }

    async handleTranslateCommand(message, text, targetLang) {
        const author = message.author.username;
        
        // Проверяем длину текста
        if (text.length > 500) {
            await this.sendMessage(`@${author} ❌ Текст слишком длинный. Максимальная длина: 500 символов.`);
            this.log(`❌ Слишком длинный текст для ${author}: ${text.length} символов`);
            return;
        }
        
        // Определяем исходный язык текста
        const sourceLang = this.detectLanguage(text);
        if (!sourceLang) {
            await this.sendMessage(`@${author} ❌ Не удалось определить язык текста. Попробуйте другой текст.`);
            this.log(`❌ Не удалось определить язык для ${author}: ${text}`);
            return;
        }
        
        // Проверяем, не пытаемся ли перевести на тот же язык
        if (sourceLang === targetLang) {
            const langNames = {
                'ru': 'русском',
                'en': 'английском',
                'es': 'испанском'
            };
            await this.sendMessage(`@${author} ℹ️ Текст уже на ${langNames[targetLang] || targetLang} языке.`);
            this.log(`ℹ️ Попытка перевода на тот же язык для ${author}: ${text}`);
            return;
        }
        
        // Check cache
        const cacheKey = `${text}_${sourceLang}_${targetLang}`;
        let translatedText = this.translationCache.get(cacheKey);
        
        if (!translatedText) {
            // Perform translation with correct source language
            translatedText = await this.translator.translate(text, sourceLang, targetLang);
            
            // Save to cache with size limit
            if (translatedText) {
                // Ограничиваем размер кэша
                if (this.translationCache.size >= 500) {
                    const firstKey = this.translationCache.keys().next().value;
                    this.translationCache.delete(firstKey);
                }
                this.translationCache.set(cacheKey, translatedText);
            }
        }
        
        if (translatedText) {
            const langNames = {
                'ru': "русский",
                'en': "английский", 
                'es': "испанский"
            };
            const writeTexts = {
                'ru': "пишет",
                'en': "write",
                'es': "escribe"
            };
            const langName = langNames[targetLang] || targetLang;
            const writeText = writeTexts[targetLang] || "write";
            await this.sendMessage(`@${author} ${writeText}: ${translatedText}`);
            this.log(`✅ Перевод выполнен для ${author} на ${langName}: ${text} -> ${translatedText}`);
        } else {
            await this.sendMessage(`@${author} ❌ Ошибка перевода. Не удалось перевести текст. Попробуйте позже или проверьте правильность написания.`);
            this.log(`❌ Ошибка перевода для ${author}: ${text}`);
        }
    }

    async handleAutoCommand(message) {
        const content = message.content.substring(6).trim(); // Remove '!auto '
        const author = message.author.username;
        
        // Check moderator privileges
        if (!this.hasModeratorPrivileges(message.author)) {
            await this.sendMessage(`@${author} 🚫 Эта команда доступна только модераторам и владельцу канала!`);
            return;
        }
        
        // Parse command: !auto @nickname on/off
        const match = content.match(/@(\w+)\s+(on|off)/);
        if (!match) {
            await this.sendMessage(`@${author} ❌ Неверный формат команды! Использование: !auto @nickname on/off`);
            return;
        }
        
        const targetUser = match[1].toLowerCase();
        const action = match[2];
        
        if (action === 'on') {
            if (this.autoTranslateUsers.has(targetUser)) {
                await this.sendMessage(`ℹ️ @${author} Авто-перевод для @${targetUser} уже включен!`);
                return;
            }
            
            this.autoTranslateUsers.add(targetUser);
            const usersCount = this.autoTranslateUsers.size;
            await this.sendMessage(`✅ @${author} Авто-перевод для @${targetUser} успешно включен! Всего пользователей в списке автоперевода: ${usersCount}`);
            this.log(`Авто-перевод включен для пользователя: ${targetUser} (команда от ${author})`);
            this.saveAutoTranslateSettings();
        } else {
            if (!this.autoTranslateUsers.has(targetUser)) {
                await this.sendMessage(`ℹ️ @${author} Авто-перевод для @${targetUser} уже отключен!`);
                return;
            }
            
            this.autoTranslateUsers.delete(targetUser);
            const usersCount = this.autoTranslateUsers.size;
            await this.sendMessage(`🔴 @${author} Авто-перевод для @${targetUser} успешно отключен. Осталось пользователей в списке автоперевода: ${usersCount}`);
            this.log(`Авто-перевод отключен для пользователя: ${targetUser} (команда от ${author})`);
            this.saveAutoTranslateSettings();
        }
    }



    async handleStatusCommand(message) {
        const author = message.author.username;
        
        const usersCount = this.autoTranslateUsers.size;
        const cacheSize = this.translationCache.size;
        
        const statusMessage = `📊 @${author} Статус бота: Пользователей в автопереводе: ${usersCount} | Переводов в кэше: ${cacheSize}`;
        
        await this.sendMessage(statusMessage);
        this.log(`Статус бота запрошен пользователем ${author}`);
    }

    async sendMessage(message) {
        if (this.client) {
            return await this.safeExecute(async () => {
                await this.client.say(this.channel, message);
            }, 'send_message');
        }
    }

    async start() {
        try {
            this.log('Запуск бота...');
            
            // Initialize Twitch client
            this.client = new tmi.Client({
                options: { debug: false },
                connection: {
                    reconnect: true,
                    secure: true
                },
                identity: {
                    username: this.nickname,
                    password: this.accessToken
                },
                channels: [this.channel]
            });
            
            // Set up event handlers
            this.client.on('connected', (addr, port) => {
                this.log(`Бот ${this.nickname} подключен к Twitch!`);
                this.log(`Присоединился к каналу: ${this.channel}`);
                this.sendMessage('🤖 Бот авто-перевода сообщений готов к работе! Доступные команды: !ru <text>, !en <text>, !es <text>, !auto @user on/off, !tstatus');
            });
            
            this.client.on('message', async (channel, tags, message, self) => {
                if (self) return; // Ignore bot's own messages
                
                // Валидация тегов
                if (!tags || !tags.username) {
                    this.log('⚠️ Получено сообщение без имени пользователя', 'warning');
                    return;
                }
                
                // Немедленно логируем входящее сообщение
                this.log(`💬 ${tags.username}: ${message}`);
                
                // Create message object for compatibility
                const messageObj = {
                    content: message,
                    author: {
                        username: tags.username,
                        mod: tags.mod || false,
                        'user-type': tags['user-type'] || 'user'
                    }
                };
                
                // Безопасная обработка сообщений с контролем concurrency
                // Не ждем завершения обработки, чтобы не блокировать поток
                this.handleMessageSafely(messageObj).catch(error => {
                    this.log(`❌ Ошибка обработки сообщения от ${tags.username}: ${error.message}`, 'error');
                });
            });
            
            this.client.on('disconnected', (reason) => {
                this.log(`Бот ${this.nickname} отключен от Twitch: ${reason}`);
                this.isRunning = false;
            });
            
            this.client.on('error', (error) => {
                this.log(`Ошибка соединения Twitch: ${error.message}`, 'error');
                this.handleError(error, 'twitch_connection', true);
            });
            
            // Connect to Twitch
            await this.client.connect();
            this.isRunning = true;
            
            this.log('Бот успешно запущен!');
            
        } catch (error) {
            this.log(`Ошибка запуска бота: ${error.message}`, 'error');
            throw error;
        }
    }

    async stop() {
        try {
            this.log('Остановка бота...');
            
            if (this.client) {
                // Send goodbye message
                await this.sendMessage('🤖 Бот авто-перевода сообщений завершает работу. До свидания!');
                
                // Disconnect from Twitch
                this.client.disconnect();
                this.client = null;
            }
            
            this.isRunning = false;
            
            // Очищаем очереди и активные операции
            this.operationQueue = [];
            this.activeOperations.clear();
            
            // Останавливаем очистку кэша переводчика
            if (this.translator && this.translator.stopCacheCleanup) {
                this.translator.stopCacheCleanup();
            }
            
            // Сохраняем настройки автоперевода перед остановкой
            this.saveAutoTranslateSettings();
            
            this.log('Бот остановлен');
            
        } catch (error) {
            this.log(`Ошибка остановки бота: ${error.message}`, 'error');
            throw error;
        }
    }

    getStatus() {
        const operationStats = this.getOperationStats();
        
        return {
            running: this.isRunning,
            autoTranslateUsers: Array.from(this.autoTranslateUsers),
            cacheSize: this.translationCache.size,
            errors: this.errorCount,
            operations: {
                active: operationStats.active,
                queued: operationStats.queued
            }
        };
    }

    getAutoTranslateSettingsPath() {
        return path.join(__dirname, '..', '..', 'auto_translate_settings.json');
    }

    saveAutoTranslateSettings() {
        try {
            const settings = {
                users: Array.from(this.autoTranslateUsers),
                timestamp: Date.now()
            };
            
            const settingsPath = this.getAutoTranslateSettingsPath();
            fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
            this.log(`Настройки автоперевода сохранены: ${this.autoTranslateUsers.size} пользователей`);
        } catch (error) {
            this.log(`Ошибка сохранения настроек автоперевода: ${error.message}`, 'error');
        }
    }

    loadAutoTranslateSettings() {
        try {
            const settingsPath = this.getAutoTranslateSettingsPath();
            if (fs.existsSync(settingsPath)) {
                const data = fs.readFileSync(settingsPath, 'utf8');
                const settings = JSON.parse(data);
                
                if (settings.users && Array.isArray(settings.users)) {
                    this.autoTranslateUsers = new Set(settings.users);
                    this.log(`Загружены настройки автоперевода: ${this.autoTranslateUsers.size} пользователей`);
                }
            }
        } catch (error) {
            this.log(`Ошибка загрузки настроек автоперевода: ${error.message}`, 'error');
        }
    }
}

module.exports = { TranslateBot };
