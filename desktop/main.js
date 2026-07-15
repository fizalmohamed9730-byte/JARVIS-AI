const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage, dialog, clipboard, Notification, shell } = require('electron');
const path = require('path');
const { autoUpdater } = require('electron-updater');

let mainWindow = null;
let tray = null;
const gotLock = app.requestSingleInstanceLock();

if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  function createWindow() {
    mainWindow = new BrowserWindow({
      width: 1200,
      height: 800,
      minWidth: 800,
      minHeight: 600,
      backgroundColor: '#0f172a',
      frame: true,
      titleBarStyle: 'hiddenInset',
      show: false,
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: false,
      },
    });

    const isDev = process.env.NODE_ENV === 'development';

    if (isDev) {
      mainWindow.loadURL('http://localhost:5173');
      mainWindow.webContents.openDevTools({ mode: 'detach' });
    } else {
      mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'));
    }

    mainWindow.once('ready-to-show', () => {
      mainWindow.show();
    });

    mainWindow.on('close', (e) => {
      if (!app.isQuitting) {
        e.preventDefault();
        mainWindow.hide();
      }
    });

    mainWindow.on('closed', () => {
      mainWindow = null;
    });

    createTray();
    setupIPC();
    setupAutoUpdater();
  }

  function createTray() {
    const icon = nativeImage.createEmpty();
    tray = new Tray(icon);
    tray.setToolTip('JARVIS AI');

    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Show JARVIS',
        click: () => {
          if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
          }
        },
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => {
          app.isQuitting = true;
          app.quit();
        },
      },
    ]);

    tray.setContextMenu(contextMenu);

    tray.on('double-click', () => {
      if (mainWindow) {
        mainWindow.show();
        mainWindow.focus();
      }
    });
  }

  function setupIPC() {
    ipcMain.handle('get-clipboard-text', () => clipboard.readText());
    ipcMain.handle('set-clipboard-text', (_, text) => clipboard.writeText(text));

    ipcMain.handle('get-system-info', () => ({
      platform: process.platform,
      arch: process.arch,
      version: app.getVersion(),
      electronVersion: process.versions.electron,
      chromeVersion: process.versions.chrome,
      nodeVersion: process.versions.node,
      memoryUsage: process.memoryUsage(),
    }));

    ipcMain.handle('show-notification', (_, { title, body, silent }) => {
      new Notification({ title, body, silent: silent || false }).show();
    });

    ipcMain.handle('show-open-dialog', async (_, options) => {
      const result = await dialog.showOpenDialog(mainWindow, options);
      return result;
    });

    ipcMain.handle('show-save-dialog', async (_, options) => {
      const result = await dialog.showSaveDialog(mainWindow, options);
      return result;
    });

    ipcMain.handle('window-minimize', () => mainWindow?.minimize());
    ipcMain.handle('window-maximize', () => {
      if (mainWindow?.isMaximized()) {
        mainWindow.unmaximize();
      } else {
        mainWindow?.maximize();
      }
    });
    ipcMain.handle('window-close', () => mainWindow?.close());
    ipcMain.handle('is-maximized', () => mainWindow?.isMaximized() ?? false);

    ipcMain.handle('open-external', (_, url) => shell.openExternal(url));
  }

  function setupAutoUpdater() {
    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = true;

    autoUpdater.on('update-available', async (info) => {
      const response = await dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'Update Available',
        message: `JARVIS ${info.version} is available. Download now?`,
        buttons: ['Download', 'Later'],
      });

      if (response.response === 0) {
        autoUpdater.downloadUpdate();
      }
    });

    autoUpdater.on('update-downloaded', async () => {
      const response = await dialog.showMessageBox(mainWindow, {
        type: 'info',
        title: 'Update Ready',
        message: 'Update downloaded. Restart to apply?',
        buttons: ['Restart', 'Later'],
      });

      if (response.response === 0) {
        autoUpdater.quitAndInstall();
      }
    });

    autoUpdater.checkForUpdates().catch(() => {});
  }

  app.whenReady().then(createWindow);

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      app.quit();
    }
  });

  app.on('activate', () => {
    if (mainWindow === null) {
      createWindow();
    } else {
      mainWindow.show();
    }
  });

  app.on('before-quit', () => {
    app.isQuitting = true;
  });
}
