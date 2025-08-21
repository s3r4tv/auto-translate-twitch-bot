#!/usr/bin/env python3
"""
Twitch Translate Bot - GUI версия с постоянным интерфейсом
"""

import os
import sys
import logging
import asyncio
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from dotenv import load_dotenv
from auth_gui import AuthGUI
from twitch_bot import TranslateBot

class BotGUI:
    """Графический интерфейс для управления ботом"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Twitch Translate Bot - Управление")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        self.root.minsize(800, 600)
        
        # Настройка темной темы
        self.setup_dark_theme()
        
        # Переменные
        self.bot = None
        self.bot_thread = None
        self.bot_running = False
        
        # Настройка логирования
        self.setup_logging()
        
        # Создание интерфейса
        self.setup_ui()
        
        # Проверка настроек
        self.check_settings()
        
    def setup_dark_theme(self):
        """Настройка темной темы"""
        self.bg_color = "#2b2b2b"
        self.fg_color = "#ffffff"
        self.entry_bg = "#3c3c3c"
        self.entry_fg = "#ffffff"
        self.button_bg = "#4a4a4a"
        self.button_fg = "#ffffff"
        self.success_bg = "#2b4a2b"
        self.error_bg = "#4a2b2b"
        
        # Применение стилей
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('TFrame', background=self.bg_color)
        style.configure('TLabel', background=self.bg_color, foreground=self.fg_color)
        style.configure('TButton', background=self.button_bg, foreground=self.button_fg)
        style.configure('TEntry', fieldbackground=self.entry_bg, foreground=self.entry_fg)
        style.configure('TLabelframe', background=self.bg_color, foreground=self.fg_color)
        style.configure('TLabelframe.Label', background=self.bg_color, foreground=self.fg_color)
        
        self.root.configure(bg=self.bg_color)
        
    def setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bot.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Основной контейнер
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="🎮 Twitch Translate Bot", 
                               font=("Arial", 18, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Статус бота
        self.status_frame = ttk.LabelFrame(main_frame, text="📊 Статус бота", padding="10")
        self.status_frame.pack(fill="x", pady=(0, 20))
        
        self.status_label = ttk.Label(self.status_frame, text="❌ Бот не запущен", 
                                     font=("Arial", 12, "bold"), foreground="red")
        self.status_label.pack()
        
        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(0, 20))
        
        self.start_button = tk.Button(button_frame, text="🚀 Запустить бота", 
                                     command=self.start_bot,
                                     bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                                     relief="raised", bd=2, padx=20, pady=10)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = tk.Button(button_frame, text="⏹️ Остановить бота", 
                                    command=self.stop_bot,
                                    bg="#f44336", fg="white", font=("Arial", 12, "bold"),
                                    relief="raised", bd=2, padx=20, pady=10,
                                    state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.settings_button = tk.Button(button_frame, text="⚙️ Настройки", 
                                        command=self.open_settings,
                                        bg="#2196F3", fg="white", font=("Arial", 12, "bold"),
                                        relief="raised", bd=2, padx=20, pady=10)
        self.settings_button.pack(side=tk.LEFT)
        
        # Лог бота
        log_frame = ttk.LabelFrame(main_frame, text="📝 Лог бота", padding="10")
        log_frame.pack(fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            bg=self.entry_bg,
            fg=self.entry_fg,
            font=("Consolas", 10),
            wrap=tk.WORD,
            state="disabled"
        )
        self.log_text.pack(fill="both", expand=True)
        
        # Кнопки лога
        log_button_frame = ttk.Frame(log_frame)
        log_button_frame.pack(fill="x", pady=(10, 0))
        
        clear_log_button = tk.Button(log_button_frame, text="🗑️ Очистить лог", 
                                    command=self.clear_log,
                                    bg="#FF9800", fg="white", font=("Arial", 10),
                                    relief="raised", bd=1, padx=10, pady=5)
        clear_log_button.pack(side=tk.LEFT)
        
        # Информация о командах
        info_frame = ttk.LabelFrame(main_frame, text="💡 Команды бота", padding="10")
        info_frame.pack(fill="x", pady=(20, 0))
        
        commands_text = """• !ru <текст> - перевод на русский
