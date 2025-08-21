const translate = require('google-translate-api-x');
const EventEmitter = require('events');

class AdvancedTranslationService extends EventEmitter {
    constructor() {
        super();
        
        this.cache = new Map();
        this.maxCacheSize = 1000; // Максимальный размер кэша
        this.maxCacheAge = 1000 * 60 * 60; // 1 час в миллисекундах
        this.cacheCleanupInterval = null;
        
        // Rate limiting
        this.requestQueue = [];
        this.isProcessingQueue = false;
        this.maxRequestsPerMinute = 30; // Лимит запросов в минуту
        this.requestTimes = [];
        
        this.stats = {
            translations: 0,
            cacheHits: 0,
            errors: 0,
            totalTime: 0,
            cacheEvictions: 0
        };
        
        // Запускаем периодическую очистку кэша
        this.startCacheCleanup();
        
        this.log('Продвинутый переводчик инициализирован');
    }

    log(message) {
        console.log(`[Translator] ${message}`);
    }

    preprocessText(text) {
        if (!text || typeof text !== 'string') return '';
        
        // Normalize text
        let processed = text.trim();
        
        // Handle emojis and special characters
        processed = processed.replace(/[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F1E0}-\u{1F1FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '');
        
        // Remove excessive whitespace
        processed = processed.replace(/\s+/g, ' ');
        
        return processed;
    }

    postprocessText(text, targetLang) {
        if (!text) return text;
        
        let processed = text;
        
        // Fix common formal/informal issues
        if (targetLang === 'ru') {
            // Make Russian translation more informal for chat
            processed = processed.replace(/^Привет, /, 'Привет, ');
            processed = processed.replace(/^Здравствуйте, /, 'Привет, ');
        } else if (targetLang === 'en') {
            // Make English translation more informal for chat
            processed = processed.replace(/^Hello, /, 'Hey, ');
            processed = processed.replace(/^Good morning, /, 'Hey, ');
        }
        
        return processed;
    }

    detectLanguage(text) {
        if (!text || text.length < 3) return null;
        
        const latinChars = (text.match(/[a-zA-Z]/g) || []).length;
        const cyrillicChars = (text.match(/[а-яё]/gi) || []).length;
        const totalChars = latinChars + cyrillicChars;
        
        if (totalChars === 0) return null;
        
        const latinPercent = (latinChars / totalChars) * 100;
        const cyrillicPercent = (cyrillicChars / totalChars) * 100;
        
        if (cyrillicPercent > 50) return 'ru';
        if (latinPercent > 50) return 'en';
        
        return null; // Mixed language
    }

    async translateToRussian(text) {
        return this.translate(text, 'en', 'ru');
    }

    async translateToEnglish(text) {
        return this.translate(text, 'ru', 'en');
    }

    async translate(text, sourceLang, targetLang) {
        const startTime = Date.now();
        
        try {
            // Preprocess text
            const processedText = this.preprocessText(text);
            if (!processedText) {
                this.stats.errors++;
                return null;
            }
            
            // Check cache
            const cacheKey = `${processedText}_${sourceLang}_${targetLang}`;
            const cachedValue = this.getCacheValue(cacheKey);
            if (cachedValue) {
                this.stats.cacheHits++;
                this.log(`Cache hit for: ${processedText.substring(0, 50)}...`);
                return cachedValue;
            }
            
            // Detect language if not provided
            const detectedLang = sourceLang || this.detectLanguage(processedText);
            if (!detectedLang) {
                this.log(`Could not detect language for: ${processedText}`);
                this.stats.errors++;
                return null;
            }
            
            // Perform translation with rate limiting
            this.log(`Translating: ${processedText.substring(0, 50)}... (${detectedLang} -> ${targetLang})`);
            
            const result = await this.performTranslationWithRateLimit(processedText, detectedLang, targetLang);
            
            if (!result || !result.text) {
                this.log(`Translation failed for: ${processedText}`);
                this.stats.errors++;
                return null;
            }
            
            // Postprocess result
            const finalResult = this.postprocessText(result.text, targetLang);
            
            // Cache result with timestamp
            this.setCacheWithTimestamp(cacheKey, finalResult);
            
            // Update stats
            this.stats.translations++;
            this.stats.totalTime += Date.now() - startTime;
            
            this.log(`Translation successful: ${processedText.substring(0, 30)}... -> ${finalResult.substring(0, 30)}...`);
            
            return finalResult;
            
        } catch (error) {
            this.log(`Translation error: ${error.message}`);
            this.stats.errors++;
            return null;
        }
    }

    getStats() {
        const avgTime = this.stats.translations > 0 ? this.stats.totalTime / this.stats.translations : 0;
        return {
            ...this.stats,
            averageTime: avgTime,
            cacheSize: this.cache.size,
            cacheHitRate: this.stats.translations > 0 ? (this.stats.cacheHits / this.stats.translations) * 100 : 0
        };
    }

    setCacheWithTimestamp(key, value) {
        // Проверяем размер кэша и очищаем при необходимости
        if (this.cache.size >= this.maxCacheSize) {
            this.evictOldestEntries();
        }
        
        this.cache.set(key, {
            value: value,
            timestamp: Date.now()
        });
    }
    
    getCacheValue(key) {
        const entry = this.cache.get(key);
        if (!entry) return null;
        
        // Проверяем возраст записи
        if (Date.now() - entry.timestamp > this.maxCacheAge) {
            this.cache.delete(key);
            this.stats.cacheEvictions++;
            return null;
        }
        
        return entry.value;
    }
    
    evictOldestEntries() {
        const entriesToDelete = Math.floor(this.maxCacheSize * 0.2); // Удаляем 20% самых старых
        const entries = Array.from(this.cache.entries());
        
        // Сортируем по времени создания
        entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
        
        for (let i = 0; i < entriesToDelete && i < entries.length; i++) {
            this.cache.delete(entries[i][0]);
            this.stats.cacheEvictions++;
        }
        
        this.log(`Evicted ${entriesToDelete} old cache entries`);
    }
    
    startCacheCleanup() {
        // Очистка кэша каждые 10 минут
        this.cacheCleanupInterval = setInterval(() => {
            this.cleanupExpiredEntries();
        }, 1000 * 60 * 10);
    }
    
    cleanupExpiredEntries() {
        const now = Date.now();
        let expiredCount = 0;
        
        for (const [key, entry] of this.cache.entries()) {
            if (now - entry.timestamp > this.maxCacheAge) {
                this.cache.delete(key);
                expiredCount++;
            }
        }
        
        if (expiredCount > 0) {
            this.stats.cacheEvictions += expiredCount;
            this.log(`Cleaned up ${expiredCount} expired cache entries`);
        }
    }
    
    stopCacheCleanup() {
        if (this.cacheCleanupInterval) {
            clearInterval(this.cacheCleanupInterval);
            this.cacheCleanupInterval = null;
        }
    }
    
    async performTranslationWithRateLimit(text, fromLang, toLang) {
        return new Promise((resolve, reject) => {
            this.requestQueue.push({
                text,
                fromLang,
                toLang,
                resolve,
                reject,
                timestamp: Date.now()
            });
            
            this.processQueue();
        });
    }
    
    async processQueue() {
        if (this.isProcessingQueue || this.requestQueue.length === 0) {
            return;
        }
        
        this.isProcessingQueue = true;
        
        try {
            while (this.requestQueue.length > 0) {
                // Проверяем лимит запросов
                if (!this.canMakeRequest()) {
                    const waitTime = this.getWaitTime();
                    this.log(`Rate limit reached, waiting ${waitTime}ms`);
                    await this.sleep(waitTime);
                    continue;
                }
                
                const request = this.requestQueue.shift();
                
                // Проверяем, не устарел ли запрос (более 30 секунд)
                const requestAge = Date.now() - request.timestamp;
                if (requestAge > 30000) {
                    this.log(`Skipping stale translation request (${requestAge}ms old)`);
                    request.reject(new Error('Request timeout'));
                    continue;
                }
                
                try {
                    // Записываем время запроса
                    this.requestTimes.push(Date.now());
                    
                    // Выполняем перевод
                    const result = await translate(request.text, {
                        from: request.fromLang,
                        to: request.toLang
                    });
                    
                    request.resolve(result);
                    
                } catch (error) {
                    this.log(`Translation API error: ${error.message}`);
                    this.stats.errors++;
                    
                    // Если это ошибка сети или API, пробуем повторить
                    if (error.message.includes('network') || error.message.includes('timeout')) {
                        this.log(`Retrying translation due to network error...`);
                        // Возвращаем запрос в очередь для повторной попытки
                        this.requestQueue.unshift(request);
                    } else {
                        request.reject(error);
                    }
                }
                
                // Небольшая задержка между запросами
                await this.sleep(100);
            }
        } catch (error) {
            this.log(`Queue processing error: ${error.message}`);
        } finally {
            this.isProcessingQueue = false;
        }
    }
    
    canMakeRequest() {
        const now = Date.now();
        const oneMinuteAgo = now - 60000;
        
        // Очищаем старые записи
        this.requestTimes = this.requestTimes.filter(time => time > oneMinuteAgo);
        
        return this.requestTimes.length < this.maxRequestsPerMinute;
    }
    
    getWaitTime() {
        if (this.requestTimes.length === 0) return 0;
        
        const oldestRequest = Math.min(...this.requestTimes);
        const timeUntilOldestExpires = 60000 - (Date.now() - oldestRequest);
        
        return Math.max(timeUntilOldestExpires, 1000); // Минимум 1 секунда
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    clearCache() {
        this.cache.clear();
        this.stats.cacheEvictions += this.cache.size;
        this.log('Translation cache cleared');
    }
}

module.exports = { AdvancedTranslationService };
