#!/usr/bin/env python3
"""
Тестовый скрипт для демонстрации функциональности Twitch Translate Bot
"""

import logging
from translator import TranslationService

def setup_logging():
    """Настраивает логирование для тестов"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_translations():
    """Тестирует функции перевода"""
    print("🧪 Тестирование функций перевода...")
    print("=" * 50)
    
    translator = TranslationService()
    
    # Тестовые фразы
    test_phrases = [
        ("Hello, how are you?", "en", "ru"),
        ("Привет, как дела?", "ru", "en"),
        ("Good morning!", "en", "ru"),
        ("Доброе утро!", "ru", "en"),
        ("I love programming", "en", "ru"),
        ("Я люблю программирование", "ru", "en"),
    ]
    
    for text, source_lang, target_lang in test_phrases:
        print(f"\n📝 Исходный текст: {text}")
        print(f"🌐 Перевод с {source_lang} на {target_lang}:")
        
        if target_lang == 'ru':
            result = translator.translate_to_russian(text)
        else:
            result = translator.translate_to_english(text)
            
        if result:
            print(f"✅ Результат: {result}")
        else:
            print("❌ Ошибка перевода")
            
    print("\n" + "=" * 50)

def test_language_detection():
    """Тестирует определение языка"""
    print("\n🔍 Тестирование определения языка...")
    print("=" * 50)
    
    translator = TranslationService()
    
    test_texts = [
        "Hello world",
        "Привет мир",
        "Programming is fun",
        "Программирование это весело",
        "123456",
        "!@#$%^"
    ]
    
    for text in test_texts:
        detected = translator.detect_language(text)
        print(f"📝 '{text}' -> {detected or 'не определен'}")
        
    print("=" * 50)

def show_bot_commands():
    """Показывает доступные команды бота"""
    print("\n🤖 Команды Twitch Translate Bot:")
    print("=" * 50)
    print("• !ru <текст> - перевод на русский язык")
    print("• !en <текст> - перевод на английский язык")
    print("• !auto @nickname on/off - авто-перевод для пользователя")
    print("• !translate on/off - глобальный перевод (модераторы)")
    print("=" * 50)

def main():
    """Главная функция тестирования"""
    print("🎮 Twitch Translate Bot - Тестирование")
    print("=" * 60)
    
    setup_logging()
    
    try:
        # Тест переводов
        test_translations()
        
        # Тест определения языка
        test_language_detection()
        
        # Показ команд
        show_bot_commands()
        
        print("\n✅ Все тесты завершены успешно!")
        print("\n💡 Для запуска бота используйте: python main.py")
        
    except Exception as e:
        print(f"\n❌ Ошибка во время тестирования: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\nНажмите Enter для выхода...")
        input()
