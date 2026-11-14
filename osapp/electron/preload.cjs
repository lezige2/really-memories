const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('os', {
  health: () => ipcRenderer.invoke('service:health'),
  start: () => ipcRenderer.invoke('service:start'),
  stop: () => ipcRenderer.invoke('service:stop'),
  ask: (text) => ipcRenderer.invoke('api:ask', text),
  memories: () => ipcRenderer.invoke('api:memories'),
  reset: () => ipcRenderer.invoke('api:reset'),
  status: () => ipcRenderer.invoke('api:status'),
  forget: (id) => ipcRenderer.invoke('api:forget', id),
  configGet: () => ipcRenderer.invoke('config:get'),
  configSet: (c) => ipcRenderer.invoke('config:set', c),
  autostartGet: () => ipcRenderer.invoke('autostart:get'),
  autostartSet: (v) => ipcRenderer.invoke('autostart:set', v),
  openPath: (p) => ipcRenderer.invoke('shell:open', p),
  onHotkey: (cb) => {
    const listener = (_e, action) => cb(action);
    ipcRenderer.on('hotkey', listener);
    return () => ipcRenderer.removeListener('hotkey', listener);
  },
  onRemember: (cb) => {
    const listener = (_e, payload) => cb(payload);
    ipcRenderer.on('remember', listener);
    return () => ipcRenderer.removeListener('remember', listener);
  }
});