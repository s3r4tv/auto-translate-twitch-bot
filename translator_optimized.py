import logging
import asyncio
import time
import re
from typing import Optional, Dict, Any
from deep_translator import GoogleTranslator
from functools import lru_cache
import aiohttp
import json

class TranslationServiceOptimized:
    """Оптимизированный сервис для перевода текста через Google Translate"""
    
    def __init__(self, max_retries: int = 3, timeout: float = 10.0, max_cache_size: int = 1000):
        self.logger = logging.getLogger(__name__)
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_cache_size = max_cache_size
        
        # Кэш переводов с ограничением размера
        self.translation_cache: Dict[str, str] = {}
        self.cache_stats = {'hits': 0, 'misses': 0}
        
        # Статистика производительности
        self.performance_stats = {
            'total_translations': 0,
            'total_time': 0.0,
            'errors': 0,
            'retries': 0
        }
        
    def _cleanup_cache(self):
        """Очистка кэша при превышении лимита"""
        if len(self.translation_cache) > self.max_cache_size:
            # Удаляем 20% старых записей
            items_to_remove = int(self.max_cache_size * 0.2)
            keys_to_remove = list(self.translation_cache.keys())[:items_to_remove]
            for key in keys_to_remove:
                del self.translation_cache[key]
            
            self.logger.info(f"Кэш очищен: удалено {items_to_remove} записей")
            
    def _validate_text(self, text: str) -> bool:
        """Валидация текста для перевода"""
        if not text or not text.strip():
            return False
            
        # Ограничение длины текста
        if len(text) > 500:
            self.logger.warning(f"Текст слишком длинный: {len(text)} символов")
            return False
            
        # Проверка на опасные паттерны
        dangerous_patterns = [
            r'<script.*?>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'on\w+\s*='
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.logger.warning(f"Обнаружен опасный паттерн в тексте: {pattern}")
                return False
                
        return True
        
    def _get_cache_key(self, text: str, target_lang: str, source_lang: str = 'auto') -> str:
        """Генерация ключа кэша"""
        return f"{text.lower().strip()}_{source_lang}_{target_lang}"
        
    def _translate_sync(self, text: str, target_lang: str, source_lang: str = 'auto') -> Optional[str]:
        """Синхронный перевод с retry логикой"""
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                translated_text = translator.translate(text)
                
                duration = time.time() - start_time
                self.performance_stats['total_translations'] += 1
                self.performance_stats['total_time'] += duration
                
                self.logger.info(f"Перевод успешен за {duration:.2f}с (попытка {attempt + 1}): '{text[:50]}...' -> '{translated_text[:50]}...'")
                return translated_text
                
            except Exception as e:
                self.performance_stats['errors'] += 1
                self.performance_stats['retries'] += 1
                
                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Экспоненциальная задержка
                    self.logger.warning(f"Ошибка перевода (попытка {attempt + 1}): {e}. Повтор через {wait_time}с")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Перевод не удался после {self.max_retries} попыток: {e}")
                    return None
                    
        return None
        
    async def translate_text_async(self, text: str, target_lang: str, source_lang: str = 'auto') -> Optional[str]:
        """Асинхронный перевод текста"""
        if not self._validate_text(text):
            return None
            
        # Проверка кэша
        cache_key = self._get_cache_key(text, target_lang, source_lang)
        if cache_key in self.translation_cache:
            self.cache_stats['hits'] += 1
            self.logger.debug(f"Кэш-хит для ключа: {cache_key[:50]}...")
            return self.translation_cache[cache_key]
            
        self.cache_stats['misses'] += 1
        
        # Выполнение перевода в отдельном потоке
        try:
            loop = asyncio.get_event_loop()
            translated_text = await loop.run_in_executor(
                None, self._translate_sync, text, target_lang, source_lang
            )
            
            # Сохранение в кэш
            if translated_text:
                self.translation_cache[cache_key] = translated_text
                self._cleanup_cache()
                
            return translated_text
            
        except Exception as e:
            self.logger.error(f"Ошибка асинхронного перевода: {e}")
            return None
            
    async def translate_to_russian_async(self, text: str) -> Optional[str]:
        """Асинхронный перевод на русский язык"""
        return await self.translate_text_async(text, 'ru')
        
    async def translate_to_english_async(self, text: str) -> Optional[str]:
        """Асинхронный перевод на английский язык"""
        return await self.translate_text_async(text, 'en')
        
    def detect_language(self, text: str) -> Optional[str]:
        """Определяет язык текста с улучшенной логикой"""
        if not text or not text.strip():
            return None
            
        try:
            # Улучшенная эвристика для определения языка
            text_lower = text.lower()
            
            # Проверяем наличие кириллических символов
            cyrillic_chars = 'аеёиоуыэюя'
            cyrillic_count = sum(1 for char in text_lower if char in cyrillic_chars)
            
            # Проверяем наличие латинских символов
            latin_chars = 'abcdefghijklmnopqrstuvwxyz'
            latin_count = sum(1 for char in text_lower if char in latin_chars)
            
            # Определяем язык на основе преобладания символов
            if cyrillic_count > 0 and cyrillic_count >= latin_count:
                return 'ru'
            elif latin_count > 0:
                return 'en'
            else:
                # Если нет букв, возвращаем None
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка определения языка: {e}")
            return None
            
    def get_performance_stats(self) -> Dict[str, Any]:
        """Получение статистики производительности"""
        avg_time = (self.performance_stats['total_time'] / 
                   max(1, self.performance_stats['total_translations']))
        
        cache_hit_rate = (self.cache_stats['hits'] / 
                         max(1, self.cache_stats['hits'] + self.cache_stats['misses']))
        
        return {
            'total_translations': self.performance_stats['total_translations'],
            'average_time': avg_time,
            'total_errors': self.performance_stats['errors'],
            'total_retries': self.performance_stats['retries'],
            'cache_hits': self.cache_stats['hits'],
            'cache_misses': self.cache_stats['misses'],
            'cache_hit_rate': cache_hit_rate,
            'cache_size': len(self.translation_cache)
        }
        
    def reset_stats(self):
        """Сброс статистики"""
        self.performance_stats = {
            'total_translations': 0,
            'total_time': 0.0,
            'errors': 0,
            'retries': 0
        }
        self.cache_stats = {'hits': 0, 'misses': 0}
        
    def clear_cache(self):
        """Очистка кэша"""
        cache_size = len(self.translation_cache)
        self.translation_cache.clear()
        self.logger.info(f"Кэш полностью очищен: удалено {cache_size} записей")
        
    # Обратная совместимость с синхронными методами
    def translate_text(self, text: str, target_lang: str, source_lang: str = 'auto') -> Optional[str]:
        """Синхронный перевод (для обратной совместимости)"""
        if not self._validate_text(text):
            return None
            
        return self._translate_sync(text, target_lang, source_lang)
        
    def translate_to_russian(self, text: str) -> Optional[str]:
        """Синхронный перевод на русский (для обратной совместимости)"""
        return self.translate_text(text, 'ru')
        
    def translate_to_english(self, text: str) -> Optional[str]:
        """Синхронный перевод на английский (для обратной совместимости)"""
        return self.translate_text(text, 'en')