• !en <текст> - перевод на английский  
• !auto @nickname on/off - авто-перевод для пользователя
• !translate on/off - глобальный перевод (модераторы)"""
        
        commands_label = ttk.Label(info_frame, text=commands_text, 
                                  font=("Arial", 10), justify=tk.LEFT)
        commands_label.pack(anchor=tk.W)
        
    def check_settings(self):
        """Проверяет настройки бота"""
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
                
        if missing_vars:
            self.log_message("⚠️ Отсутствуют настройки. Нажмите 'Настройки' для конфигурации.")
            self.status_label.config(text="❌ Требуется настройка", foreground="orange")
        else:
            self.log_message("✅ Настройки найдены. Бот готов к запуску.")
            self.status_label.config(text="✅ Готов к запуску", foreground="green")
            
    def log_message(self, message):
        """Добавляет сообщение в лог"""
        try:
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        except:
            pass  # Игнорируем ошибки если GUI уже закрыт или вызывается из другого потока
        
    def start_bot(self):
        """Запускает бота"""
        if self.bot_running:
            messagebox.showwarning("Предупреждение", "Бот уже запущен!")
            return
            
        # Проверка настроек
        load_dotenv()
        if not os.getenv('TWITCH_ACCESS_TOKEN'):
            messagebox.showerror("Ошибка", "Не настроены данные авторизации!")
            return
            
        try:
            # Сохраняем данные авторизации для создания бота в отдельном потоке
            self.auth_data = {
                'access_token': os.getenv('TWITCH_ACCESS_TOKEN'),
                'client_id': os.getenv('TWITCH_CLIENT_ID'),
                'nickname': os.getenv('TWITCH_NICKNAME'),
                'channel': os.getenv('TWITCH_CHANNEL')
            }
            
            # Запуск бота в отдельном потоке
            self.bot_running = True
            self.bot_thread = threading.Thread(target=self.run_bot_async, daemon=True)
            self.bot_thread.start()
            
            # Обновление интерфейса
            self.status_label.config(text="🟢 Бот запущен", foreground="green")
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            
            self.log_message("🚀 Бот запускается...")
            
        except Exception as e:
            self.log_message(f"❌ Ошибка запуска бота: {e}")
            messagebox.showerror("Ошибка", f"Не удалось запустить бота: {e}")
            
    def run_bot_async(self):
        """Запускает бота асинхронно"""
        try:
            # Создаем новый event loop для этого потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Создаем бота в этом потоке
            self.bot = TranslateBot(
                access_token=self.auth_data['access_token'],
                client_id=self.auth_data['client_id'],
                nickname=self.auth_data['nickname'],
                channel=self.auth_data['channel']
            )
            
            # Перенаправляем логи бота в GUI (заменяем стандартную функцию логирования)
            original_log = self.bot.logger.info
            def custom_log(message):
                original_log(message)
                # Добавляем в GUI лог
                try:
                    if "подключен к Twitch" in message:
                        print(f"✅ {message}")
                    elif "Перевод для" in message:
                        print(f"🔄 {message}")
                    elif "Присоединился к каналу" in message:
                        print(f"🎮 {message}")
                    else:
                        print(f"📝 {message}")
                except:
                    pass
            
            self.bot.logger.info = custom_log
            
            # Запускаем бота
            print("🔄 Подключение к Twitch...")
            loop.run_until_complete(self.bot.start())
            
        except Exception as e:
            error_msg = f"❌ Ошибка в работе бота: {e}"
            self.root.after(0, lambda: self.log_message(error_msg))
            self.root.after(0, self.stop_bot)
        finally:
            try:
                loop.close()
            except:
                pass
            
    def stop_bot(self):
        """Останавливает бота"""
        if not self.bot_running:
            return
            
        try:
            self.log_message("🔄 Остановка бота...")
            
            if self.bot:
                # Сначала отправляем сообщение в чат о завершении работы
                try:
                    # Создаем временный event loop для отправки сообщения
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def send_goodbye():
                        try:
                            channel = self.bot.get_channel(self.bot.channel)
                            if channel:
                                goodbye_message = "🤖 Бот завершает работу. До свидания!"
                                await channel.send(goodbye_message)
                                self.log_message("📤 Сообщение о завершении работы отправлено в чат")
                        except Exception as e:
                            self.log_message(f"⚠️ Не удалось отправить сообщение в чат: {e}")
                    
                    # Выполняем отправку сообщения
                    loop.run_until_complete(send_goodbye())
                    loop.close()
                    
                except Exception as e:
                    self.log_message(f"⚠️ Ошибка отправки сообщения в чат: {e}")
                
                # Небольшая задержка, чтобы сообщение успело отправиться
                import time
                time.sleep(1)
            
            # Теперь останавливаем бота
            self.bot_running = False
            self.bot = None
            
            # Обновление интерфейса
            self.status_label.config(text="❌ Бот остановлен", foreground="red")
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            
            self.log_message("⏹️ Бот остановлен")
            
        except Exception as e:
            self.log_message(f"❌ Ошибка остановки бота: {e}")
            
    def open_settings(self):
        """Открывает окно настроек"""
        try:
            # Создаем окно настроек в отдельном потоке
            auth_gui = AuthGUI()
            
            # Запускаем в отдельном потоке для избежания конфликтов
            def run_auth_gui():
                try:
                    auth_gui.run()
                except Exception as e:
                    print(f"Ошибка в AuthGUI: {e}")
                finally:
                    # Проверяем настройки после закрытия
                    self.root.after(100, self.check_settings)
            
            # Запускаем в отдельном потоке
            auth_thread = threading.Thread(target=run_auth_gui, daemon=True)
            auth_thread.start()
            
        except Exception as e:
            self.log_message(f"❌ Ошибка открытия настроек: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть настройки: {e}")
            
    def clear_log(self):
        """Очищает лог"""
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
        
    def on_closing(self):
        """Обработчик закрытия окна"""
        if self.bot_running:
            if messagebox.askokcancel("Выход", "Бот запущен. Остановить и выйти?"):
                self.stop_bot()
                self.root.destroy()
        else:
            self.root.destroy()
            
    def run(self):
        """Запускает GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

def main():
    """Главная функция"""
    app = BotGUI()
    app.run()

if __name__ == "__main__":
    main()
