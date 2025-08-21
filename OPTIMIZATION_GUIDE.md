# 🚀 Руководство по оптимизации и диагностике Twitch Translate Bot

## 📊 Анализ производительности

### Ключевые метрики для мониторинга:

1. **Время ответа переводов** - должно быть < 2 секунд
2. **Использование памяти** - должно быть < 500MB
3. **Cache hit rate** - должно быть > 70%
4. **API success rate** - должно быть > 95%
5. **Количество ошибок** - должно быть < 10 в час

## 🔧 Методы диагностики

### 1. Мониторинг в реальном времени

```python
# Запуск с подробным логированием
python main.py --debug --monitor

# Просмотр статистики каждые 5 минут
python -c "from monitoring import BotMonitor; monitor = BotMonitor(); monitor.log_periodic_stats()"
```

### 2. Проверка здоровья системы

```python
# Проверка состояния бота
from monitoring import BotMonitor
monitor = BotMonitor()
health = monitor.check_health()
print(f"Статус: {health['status']}")
print(f"Проблемы: {health['issues']}")
```

### 3. Анализ производительности переводов

```python
# Статистика переводов
from translator_optimized import TranslationServiceOptimized
translator = TranslationServiceOptimized()
stats = translator.get_performance_stats()
print(f"Среднее время перевода: {stats['average_time']:.2f}с")
print(f"Cache hit rate: {stats['cache_hit_rate']:.1%}")
```

## 🛠️ Оптимизации

### 1. Асинхронные переводы

**Проблема:** Синхронные переводы блокируют обработку сообщений

**Решение:** Использовать `translator_optimized.py`

```python
# Вместо синхронного вызова
result = translator.translate_to_russian(text)

# Использовать асинхронный
result = await translator.translate_to_russian_async(text)
```

### 2. Управление кэшем

**Проблема:** Неограниченный рост кэша

**Решение:** Автоматическая очистка

```python
# Настройка ограничений кэша
translator = TranslationServiceOptimized(max_cache_size=1000)

# Ручная очистка
translator.clear_cache()
```

### 3. Retry логика

**Проблема:** Временные сбои API

**Решение:** Автоматические повторы

```python
# Настройка retry
translator = TranslationServiceOptimized(max_retries=3, timeout=10.0)
```

### 4. Валидация входных данных

**Проблема:** Небезопасный пользовательский ввод

**Решение:** Строгая валидация

```python
from validators import InputValidator

validator = InputValidator()
result = validator.validate_text(user_input)

if not result.is_valid:
    print(f"Ошибки: {result.errors}")
```

## 📈 Улучшения производительности

### 1. Оптимизация логирования

```python
# Настройка ротации логов
import logging.handlers

handler = logging.handlers.RotatingFileHandler(
    'bot.log', maxBytes=10*1024*1024, backupCount=5
)
```

### 2. Мониторинг памяти

```python
# Автоматическая очистка памяти
import gc

def cleanup_memory():
    gc.collect()
    # Принудительная очистка кэша
    translator.clear_cache()
```

### 3. Ограничение частоты запросов

```python
# Rate limiting для API
import asyncio
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    async def acquire(self):
        now = datetime.now()
        # Удаляем старые запросы
        self.requests = [req for req in self.requests 
                        if now - req < timedelta(seconds=self.time_window)]
        
        if len(self.requests) >= self.max_requests:
            wait_time = self.time_window - (now - self.requests[0]).seconds
            await asyncio.sleep(wait_time)
        
        self.requests.append(now)
```

## 🔍 Диагностика проблем

### 1. Проблемы с подключением

**Симптомы:** Бот не подключается к Twitch

**Диагностика:**
```python
# Проверка токенов
import requests

def test_twitch_connection(access_token, client_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Client-Id': client_id
    }
    
    response = requests.get('https://api.twitch.tv/helix/users', headers=headers)
    return response.status_code == 200
```

### 2. Проблемы с переводами

**Симптомы:** Медленные или неудачные переводы

**Диагностика:**
```python
# Тест переводов
async def test_translations():
    translator = TranslationServiceOptimized()
    
    test_texts = [
        "Hello world",
        "Привет мир",
        "Test message"
    ]
    
    for text in test_texts:
        start = time.time()
        result = await translator.translate_to_russian_async(text)
        duration = time.time() - start
        
        print(f"'{text}' -> '{result}' ({duration:.2f}с)")
```

### 3. Проблемы с памятью

**Симптомы:** Высокое использование памяти

**Диагностика:**
```python
import psutil

def check_memory_usage():
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"Использование памяти: {memory_info.rss / 1024 / 1024:.1f} MB")
    
    if memory_info.rss > 500 * 1024 * 1024:  # 500MB
        print("⚠️ Высокое использование памяти!")
        return False
    return True
```

## 🚨 Обработка критических ошибок

### 1. Graceful degradation

```python
class BotErrorHandler:
    def __init__(self):
        self.error_count = 0
        self.max_errors = 10
        
    async def handle_error(self, error: Exception, context: str):
        self.error_count += 1
        
        if self.error_count > self.max_errors:
            # Перезапуск бота
            await self.restart_bot()
        else:
            # Логирование и продолжение работы
            self.logger.error(f"Ошибка [{context}]: {error}")
```

### 2. Автоматическое восстановление

```python
async def auto_recovery():
    while True:
        try:
            # Проверка здоровья
            health = monitor.check_health()
            
            if health['status'] == 'critical':
                await restart_bot()
            
            await asyncio.sleep(60)  # Проверка каждую минуту
            
        except Exception as e:
            logger.error(f"Ошибка в auto_recovery: {e}")
```

## 📋 Чек-лист оптимизации

### Перед запуском:
- [ ] Проверить все зависимости
- [ ] Настроить логирование
- [ ] Проверить токены Twitch
- [ ] Настроить права модератора

### Во время работы:
- [ ] Мониторить использование памяти
- [ ] Следить за временем ответа
- [ ] Проверять cache hit rate
- [ ] Анализировать ошибки

### При проблемах:
- [ ] Проверить логи
- [ ] Перезапустить бота
- [ ] Очистить кэш
- [ ] Проверить сетевое соединение

## 🎯 Рекомендации по производительности

1. **Используйте асинхронные переводы** для лучшей производительности
2. **Настройте размер кэша** в зависимости от доступной памяти
3. **Мониторьте метрики** регулярно
4. **Обрабатывайте ошибки** gracefully
5. **Валидируйте входные данные** строго
6. **Используйте retry логику** для API вызовов
7. **Ограничивайте частоту запросов** для избежания rate limiting
8. **Периодически очищайте память** для предотвращения утечек
