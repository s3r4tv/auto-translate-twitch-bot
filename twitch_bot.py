import asyncio
import logging
import re
from typing import Dict, Set, Optional
from twitchio.ext import commands
from twitchio import Client
from translator_advanced import AdvancedTranslationService

class TranslateBot(commands.Bot):
    """Twitch бот с поддержкой переводов"""
    
    def __init__(self, access_token: str, client_id: str, nickname: str, channel: str):
        super().__init__(
            token=access_token,
            client_id=client_id,
            nick=nickname,
            prefix='!',
            initial_channels=[channel]
        )
        
        self.channel = channel
        self.translator = AdvancedTranslationService()
        self.logger = logging.getLogger(__name__)
        
        # Настройки перевода
        self.global_translate_enabled = True
        self.auto_translate_users: Set[str] = set()
        
        # Кэш для избежания повторных переводов
        self.translation_cache: Dict[str, str] = {}
        
        self.logger.info(f"Бот инициализирован для канала: {channel}")
        
    def has_moderator_privileges(self, message) -> bool:
        """Проверяет, имеет ли пользователь права модератора или является владельцем канала"""
        author = message.author
        
        # Проверяем, является ли пользователь модератором
        if author.is_mod:
            return True
            
        # Проверяем, является ли пользователь владельцем канала (broadcaster)
        if hasattr(author, 'is_broadcaster') and author.is_broadcaster:
            return True
            
        # Альтернативная проверка владельца канала по имени
        if author.name.lower() == self.channel.lower():
            return True
            
        return False
        
    async def event_ready(self):
        """Вызывается при успешном подключении к Twitch"""
        self.logger.info(f"Бот {self.nick} подключен к Twitch!")
        self.logger.info(f"Присоединился к каналу: {self.channel}")
        
        # Отправляем сообщение в чат о готовности бота
        ready_message = "🤖 Бот готов к работе! Доступные команды: !ru <текст>, !en <текст>, !auto @user on/off, !translate on/off, !status"
        try:
            await self.get_channel(self.channel).send(ready_message)
            self.logger.info(f"Сообщение о готовности отправлено в чат: {ready_message}")
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения о готовности: {e}")
        
    async def event_message(self, message):
        """Обрабатывает все входящие сообщения"""
        if message.echo:
            return
            
        # Логирование сообщения
        self.logger.info(f"[{message.author.name}]: {message.content}")
        
        # Проверка на команды
        if message.content.startswith('!'):
            await self.handle_commands(message)
        else:
            # Обработка обычных сообщений для авто-перевода
            await self.handle_auto_translate(message)
            
    async def handle_commands(self, message):
        """Обрабатывает команды бота"""
        content = message.content.lower().strip()
        author = message.author.name
        
        # Команда !ru
        if content.startswith('!ru '):
            text = message.content[4:].strip()
            if text:
                await self.handle_translate_command(message, text, 'ru')
            else:
                await message.channel.send(f"@{author} ❌ Укажите текст для перевода! Использование: !ru <текст>")
                
        # Команда !en
        elif content.startswith('!en '):
            text = message.content[4:].strip()
            if text:
                await self.handle_translate_command(message, text, 'en')
            else:
                await message.channel.send(f"@{author} ❌ Укажите текст для перевода! Использование: !en <текст>")
                
        # Команда !auto
        elif content.startswith('!auto '):
            await self.handle_auto_command(message)
            
        # Команда !translate
        elif content.startswith('!translate '):
            await self.handle_global_translate_command(message)
            
        # Команда !status - показывает статус бота
        elif content == '!status':
            await self.handle_status_command(message)
            
        # Обработка других команд через базовый класс
        else:
            await super().event_message(message)
            
    async def handle_translate_command(self, message, text: str, target_lang: str):
        """Обрабатывает команды перевода"""
        author = message.author.name
        
        # Проверка кэша
        cache_key = f"{text}_{target_lang}"
        if cache_key in self.translation_cache:
            translated_text = self.translation_cache[cache_key]
        else:
            # Выполнение перевода
            if target_lang == 'ru':
                translated_text = self.translator.translate_to_russian(text)
            else:
                translated_text = self.translator.translate_to_english(text)
                
            # Сохранение в кэш
            if translated_text:
                self.translation_cache[cache_key] = translated_text
                
        if translated_text:
            lang_name = "русский" if target_lang == 'ru' else "английский"
            response = f"@{author} write: {translated_text}"
            await message.channel.send(response)
            self.logger.info(f"✅ Перевод выполнен для {author} на {lang_name}: {text} -> {translated_text}")
        else:
            error_message = f"@{author} ❌ Ошибка перевода. Не удалось перевести текст. Попробуйте позже или проверьте правильность написания."
            await message.channel.send(error_message)
            self.logger.error(f"❌ Ошибка перевода для {author}: {text}")
            
    async def handle_auto_command(self, message):
        """Обрабатывает команду !auto"""
        content = message.content[6:].strip()  # Убираем '!auto '
        author = message.author.name
        
        # Проверка прав модератора или владельца канала
        if not self.has_moderator_privileges(message):
            await message.channel.send(f"@{author} 🚫 Эта команда доступна только модераторам и владельцу канала!")
            return
        
        # Парсинг команды: !auto @nickname on/off
        match = re.match(r'@(\w+)\s+(on|off)', content)
        if not match:
            await message.channel.send(f"@{author} ❌ Неверный формат команды! Использование: !auto @nickname on/off")
            return
            
        target_user = match.group(1).lower()
        action = match.group(2)
        
        if action == 'on':
            if target_user in self.auto_translate_users:
                await message.channel.send(f"ℹ️ @{author} Авто-перевод для @{target_user} уже включен!")
                return
            
            self.auto_translate_users.add(target_user)
            users_count = len(self.auto_translate_users)
            success_message = f"✅ @{author} Авто-перевод для @{target_user} успешно включен! Всего пользователей в списке автоперевода: {users_count}"
            await message.channel.send(success_message)
            self.logger.info(f"Авто-перевод включен для пользователя: {target_user} (команда от {author})")
        else:
            if target_user not in self.auto_translate_users:
                await message.channel.send(f"ℹ️ @{author} Авто-перевод для @{target_user} уже отключен!")
                return
                
            self.auto_translate_users.discard(target_user)
            users_count = len(self.auto_translate_users)
            success_message = f"🔴 @{author} Авто-перевод для @{target_user} успешно отключен. Осталось пользователей в списке автоперевода: {users_count}"
            await message.channel.send(success_message)
            self.logger.info(f"Авто-перевод отключен для пользователя: {target_user} (команда от {author})")
            
    async def handle_global_translate_command(self, message):
        """Обрабатывает команду !translate"""
        content = message.content[11:].strip()  # Убираем '!translate '
        author = message.author.name
        
        # Проверка прав модератора или владельца канала
        if not self.has_moderator_privileges(message):
            await message.channel.send(f"@{author} 🚫 Эта команда доступна только модераторам и владельцу канала!")
            return
            
        if content == 'on':
            if self.global_translate_enabled:
                await message.channel.send(f"ℹ️ @{author} Глобальный перевод уже включен!")
                return
                
            self.global_translate_enabled = True
            users_count = len(self.auto_translate_users)
            success_message = f"🌐 @{author} Глобальный перевод успешно включен! Активно пользователей в автопереводе: {users_count}. Бот готов к работе!"
            await message.channel.send(success_message)
            self.logger.info(f"Глобальный перевод включен (команда от {author})")
        elif content == 'off':
            if not self.global_translate_enabled:
                await message.channel.send(f"ℹ️ @{author} Глобальный перевод уже отключен!")
                return
                
            self.global_translate_enabled = False
            success_message = f"🚫 @{author} Глобальный перевод успешно отключен. Автоматический перевод сообщений приостановлен для всех пользователей."
            await message.channel.send(success_message)
            self.logger.info(f"Глобальный перевод отключен (команда от {author})")
        else:
            await message.channel.send(f"@{author} ❌ Неверный формат команды. Использование: !translate on/off")
            
    async def handle_status_command(self, message):
        """Обрабатывает команду !status"""
        author = message.author.name
        
        # Собираем информацию о статусе
        global_status = "включен" if self.global_translate_enabled else "отключен"
        users_count = len(self.auto_translate_users)
        cache_size = len(self.translation_cache)
        
        # Формируем сообщение о статусе
        status_message = f"📊 @{author} Статус бота: Глобальный перевод {global_status} | Пользователей в автопереводе: {users_count} | Переводов в кэше: {cache_size}"
        
        await message.channel.send(status_message)
        self.logger.info(f"Статус бота запрошен пользователем {author}")
            
    async def handle_auto_translate(self, message):
        """Обрабатывает автоматический перевод сообщений"""
        if not self.global_translate_enabled:
            return
            
        author = message.author.name.lower()
        content = message.content.strip()
        
        # Проверка, нужно ли переводить сообщение
        user_in_auto_list = author in self.auto_translate_users
        should_auto_detect = self.should_auto_translate_message(content)
        
        # Для пользователей в списке автоперевода проверяем специальную логику
        if user_in_auto_list:
            should_translate = self.should_translate_for_auto_user(content)
        else:
            should_translate = should_auto_detect
        
        if should_translate and content:
            # Логируем для отладки
            self.logger.info(f"🔍 Проверка автоперевода для {message.author.name}: user_in_auto_list={user_in_auto_list}, should_auto_detect={should_auto_detect}")
            
            # Определяем доминирующий язык в сообщении
            latin_chars = len(re.findall(r'[a-zA-Z]', content))
            cyrillic_chars = len(re.findall(r'[а-яё]', content, re.IGNORECASE))
            total_chars = len(re.findall(r'[a-zA-Zа-яё]', content, re.IGNORECASE))
            
            if total_chars > 0:
                latin_percent = (latin_chars / total_chars) * 100
                cyrillic_percent = (cyrillic_chars / total_chars) * 100
                
                self.logger.info(f"🔍 Анализ языка для '{content}': латиница {latin_percent:.1f}%, кириллица {cyrillic_percent:.1f}%")
                
                # Определяем направление перевода
                if user_in_auto_list:
                    # Для пользователей в списке автоперевода - переводим на противоположный язык
                    if cyrillic_percent > 50 and latin_percent < 50:
                        # Преобладает русский - переводим на английский
                        translated_text = self.translator.translate_to_english(content)
                        target_lang = "английский"
                        self.logger.info(f"🔄 Автоперевод для {message.author.name}: русский -> английский")
                    elif latin_percent > 50 and cyrillic_percent < 50:
                        # Преобладает английский - переводим на русский
                        translated_text = self.translator.translate_to_russian(content)
                        target_lang = "русский"
                        self.logger.info(f"🔄 Автоперевод для {message.author.name}: английский -> русский")
                    else:
                        # Смешанный язык - не переводим
                        self.logger.info(f"⏭️ Смешанный язык для {message.author.name} - пропускаем")
                        return
                        
                    if translated_text and translated_text != content:
                        response = f"@{message.author.name} write: {translated_text}"
                        await message.channel.send(response)
                        self.logger.info(f"🔄 Авто-перевод для {message.author.name} на {target_lang}: {content} -> {translated_text}")
                        
                # Если автоматическое определение - переводим только английский на русский
                elif should_auto_detect:
                    translated_text = self.translator.translate_to_russian(content)
                    if translated_text and translated_text != content:
                        response = f"@{message.author.name} write: {translated_text}"
                        await message.channel.send(response)
                        self.logger.info(f"🔄 Авто-перевод для {message.author.name}: {content} -> {translated_text}")
            else:
                self.logger.info(f"⏭️ Нет букв для анализа в сообщении: '{content}'")
                        
    def should_auto_translate_message(self, content: str) -> bool:
        """Определяет, нужно ли автоматически переводить сообщение (для автоматического определения)"""
        if len(content) < 3:
            return False
            
        # Подсчитываем количество символов каждого языка
        latin_chars = len(re.findall(r'[a-zA-Z]', content))
        cyrillic_chars = len(re.findall(r'[а-яё]', content, re.IGNORECASE))
        total_chars = len(re.findall(r'[a-zA-Zа-яё]', content, re.IGNORECASE))
        
        if total_chars == 0:
            return False
            
        # Вычисляем процент каждого языка
        latin_percent = (latin_chars / total_chars) * 100
        cyrillic_percent = (cyrillic_chars / total_chars) * 100
        
        # Для автоматического определения: переводим только английский на русский
        # если английский составляет больше 50%
        return latin_percent > 50
        
    def should_translate_for_auto_user(self, content: str) -> bool:
        """Определяет, нужно ли переводить сообщение для пользователя в списке автоперевода"""
        if len(content) < 3:
            return False
            
        # Подсчитываем количество символов каждого языка
        latin_chars = len(re.findall(r'[a-zA-Z]', content))
        cyrillic_chars = len(re.findall(r'[а-яё]', content, re.IGNORECASE))
        total_chars = len(re.findall(r'[a-zA-Zа-яё]', content, re.IGNORECASE))
        
        if total_chars == 0:
            return False
            
        # Вычисляем процент каждого языка
        latin_percent = (latin_chars / total_chars) * 100
        cyrillic_percent = (cyrillic_chars / total_chars) * 100
        
        # Переводим только если один язык составляет БОЛЬШЕ 50% (не равно!)
        # И второй язык составляет МЕНЬШЕ 50%
        return (latin_percent > 50 and cyrillic_percent < 50) or (cyrillic_percent > 50 and latin_percent < 50)
        
    def get_status(self) -> Dict:
        """Возвращает статус бота"""
        return {
            'global_translate': self.global_translate_enabled,
            'auto_translate_users': list(self.auto_translate_users),
            'cache_size': len(self.translation_cache)
        }
        
    async def event_disconnect(self):
        """Вызывается при отключении от Twitch"""
        self.logger.info(f"Бот {self.nick} отключен от Twitch")
        
        # Отправляем сообщение в чат о завершении работы (если возможно)
        goodbye_message = "🤖 Бот завершает работу. До свидания!"
        try:
            channel = self.get_channel(self.channel)
            if channel:
                await channel.send(goodbye_message)
                self.logger.info(f"Сообщение о завершении работы отправлено в чат: {goodbye_message}")
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения о завершении: {e}")
            
    async def run(self):
        """Запускает бота"""
        try:
            self.logger.info("Запуск бота...")
            await self.start()
        except Exception as e:
            self.logger.error(f"Ошибка запуска бота: {e}")
            raise
