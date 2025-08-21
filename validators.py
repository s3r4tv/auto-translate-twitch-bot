import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Результат валидации"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class InputValidator:
    """Валидатор пользовательского ввода"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.max_text_length = 500
        self.supported_languages = {'ru', 'en'}
        
        # Паттерны для проверки безопасности
        self.dangerous_patterns = [
            r'<script.*?>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'on\w+\s*=',
            r'<iframe.*?>',
            r'<object.*?>',
            r'<embed.*?>'
        ]
        
        # Паттерны для валидации Twitch имен
        self.twitch_username_pattern = r'^[a-zA-Z0-9_]{4,25}$'
        self.channel_name_pattern = r'^[a-zA-Z0-9_]{4,25}$'
        
    def validate_text(self, text: str) -> ValidationResult:
        """Валидация текста для перевода"""
        errors = []
        warnings = []
        
        if not text or not text.strip():
            errors.append("Текст не может быть пустым")
            return ValidationResult(False, errors, warnings)
            
        if len(text) > self.max_text_length:
            errors.append(f"Текст слишком длинный: {len(text)} символов (максимум {self.max_text_length})")
            
        # Проверка на опасные паттерны
        for pattern in self.dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append(f"Обнаружен опасный паттерн: {pattern}")
                
        # Проверка на специальные символы
        if text.count('@') > 5:
            warnings.append("Много упоминаний пользователей (@)")
            
        if text.count('#') > 3:
            warnings.append("Много хэштегов (#)")
            
        return ValidationResult(len(errors) == 0, errors, warnings)
        
    def validate_language(self, lang: str) -> ValidationResult:
        """Валидация языка"""
        errors = []
        warnings = []
        
        if not lang:
            errors.append("Язык не указан")
        elif lang not in self.supported_languages:
            errors.append(f"Неподдерживаемый язык: {lang}")
            
        return ValidationResult(len(errors) == 0, errors, warnings)
        
    def validate_twitch_username(self, username: str) -> ValidationResult:
        """Валидация имени пользователя Twitch"""
        errors = []
        warnings = []
        
        if not username:
            errors.append("Имя пользователя не указано")
        elif not re.match(self.twitch_username_pattern, username):
            errors.append(f"Некорректное имя пользователя: {username}")
            
        return ValidationResult(len(errors) == 0, errors, warnings)
        
    def validate_channel_name(self, channel: str) -> ValidationResult:
        """Валидация имени канала"""
        errors = []
        warnings = []
        
        if not channel:
            errors.append("Имя канала не указано")
        elif not re.match(self.channel_name_pattern, channel):
            errors.append(f"Некорректное имя канала: {channel}")
            
        return ValidationResult(len(errors) == 0, errors, warnings)
        
    def validate_command(self, command: str) -> ValidationResult:
        """Валидация команды бота"""
        errors = []
        warnings = []
        
        if not command:
            errors.append("Команда не указана")
            return ValidationResult(False, errors, warnings)
            
        # Проверяем формат команды
        if not command.startswith('!'):
            errors.append("Команда должна начинаться с '!'")
            
        # Проверяем длину команды
        if len(command) > 200:
            errors.append("Команда слишком длинная")
            
        # Проверяем на опасные символы
        dangerous_chars = ['<', '>', '"', "'", '&']
        for char in dangerous_chars:
            if char in command:
                warnings.append(f"Команда содержит специальный символ: {char}")
                
        return ValidationResult(len(errors) == 0, errors, warnings)
        
    def sanitize_text(self, text: str) -> str:
        """Очистка текста от потенциально опасных символов"""
        if not text:
            return ""
            
        # Удаляем HTML теги
        text = re.sub(r'<[^>]+>', '', text)
        
        # Экранируем специальные символы
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#39;')
        
        return text.strip()
        
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Валидация конфигурации"""
        errors = []
        warnings = []
        
        required_fields = ['access_token', 'client_id', 'nickname', 'channel']
        
        for field in required_fields:
            if field not in config or not config[field]:
                errors.append(f"Отсутствует обязательное поле: {field}")
                
        # Проверяем длину токенов
        if 'access_token' in config and config['access_token']:
            if len(config['access_token']) < 20:
                errors.append("Access Token слишком короткий")
                
        if 'client_id' in config and config['client_id']:
            if len(config['client_id']) < 10:
                errors.append("Client ID слишком короткий")
                
        return ValidationResult(len(errors) == 0, errors, warnings)
