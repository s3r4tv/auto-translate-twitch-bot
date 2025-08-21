import logging
from deep_translator import GoogleTranslator
from typing import Optional

class TranslationService:
    """Сервис для перевода текста через Google Translate"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def translate_text(self, text: str, target_lang: str, source_lang: str = 'auto') -> Optional[str]:
        """
        Переводит текст на указанный язык
        
        Args:
            text: Текст для перевода
            target_lang: Целевой язык (например, 'ru', 'en')
            source_lang: Исходный язык (по умолчанию 'auto' для автоопределения)
            
        Returns:
            Переведенный текст или None в случае ошибки
        """
        try:
            if not text.strip():
                return None
                
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated_text = translator.translate(text)
            
            self.logger.info(f"Перевод: '{text}' -> '{translated_text}' ({source_lang} -> {target_lang})")
            return translated_text
            
        except Exception as e:
            self.logger.error(f"Ошибка перевода: {e}")
            return None
    
    def translate_to_russian(self, text: str) -> Optional[str]:
        """Переводит текст на русский язык"""
        return self.translate_text(text, 'ru')
    
    def translate_to_english(self, text: str) -> Optional[str]:
        """Переводит текст на английский язык"""
        return self.translate_text(text, 'en')
    
    def detect_language(self, text: str) -> Optional[str]:
        """
        Определяет язык текста
        
        Args:
            text: Текст для определения языка
            
        Returns:
            Код языка или None в случае ошибки
        """
        try:
            if not text or not text.strip():
                return None
                
            # Простая эвристика для определения языка
            # Проверяем наличие кириллических символов
            cyrillic_chars = 'аеёиоуыэюя'
            if any(char.lower() in cyrillic_chars for char in text):
                return 'ru'
            
            # Проверяем наличие латинских символов
            latin_chars = 'abcdefghijklmnopqrstuvwxyz'
            if any(char.lower() in latin_chars for char in text):
                return 'en'
                
            # Если нет ни кириллицы, ни латиницы, возвращаем None
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка определения языка: {e}")
            return None
