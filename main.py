#!/usr/bin/env python3
"""
Twitch Translate Bot - главный файл приложения
"""

import os
import sys
import logging
import asyncio
from dotenv import load_dotenv
from auth_gui import AuthGUI
from twitch_bot import TranslateBot

def setup_logging():
    """Настраивает логирование"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )
    
def check_environment():
    """Проверяет наличие необходимых переменных окружения"""
    load_dotenv()
    
    required_vars = [
        'TWITCH_ACCESS_TOKEN',
        'TWITCH_CLIENT_ID',
        'TWITCH_NICKNAME', 
        'TWITCH_CHANNEL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            
    return missing_vars

def get_auth_data():
    """Получает данные авторизации из .env файла"""
    load_dotenv()
    
    return {
        'access_token': os.getenv('TWITCH_ACCESS_TOKEN'),
        'refresh_token': os.getenv('TWITCH_REFRESH_TOKEN', ''),
        'client_id': os.getenv('TWITCH_CLIENT_ID'),
        'nickname': os.getenv('TWITCH_NICKNAME'),
        'channel': os.getenv('TWITCH_CHANNEL')
    }

def show_welcome_message():
    """Показывает приветственное сообщение"""
    print("=" * 60)
    print("🎮 Twitch Translate Bot")
    print("=" * 60)
    print("Функции бота:")
    print("• !ru <текст> - перевод на русский")
    print("• !en <текст> - перевод на английский")
    print("• !auto @nickname on/off - авто-перевод для пользователя")
    print("• !translate on/off - глобальный перевод (модераторы)")
    print("=" * 60)

async def run_bot():
    """Запускает бота"""
    logger = logging.getLogger(__name__)
    
    try:
        # Получение данных авторизации
        auth_data = get_auth_data()
        
        # Создание и запуск бота
        bot = TranslateBot(
            access_token=auth_data['access_token'],
            client_id=auth_data['client_id'],
            nickname=auth_data['nickname'],
            channel=auth_data['channel']
        )
        
        logger.info("Запуск бота...")
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        return False
        
    return True

def main():
    """Главная функция приложения"""
    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Показ приветственного сообщения
    show_welcome_message()
    
    # Проверка переменных окружения
    missing_vars = check_environment()
    
    if missing_vars:
        logger.info("Отсутствуют данные авторизации. Запуск GUI для настройки...")
        
        # Запуск GUI для настройки
        try:
            auth_gui = AuthGUI()
            auth_gui.run()
            
            # Проверка после закрытия GUI
            missing_vars = check_environment()
            if missing_vars:
                logger.error(f"Не заполнены обязательные поля: {', '.join(missing_vars)}")
                print("❌ Ошибка: Не все обязательные поля заполнены.")
                print("Запустите программу снова для настройки.")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка GUI: {e}")
            print("❌ Ошибка запуска интерфейса настройки.")
            return False
    
    # Запуск бота
    logger.info("Все данные авторизации найдены. Запуск бота...")
    print("🚀 Запуск бота...")
    
    try:
        # Простой запуск бота
        asyncio.run(run_bot())
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"❌ Критическая ошибка: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\nНажмите Enter для выхода...")
        input()
        sys.exit(1)
