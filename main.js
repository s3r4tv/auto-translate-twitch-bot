const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { TranslateBot } = require('./src/bot/twitch_bot.js');

let mainWindow;
let bot = null;
let botRunning = false;

function createWindow() {
  try {
    mainWindow = new BrowserWindow({
      width: 1200,
      height: 900,
      minWidth: 1000,
      minHeight: 800,
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false,
        enableRemoteModule: true
      },
      // icon: path.join(__dirname, 'assets/icon.png'),
      titleBarStyle: 'default',
      show: false,
      backgroundColor: '#1a1a1a'
    });

    // Убираем меню
    mainWindow.setMenuBarVisibility(false);

    mainWindow.loadFile('src/renderer/index.html');

    mainWindow.once('ready-to-show', () => {
      mainWindow.show();
    });

    mainWindow.on('closed', () => {
      mainWindow = null;
    });
    
    mainWindow.on('error', (error) => {
      console.error('Window error:', error);
    });
    
  } catch (error) {
    console.error('Error creating window:', error);
    app.quit();
  }
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC Handlers
ipcMain.handle('check-settings', async () => {
  try {
    const envPath = path.join(__dirname, '.env');
    if (!fs.existsSync(envPath)) {
      return { exists: false, missing: ['TWITCH_ACCESS_TOKEN', 'TWITCH_CLIENT_ID', 'TWITCH_NICKNAME', 'TWITCH_CHANNEL'] };
    }

    const envContent = fs.readFileSync(envPath, 'utf8');
    const requiredVars = ['TWITCH_ACCESS_TOKEN', 'TWITCH_CLIENT_ID', 'TWITCH_NICKNAME', 'TWITCH_CHANNEL'];
    const missing = [];

    for (const varName of requiredVars) {
      if (!envContent.includes(`${varName}=`)) {
        missing.push(varName);
      }
    }

    return { exists: missing.length === 0, missing };
  } catch (error) {
    console.error('Error checking settings:', error);
    return { exists: false, missing: ['Error reading settings'] };
  }
});

ipcMain.handle('save-settings', async (event, settings) => {
  try {
    // Валидация настроек
    if (!settings.accessToken || !settings.clientId || !settings.nickname || !settings.channel) {
      return { success: false, error: 'Все поля должны быть заполнены' };
    }
    
    if (settings.accessToken.length < 10) {
      return { success: false, error: 'Access Token слишком короткий' };
    }
    
    if (settings.clientId.length < 5) {
      return { success: false, error: 'Client ID слишком короткий' };
    }
    
    if (settings.nickname.length < 3) {
      return { success: false, error: 'Nickname слишком короткий' };
    }
    
    if (settings.channel.length < 3) {
      return { success: false, error: 'Channel слишком короткий' };
    }
    
    const envContent = `TWITCH_ACCESS_TOKEN=${settings.accessToken}
TWITCH_CLIENT_ID=${settings.clientId}
TWITCH_NICKNAME=${settings.nickname}
TWITCH_CHANNEL=${settings.channel}`;

    const envPath = path.join(__dirname, '.env');
    fs.writeFileSync(envPath, envContent);
    return { success: true };
  } catch (error) {
    console.error('Error saving settings:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('load-settings', async () => {
  try {
    const envPath = path.join(__dirname, '.env');
    if (!fs.existsSync(envPath)) {
      return { success: false, error: 'Settings file not found' };
    }

    const envContent = fs.readFileSync(envPath, 'utf8');
    const lines = envContent.split('\n');
    const settings = {};

    lines.forEach(line => {
      const trimmedLine = line.trim();
      if (trimmedLine && !trimmedLine.startsWith('#')) {
        const equalIndex = trimmedLine.indexOf('=');
        if (equalIndex > 0) {
          const key = trimmedLine.substring(0, equalIndex).trim();
          const value = trimmedLine.substring(equalIndex + 1).trim();
          
          switch (key) {
            case 'TWITCH_ACCESS_TOKEN':
              settings.accessToken = value;
              break;
            case 'TWITCH_CLIENT_ID':
              settings.clientId = value;
              break;
            case 'TWITCH_NICKNAME':
              settings.nickname = value;
              break;
            case 'TWITCH_CHANNEL':
              settings.channel = value;
              break;
          }
        }
      }
    });

    return { success: true, data: settings };
  } catch (error) {
    console.error('Error loading settings:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('start-bot', async (event) => {
  if (botRunning) {
    return { success: false, error: 'Bot is already running' };
  }

  try {
    const envPath = path.join(__dirname, '.env');
    if (!fs.existsSync(envPath)) {
      return { success: false, error: 'Settings not found. Please configure the bot first.' };
    }

    require('dotenv').config({ path: envPath });

    const accessToken = process.env.TWITCH_ACCESS_TOKEN;
    const clientId = process.env.TWITCH_CLIENT_ID;
    const nickname = process.env.TWITCH_NICKNAME;
    const channel = process.env.TWITCH_CHANNEL;

    if (!accessToken || !clientId || !nickname || !channel) {
      return { success: false, error: 'Missing required settings' };
    }

    // Дополнительная валидация токенов
    if (accessToken.length < 10 || clientId.length < 5 || nickname.length < 3 || channel.length < 3) {
      return { success: false, error: 'Invalid settings format' };
    }

    bot = new TranslateBot(accessToken, clientId, nickname, channel);
    
    // Set up logging to send to renderer
    bot.on('log', (message) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('bot-log', message);
      }
    });

    await bot.start();
    botRunning = true;

    return { success: true };
  } catch (error) {
    console.error('Error starting bot:', error);
    // Сброс состояния при ошибке
    bot = null;
    botRunning = false;
    return { success: false, error: error.message };
  }
});

ipcMain.handle('stop-bot', async (event) => {
  if (!botRunning || !bot) {
    return { success: false, error: 'Bot is not running' };
  }

  try {
    await bot.stop();
    bot = null;
    botRunning = false;
    
    // Уведомляем renderer о остановке бота
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('bot-stopped');
    }
    
    return { success: true };
  } catch (error) {
    console.error('Error stopping bot:', error);
    return { success: false, error: error.message };
  }
});

ipcMain.handle('get-bot-status', () => {
  if (bot && botRunning) {
    try {
      return {
        running: botRunning,
        ...bot.getStatus()
      };
    } catch (error) {
      console.error('Error getting bot status:', error);
      return { 
        running: false,
        autoTranslateUsers: [],
        cacheSize: 0,
        errors: 0,
        operations: { active: 0, queued: 0 }
      };
    }
  }
  return { 
    running: false,
    autoTranslateUsers: [],
    cacheSize: 0,
    errors: 0,
    operations: { active: 0, queued: 0 }
  };
});
