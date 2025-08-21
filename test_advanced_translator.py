#!/usr/bin/env python3
"""
Тест улучшенного переводчика с поддержкой сленга
"""

import asyncio
import logging
from translator_advanced import AdvancedTranslationService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_translator():
    """Тестирует улучшенный переводчик"""
    translator = AdvancedTranslationService()
    
    # Тестовые фразы с сленгом и сокращениями
    test_cases = [
        # Русский -> Английский
        ("привет, как дела?", "ru"),
        ("круто, спасибо!", "ru"),
        ("вау, это офигенно!", "ru"),
        ("лол, забавно", "ru"),
        ("имхо, это не очень", "ru"),
        
        # Английский -> Русский
        ("hello, how are you?", "en"),
        ("cool, thanks!", "en"),
        ("wow, that's awesome!", "en"),
        ("lol, funny", "en"),
        ("imo, that's not very good", "en"),
        
        # С эмодзи
        ("привет! 😊 как дела?", "ru"),
        ("wow! 🎉 that's amazing!", "en"),
        ("лол 😂 забавно", "ru"),
        ("cool! 👍 thanks", "en"),
    ]
    
    print("🧪 Тестирование улучшенного переводчика\n")
    
    for i, (text, target_lang) in enumerate(test_cases, 1):
        print(f"Тест {i}:")
        print(f"  Исходный текст: {text}")
        
        if target_lang == "ru":
            result = translator.translate_to_russian(text)
            direction = "EN -> RU"
        else:
            result = translator.translate_to_english(text)
            direction = "RU -> EN"
            
        print(f"  Направление: {direction}")
        print(f"  Результат: {result}")
        print(f"  Определенный язык: {translator.detect_language(text)}")
        print("-" * 50)
        
    # Показываем статистику
    stats = translator.get_stats()
    print("\n📊 Статистика переводов:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

if __name__ == "__main__":
    test_translator()
