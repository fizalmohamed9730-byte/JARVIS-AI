const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  clipboard: {
    readText: () => ipcRenderer.invoke('get-clipboard-text'),
    writeText: (text) => ipcRenderer.invoke('set-clipboard-text', text),
  },

  system: {
    getInfo: () => ipcRenderer.invoke('get-system-info'),
  },

  notification: {
    show: (options) => ipcRenderer.invoke('show-notification', options),
  },

  dialog: {
    showOpen: (options) => ipcRenderer.invoke('show-open-dialog', options),
    showSave: (options) => ipcRenderer.invoke('show-save-dialog', options),
  },

  window: {
    minimize: () => ipcRenderer.invoke('window-minimize'),
    maximize: () => ipcRenderer.invoke('window-maximize'),
    close: () => ipcRenderer.invoke('window-close'),
    isMaximized: () => ipcRenderer.invoke('is-maximized'),
  },

  shell: {
    openExternal: (url) => ipcRenderer.invoke('open-external', url),
  },
});
