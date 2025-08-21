import asyncio
import logging
import re
import time
from typing import Dict, Optional, Tuple
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException
import emoji

class AdvancedTranslationService:
    """Улучшенный сервис перевода с поддержкой сленга и контекста"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache: Dict[str, str] = {}
        self.cache_size_limit = 1000
        self.stats = {
            'translations': 0,
            'cache_hits': 0,
            'errors': 0,
            'avg_time': 0.0
        }
        
        # Инициализация переводчиков
        self.ru_en_translator = GoogleTranslator(source='ru', target='en')
        self.en_ru_translator = GoogleTranslator(source='en', target='ru')
        
        self.logger.info("AdvancedTranslationService инициализирован")
        
    def preprocess_text(self, text: str) -> str:
        """Предобработка текста для лучшего перевода"""
        if not text or not text.strip():
            return text
            
        # Нормализуем пробелы
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
        
    def postprocess_text(self, text: str, target_lang: str) -> str:
        """Постобработка переведенного текста"""
        if not text:
            return text
            
        # Исправляем типичные ошибки перевода
        if target_lang == 'ru':
            # Исправляем "ты" на "вы" в формальном контексте
            text = re.sub(r'\bты\b', 'вы', text, flags=re.IGNORECASE)
            # Исправляем "ваш" на "твой" в неформальном контексте
            text = re.sub(r'\bваш\b', 'твой', text, flags=re.IGNORECASE)
            
        elif target_lang == 'en':
            # Исправляем формальные формы на неформальные для чата
            text = re.sub(r'\bI am\b', "I'm", text, flags=re.IGNORECASE)
            text = re.sub(r'\byou are\b', "you're", text, flags=re.IGNORECASE)
            text = re.sub(r'\bwe are\b', "we're", text, flags=re.IGNORECASE)
            text = re.sub(r'\bthey are\b', "they're", text, flags=re.IGNORECASE)
            
        return text
        
    def detect_language(self, text: str) -> Optional[str]:
        """Определяет язык текста"""
        if not text or not text.strip():
            return None
            
        try:
            # Убираем эмодзи и специальные символы для определения языка
            clean_text = re.sub(r'[^\w\s]', '', text)
            if len(clean_text) < 3:
                return None
                
            lang = detect(clean_text)
            return lang
            
        except LangDetectException:
            # Fallback: проверяем наличие кириллицы
            if re.search(r'[а-яё]', text, re.IGNORECASE):
                return 'ru'
            elif re.search(r'[a-z]', text, re.IGNORECASE):
                return 'en'
            return None
            
    def translate_text(self, text: str, target_lang: str) -> Optional[str]:
        """Переводит текст с улучшенной обработкой"""
        if not text or not text.strip():
            return text
            
        start_time = time.time()
        
        try:
            # Проверяем кэш
            cache_key = f"{text}_{target_lang}"
            if cache_key in self.cache:
                self.stats['cache_hits'] += 1
                return self.cache[cache_key]
                
            # Предобработка
            processed_text = self.preprocess_text(text)
            
            # Определяем исходный язык
            source_lang = self.detect_language(processed_text)
            if not source_lang:
                self.logger.warning(f"Не удалось определить язык для: {text}")
                return None
                
            # Если язык уже целевой, возвращаем как есть
            if source_lang == target_lang:
                return text
                
            # Выбираем переводчик
            if source_lang == 'ru' and target_lang == 'en':
                translator = self.ru_en_translator
            elif source_lang == 'en' and target_lang == 'ru':
                translator = self.en_ru_translator
            else:
                # Fallback для других языков
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                
            # Выполняем перевод
            translated = translator.translate(processed_text)
            
            # Постобработка
            result = self.postprocess_text(translated, target_lang)
            
            # Кэшируем результат
            if len(self.cache) >= self.cache_size_limit:
                # Удаляем старые записи
                old_keys = list(self.cache.keys())[:100]
                for key in old_keys:
                    del self.cache[key]
                    
            self.cache[cache_key] = result
            
            # Обновляем статистику
            self.stats['translations'] += 1
            translation_time = time.time() - start_time
            self.stats['avg_time'] = (
                (self.stats['avg_time'] * (self.stats['translations'] - 1) + translation_time) 
                / self.stats['translations']
            )
            
            self.logger.info(f"Перевод: {text} -> {result} (время: {translation_time:.2f}с)")
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Ошибка перевода '{text}': {e}")
            return None
            
    def translate_to_russian(self, text: str) -> Optional[str]:
        """Переводит текст на русский язык"""
        return self.translate_text(text, 'ru')
        
    def translate_to_english(self, text: str) -> Optional[str]:
        """Переводит текст на английский язык"""
        return self.translate_text(text, 'en')
        
    def get_stats(self) -> Dict:
        """Возвращает статистику переводов"""
        return {
            **self.stats,
            'cache_size': len(self.cache),
            'cache_hit_rate': (
                self.stats['cache_hits'] / max(self.stats['translations'], 1) * 100
            )
        }
        
    def clear_cache(self):
        """Очищает кэш переводов"""
        self.cache.clear()
        self.logger.info("Кэш переводов очищен")
