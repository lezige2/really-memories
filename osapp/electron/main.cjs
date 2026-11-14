const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, shell, globalShortcut } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, execFile } = require('child_process');

const ROOT = process.env.LLAMA_MEM_ROOT || 'D:\\llama-mem';
const PY = process.env.LLAMA_MEM_PYTHON || 'C:\\Users\\lezige\\AppData\\Local\\Programs\\Python\\Python314\\python.exe';
const API = process.env.LLAMA_MEM_API || 'http://127.0.0.1:8765';
const CONFIG = path.join(app.getPath('userData'), 'config.json');

let win = null;
let tray = null;
let quitting = false;

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.exit(0);
}
app.on('second-instance', () => {
  if (win) {
    if (win.isMinimized()) win.restore();
    win.show();
    win.focus();
  }
});

function readConfig() {
  try { return JSON.parse(fs.readFileSync(CONFIG, 'utf8')); } catch { return {}; }
}
function writeConfig(c) {
  fs.mkdirSync(path.dirname(CONFIG), { recursive: true });
  fs.writeFileSync(CONFIG, JSON.stringify(c, null, 2));
}

async function health() {
  try {
    const r = await fetch(API + '/health', { signal: AbortSignal.timeout(1500) });
    return { ok: r.ok, status: r.status };
  } catch (e) {
    return { ok: false, error: String(e.message || e) };
  }
}

function spawnService() {
  const launcher = path.join(ROOT, 'out', 'ops', 'launch_service.py');
  if (!fs.existsSync(launcher)) return { ok: false, error: 'launcher not found: ' + launcher };
  const p = spawn(PY, ['-X', 'utf8', launcher], {
    cwd: ROOT, detached: true, stdio: 'ignore', windowsHide: true
  });
  p.unref();
  return { ok: true, pid: p.pid };
}

function stopService() {
  return new Promise((resolve) => {
    execFile('netstat', ['-ano'], { windowsHide: true }, (err, stdout) => {
      if (err) return resolve({ ok: false, error: err.message });
      const line = String(stdout).split(/\r?\n/).find(l => /:8765\s+.*LISTENING/i.test(l));
      if (!line) return resolve({ ok: true, stopped: false, note: 'not listening' });
      const pid = line.trim().split(/\s+/).pop();
      execFile('taskkill', ['/PID', pid, '/F'], { windowsHide: true }, (e2) => {
        resolve({ ok: !e2, pid, error: e2 ? e2.message : null });
      });
    });
  });
}

async function apiJson(pathname, opts = {}) {
  const r = await fetch(API + pathname, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    signal: AbortSignal.timeout(opts.timeout || 60000)
  });
  const text = await r.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { raw: text }; }
  return { ok: r.ok, status: r.status, data };
}

function createWindow() {
  win = new BrowserWindow({
    width: 1180, height: 780, minWidth: 900, minHeight: 600,
    backgroundColor: '#0b0d10',
    title: 'llama-mem',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  win.webContents.on('console-message', (_e, level, message, line, source) => {
    console.log('CONSOLE', level, message, source + ':' + line);
  });
  win.webContents.on('did-fail-load', (_e, code, desc) => {
    console.error('LOAD_FAIL', code, desc);
  });
  const dev = process.env.VITE_DEV_SERVER_URL;
  if (dev) win.loadURL(dev);
  else win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  if (process.env.OSAPP_SHOT) {
    win.webContents.once('did-finish-load', () => {
      setTimeout(async () => {
        try {
          const img = await win.webContents.capturePage();
          fs.writeFileSync(process.env.OSAPP_SHOT, img.toPNG());
        } catch (e) { console.error('shot failed', e); }
        quitting = true;
        app.quit();
      }, 2500);
    });
  }
  win.on('close', (e) => {
    if (!quitting) { e.preventDefault(); win.hide(); }
  });
}

function showWindow(focusChat = false) {
  if (!win) return;
  if (win.isMinimized()) win.restore();
  win.show();
  win.focus();
  if (focusChat) win.webContents.send('hotkey', 'chat');
}

function createTray() {
  const iconPath = path.join(__dirname, 'icon.png');
  const img = fs.existsSync(iconPath) ? nativeImage.createFromPath(iconPath) : nativeImage.createEmpty();
  tray = new Tray(img);
  tray.setToolTip('llama-mem');
  const menu = Menu.buildFromTemplate([
    { label: '打开 llama-mem', click: () => showWindow(false) },
    { label: '显示/隐藏', click: () => { if (win && win.isVisible()) win.hide(); else showWindow(false); } },
    { type: 'separator' },
    { label: '启动本地服务', click: () => spawnService() },
    { label: '停止本地服务', click: () => stopService() },
    { type: 'separator' },
    { label: '退出', click: () => { quitting = true; app.quit(); } }
  ]);
  tray.setContextMenu(menu);
  tray.on('double-click', () => showWindow(false));
}

app.whenReady().then(() => {
  createWindow();
  createTray();
  const ok1 = globalShortcut.register('CommandOrControl+Alt+M', () => showWindow(true));
  const ok2 = globalShortcut.register('CommandOrControl+Alt+Q', () => showWindow(true));
  console.log('hotkeys', { memory: ok1, ask: ok2 });
  if (readConfig().autoService) spawnService();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

app.on('will-quit', () => { globalShortcut.unregisterAll(); });
app.on('before-quit', () => { quitting = true; });
app.on('window-all-closed', () => { /* keep tray alive */ });

ipcMain.handle('service:health', health);
ipcMain.handle('service:start', spawnService);
ipcMain.handle('service:stop', stopService);
ipcMain.handle('api:ask', async (_e, text) => apiJson('/ask', { method: 'POST', body: JSON.stringify({ text }) }));
ipcMain.handle('api:memories', async () => apiJson('/memories'));
ipcMain.handle('api:forget', async (_e, id) => apiJson('/forget', { method: 'POST', body: JSON.stringify({ id }) }));
ipcMain.handle('config:get', () => readConfig());
ipcMain.handle('config:set', (_e, c) => { writeConfig(c); return true; });
ipcMain.handle('autostart:get', () => app.getLoginItemSettings().openAtLogin);
ipcMain.handle('autostart:set', (_e, v) => { app.setLoginItemSettings({ openAtLogin: !!v }); return true; });
ipcMain.handle('shell:open', (_e, p) => shell.openPath(p));