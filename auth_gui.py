import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
from dotenv import load_dotenv

class AuthGUI:
    """Графический интерфейс для авторизации в Twitch"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Twitch Translate Bot - Авторизация")
        self.root.geometry("800x900")
        self.root.resizable(True, True)
        self.root.minsize(750, 800)
        
        # Настройка темной темы
        self.setup_dark_theme()
        
        # Центрирование окна
        self.center_window()
        
        # Переменные для хранения данных
        self.access_token = tk.StringVar()
        self.refresh_token = tk.StringVar()
        self.client_id = tk.StringVar()
        self.nickname = tk.StringVar()
        self.channel = tk.StringVar()
        
        self.setup_ui()
        self.load_existing_data()
        
    def setup_dark_theme(self):
        """Настройка темной темы"""
        # Цвета темной темы
        self.bg_color = "#2b2b2b"
        self.fg_color = "#ffffff"
        self.entry_bg = "#3c3c3c"
        self.entry_fg = "#ffffff"
        self.button_bg = "#4a4a4a"
        self.button_fg = "#ffffff"
        self.warning_bg = "#4a2b2b"
        self.warning_fg = "#ff6b6b"
        
        # Применение стилей
        style = ttk.Style()
        style.theme_use('clam')
        
        # Настройка основных стилей для темной темы
        style.configure('TFrame', background=self.bg_color, relief='flat', borderwidth=0)
        style.configure('TLabel', background=self.bg_color, foreground=self.fg_color, font=("Arial", 10))
        style.configure('TButton', background=self.button_bg, foreground=self.button_fg, borderwidth=1, focuscolor='none')
        style.configure('TEntry', fieldbackground=self.entry_bg, foreground=self.entry_fg, borderwidth=1, insertcolor=self.entry_fg)
        style.configure('TLabelframe', background=self.bg_color, foreground=self.fg_color, borderwidth=1, relief='solid')
        style.configure('TLabelframe.Label', background=self.bg_color, foreground=self.fg_color, font=("Arial", 10, "bold"))
        
        # Дополнительные стили для скроллбара
        style.configure('Vertical.TScrollbar', 
                       background=self.button_bg, 
                       troughcolor=self.bg_color,
                       bordercolor=self.bg_color,
                       arrowcolor=self.fg_color,
                       darkcolor=self.button_bg,
                       lightcolor=self.button_bg)
        
        # Настройка окна
        self.root.configure(bg=self.bg_color)
        
    def center_window(self):
        """Центрирует окно на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def setup_ui(self):
        """Настраивает пользовательский интерфейс"""
        # Создаем основной контейнер с прокруткой
        canvas = tk.Canvas(self.root, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Создаем окно в canvas для размещения фрейма
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Размещение элементов прокрутки
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Обработка прокрутки мышью
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Основной контейнер
        main_frame = ttk.Frame(scrollable_frame, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Обновляем область прокрутки после добавления содержимого
        def update_scroll_region():
            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Устанавливаем ширину фрейма равной ширине canvas
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())
        
        # Привязываем обновление области прокрутки
        scrollable_frame.bind("<Configure>", lambda e: update_scroll_region())
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="Настройка Twitch Translate Bot", 
                               font=("Arial", 18, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Инструкции в текстовом виджете с прокруткой
        instructions_frame = ttk.LabelFrame(main_frame, text="📋 Инструкции по настройке", padding="10")
        instructions_frame.pack(fill="x", pady=(0, 20))
        
        instructions = """ПОШАГОВАЯ НАСТРОЙКА TWITCH БОТА:

1. СОЗДАНИЕ БОТА:
   • Создайте отдельный Twitch аккаунт для бота (рекомендуется)
   • Или используйте существующий аккаунт

2. ПОЛУЧЕНИЕ ТОКЕНОВ:
   • Перейдите на https://twitchtokengenerator.com/
   • Выберите "Bot Chat Token"
   • Авторизуйтесь через аккаунт БОТА (не основной канал!)
   • Скопируйте: ACCESS TOKEN, REFRESH TOKEN, CLIENT ID

3. НАСТРОЙКА КАНАЛА:
   • В поле "Канал" укажите ВАШ стрим-канал (куда будет заходить бот)
   • В поле "Никнейм бота" укажите имя АККАУНТА БОТА

4. ВЫДАЧА ПРАВ (ВАЖНО!):
   • Зайдите в чат вашего канала
   • Выдайте боту права модератора: /mod имя_бота
   • Без прав модератора бот не сможет отвечать быстро"""
        
        instruction_text = scrolledtext.ScrolledText(
            instructions_frame, 
            font=("Arial", 10),
            wrap=tk.WORD,
            height=12,
            bg=self.entry_bg,
            fg=self.entry_fg,
            insertbackground=self.entry_fg,
            selectbackground="#555555",
            selectforeground=self.entry_fg,
            state="normal"
        )
        instruction_text.insert("1.0", instructions)
        instruction_text.config(state="disabled")
        instruction_text.pack(fill="both", expand=True)
        
        # Поля ввода
        input_frame = ttk.LabelFrame(main_frame, text="🔑 Данные авторизации", padding="15")
        input_frame.pack(fill="x", pady=(0, 20))
        
        # Access Token
        token_frame = ttk.Frame(input_frame)
        token_frame.pack(fill="x", pady=5)
        ttk.Label(token_frame, text="Access Token:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        access_entry = tk.Entry(token_frame, textvariable=self.access_token, show="*", 
                               bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg,
                               font=("Arial", 10), relief="solid", bd=1)
        access_entry.pack(fill="x", pady=(5, 0))
        
        # Refresh Token  
        refresh_frame = ttk.Frame(input_frame)
        refresh_frame.pack(fill="x", pady=5)
        ttk.Label(refresh_frame, text="Refresh Token:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        refresh_entry = tk.Entry(refresh_frame, textvariable=self.refresh_token, show="*",
                                bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg,
                                font=("Arial", 10), relief="solid", bd=1)
        refresh_entry.pack(fill="x", pady=(5, 0))
        
        # Client ID
        client_frame = ttk.Frame(input_frame)
        client_frame.pack(fill="x", pady=5)
        ttk.Label(client_frame, text="Client ID:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        client_entry = tk.Entry(client_frame, textvariable=self.client_id,
                               bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg,
                               font=("Arial", 10), relief="solid", bd=1)
        client_entry.pack(fill="x", pady=(5, 0))
        
        # Nickname
        nickname_frame = ttk.Frame(input_frame)
        nickname_frame.pack(fill="x", pady=5)
        ttk.Label(nickname_frame, text="Никнейм бота:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        nickname_entry = tk.Entry(nickname_frame, textvariable=self.nickname,
                                 bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg,
                                 font=("Arial", 10), relief="solid", bd=1)
        nickname_entry.pack(fill="x", pady=(5, 0))
        
        # Подсказка для никнейма
        ttk.Label(nickname_frame, text="(имя аккаунта бота, например: mybotname)", 
                 font=("Arial", 9), foreground="#aaaaaa").pack(anchor=tk.W, pady=(5, 0))
        
        # Channel
        channel_frame = ttk.Frame(input_frame)
        channel_frame.pack(fill="x", pady=5)
        ttk.Label(channel_frame, text="Ваш канал:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        channel_entry = tk.Entry(channel_frame, textvariable=self.channel,
                                bg=self.entry_bg, fg=self.entry_fg, insertbackground=self.entry_fg,
                                font=("Arial", 10), relief="solid", bd=1)
        channel_entry.pack(fill="x", pady=(5, 0))
        
        # Подсказка для канала
        ttk.Label(channel_frame, text="(имя вашего стрим-канала, например: yourchannelname)", 
                 font=("Arial", 9), foreground="#aaaaaa").pack(anchor=tk.W, pady=(5, 0))
        
        # Важное предупреждение
        warning_frame = ttk.LabelFrame(main_frame, text="⚠️ ВАЖНО - ОБЯЗАТЕЛЬНО ПРОЧИТАЙТЕ", padding="15")
        warning_frame.pack(fill="x", pady=(0, 20))
        
        warning_text = """После сохранения настроек и запуска бота:

1. Зайдите в чат вашего канала
2. Выдайте боту права модератора командой: /mod имя_бота
3. Проверьте, что бот появился в списке модераторов
4. Без прав модератора бот может не работать или работать медленно!

Пример: если никнейм бота "mytranslatebot", введите: /mod mytranslatebot"""
        
        warning_text_widget = scrolledtext.ScrolledText(
            warning_frame, 
            font=("Arial", 10),
            wrap=tk.WORD,
            height=8,
            bg=self.warning_bg,
            fg=self.warning_fg,
            insertbackground=self.warning_fg,
            selectbackground="#555555",
            selectforeground=self.warning_fg,
            state="normal"
        )
        warning_text_widget.insert("1.0", warning_text)
        warning_text_widget.config(state="disabled")
        warning_text_widget.pack(fill="both", expand=True)
        
        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        save_button = tk.Button(button_frame, text="💾 Сохранить и запустить", 
                               command=self.save_and_exit,
                               bg="#4CAF50", fg="white", font=("Arial", 12, "bold"),
                               relief="raised", bd=2, padx=20, pady=10)
        save_button.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_button = tk.Button(button_frame, text="❌ Отмена", 
                                 command=self.cancel,
                                 bg="#f44336", fg="white", font=("Arial", 12, "bold"),
                                 relief="raised", bd=2, padx=20, pady=10)
        cancel_button.pack(side=tk.LEFT)
        
        # Принудительно обновляем область прокрутки после создания всех элементов
        self.root.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfig(canvas_window, width=canvas.winfo_width())
        
    def load_existing_data(self):
        """Загружает существующие данные из .env файла"""
        if os.path.exists('.env'):
            load_dotenv()
            
            if os.getenv('TWITCH_ACCESS_TOKEN'):
                self.access_token.set(os.getenv('TWITCH_ACCESS_TOKEN'))
            if os.getenv('TWITCH_REFRESH_TOKEN'):
                self.refresh_token.set(os.getenv('TWITCH_REFRESH_TOKEN'))
            if os.getenv('TWITCH_CLIENT_ID'):
                self.client_id.set(os.getenv('TWITCH_CLIENT_ID'))
            if os.getenv('TWITCH_NICKNAME'):
                self.nickname.set(os.getenv('TWITCH_NICKNAME'))
            if os.getenv('TWITCH_CHANNEL'):
                self.channel.set(os.getenv('TWITCH_CHANNEL'))
                
    def save_and_exit(self):
        """Сохраняет данные и закрывает окно"""
        # Проверка заполнения полей
        if not self.access_token.get().strip():
            messagebox.showerror("Ошибка", "Введите Access Token")
            return
            
        if not self.client_id.get().strip():
            messagebox.showerror("Ошибка", "Введите Client ID")
            return
            
        if not self.nickname.get().strip():
            messagebox.showerror("Ошибка", "Введите никнейм бота")
            return
            
        if not self.channel.get().strip():
            messagebox.showerror("Ошибка", "Введите канал")
            return
            
        # Сохранение в .env файл
        env_content = f"""# Twitch Translate Bot Configuration
TWITCH_ACCESS_TOKEN={self.access_token.get().strip()}
TWITCH_REFRESH_TOKEN={self.refresh_token.get().strip()}
TWITCH_CLIENT_ID={self.client_id.get().strip()}
TWITCH_NICKNAME={self.nickname.get().strip()}
TWITCH_CHANNEL={self.channel.get().strip()}
"""
        
        try:
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            messagebox.showinfo("Успех", "Данные сохранены! Бот запускается...")
            self.root.destroy()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить данные: {e}")
            
    def cancel(self):
        """Отменяет операцию и закрывает окно"""
        if messagebox.askokcancel("Отмена", "Вы уверены, что хотите отменить настройку?"):
            self.root.destroy()
            
    def on_closing(self):
        """Обработчик закрытия окна"""
        try:
            if hasattr(self, 'root') and self.root:
                self.root.quit()
                self.root.destroy()
        except Exception as e:
            print(f"Ошибка при закрытии AuthGUI: {e}")
            
    def run(self):
        """Запускает GUI"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            print(f"Ошибка в AuthGUI.run(): {e}")
        finally:
            try:
                if hasattr(self, 'root') and self.root:
                    self.root.destroy()
            except:
                pass
        
    def get_auth_data(self):
        """Возвращает данные авторизации"""
        return {
            'access_token': self.access_token.get().strip(),
            'refresh_token': self.refresh_token.get().strip(),
            'client_id': self.client_id.get().strip(),
            'nickname': self.nickname.get().strip(),
            'channel': self.channel.get().strip()
        }
