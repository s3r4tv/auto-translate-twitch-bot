import logging
import time
import psutil
import gc
from datetime import datetime
from typing import Dict, Any, Optional
import json
import asyncio
from dataclasses import dataclass, asdict

@dataclass
class BotStats:
    """Статистика работы бота"""
    start_time: datetime
    messages_processed: int = 0
    translations_made: int = 0
    errors_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls: int = 0
    api_errors: int = 0
    memory_usage_mb: float = 0.0
    
class BotMonitor:
    """Мониторинг состояния бота"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.stats = BotStats(start_time=datetime.now())
        self.logger = logger or logging.getLogger(__name__)
        self.performance_metrics = []
        self.error_history = []
        
    def log_message_processed(self):
        """Логирование обработанного сообщения"""
        self.stats.messages_processed += 1
        
    def log_translation_made(self, duration: float = 0.0):
        """Логирование выполненного перевода"""
        self.stats.translations_made += 1
        self.performance_metrics.append({
            'type': 'translation',
            'duration': duration,
            'timestamp': datetime.now()
        })
        
    def log_error(self, error: Exception, context: str = ""):
        """Логирование ошибки"""
        self.stats.errors_count += 1
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'timestamp': datetime.now()
        }
        self.error_history.append(error_info)
        
        # Ограничиваем историю ошибок
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-50:]
            
        self.logger.error(f"Ошибка [{context}]: {error}", exc_info=True)
        
    def log_cache_hit(self):
        """Логирование попадания в кэш"""
        self.stats.cache_hits += 1
        
    def log_cache_miss(self):
        """Логирование промаха кэша"""
        self.stats.cache_misses += 1
        
    def log_api_call(self, success: bool = True):
        """Логирование вызова API"""
        self.stats.api_calls += 1
        if not success:
            self.stats.api_errors += 1
            
    def update_memory_usage(self):
        """Обновление информации об использовании памяти"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            self.stats.memory_usage_mb = memory_info.rss / 1024 / 1024
        except Exception as e:
            self.logger.warning(f"Не удалось получить информацию о памяти: {e}")
            
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        self.update_memory_usage()
        
        uptime = datetime.now() - self.stats.start_time
        total_cache_requests = self.stats.cache_hits + self.stats.cache_misses
        
        return {
            **asdict(self.stats),
            'uptime_seconds': uptime.total_seconds(),
            'uptime_formatted': str(uptime).split('.')[0],
            'cache_hit_rate': self.stats.cache_hits / max(1, total_cache_requests),
            'api_success_rate': (self.stats.api_calls - self.stats.api_errors) / max(1, self.stats.api_calls),
            'messages_per_minute': self.stats.messages_processed / max(1, uptime.total_seconds() / 60),
            'translations_per_minute': self.stats.translations_made / max(1, uptime.total_seconds() / 60)
        }
        
    def log_periodic_stats(self):
        """Периодическое логирование статистики"""
        stats = self.get_stats()
        
        # Форматируем статистику для логирования
        log_stats = {
            'uptime': stats['uptime_formatted'],
            'messages': stats['messages_processed'],
            'translations': stats['translations_made'],
            'errors': stats['errors_count'],
            'cache_hit_rate': f"{stats['cache_hit_rate']:.1%}",
            'api_success_rate': f"{stats['api_success_rate']:.1%}",
            'memory_mb': f"{stats['memory_usage_mb']:.1f}",
            'msg_per_min': f"{stats['messages_per_minute']:.1f}",
            'trans_per_min': f"{stats['translations_per_minute']:.1f}"
        }
        
        self.logger.info(f"Статистика бота: {json.dumps(log_stats, indent=2)}")
        
    def get_error_summary(self) -> Dict[str, Any]:
        """Получение сводки ошибок"""
        if not self.error_history:
            return {'total_errors': 0, 'error_types': {}}
            
        error_types = {}
        for error in self.error_history:
            error_type = error['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
        return {
            'total_errors': len(self.error_history),
            'error_types': error_types,
            'recent_errors': self.error_history[-5:]  # Последние 5 ошибок
        }
        
    def check_health(self) -> Dict[str, Any]:
        """Проверка здоровья бота"""
        stats = self.get_stats()
        error_summary = self.get_error_summary()
        
        # Определяем состояние здоровья
        health_status = 'healthy'
        issues = []
        
        # Проверяем количество ошибок
        if stats['errors_count'] > 10:
            health_status = 'warning'
            issues.append(f"Много ошибок: {stats['errors_count']}")
            
        # Проверяем успешность API
        if stats['api_success_rate'] < 0.9:
            health_status = 'warning'
            issues.append(f"Низкая успешность API: {stats['api_success_rate']:.1%}")
            
        # Проверяем использование памяти
        if stats['memory_usage_mb'] > 500:  # Больше 500MB
            health_status = 'warning'
            issues.append(f"Высокое использование памяти: {stats['memory_usage_mb']:.1f}MB")
            
        return {
            'status': health_status,
            'issues': issues,
            'stats': stats,
            'errors': error_summary
        }
