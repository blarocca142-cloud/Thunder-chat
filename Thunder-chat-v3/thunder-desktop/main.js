const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, dialog, shell, nativeImage } = require("electron");
const fs = require("fs");
const path = require("path");

const ICON = path.join(__dirname, "icon.png");
const PREFS = path.join(app.getPath("userData"), "thunder-desktop.json");

let tray = null;
let settingsWin = null;

function prefs() {
  try {
    return JSON.parse(fs.readFileSync(PREFS, "utf8"));
  } catch {
    return { api: "http://127.0.0.1:8080" };
  }
}

function savePrefs(next) {
  fs.mkdirSync(path.dirname(PREFS), { recursive: true });
  fs.writeFileSync(PREFS, JSON.stringify(next, null, 2));
}

function currentApi() {
  return (prefs().api || "http://127.0.0.1:8080").trim().replace(/\/$/, "");
}

function webIndex() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "thunder-web", "index.html");
  }
  return path.join(__dirname, "..", "thunder-web", "index.html");
}

function applyApi(api, { reload = true } = {}) {
  const next = (api || "").trim().replace(/\/$/, "") || "http://127.0.0.1:8080";
  savePrefs({ ...prefs(), api: next });
  if (reload) {
    BrowserWindow.getAllWindows().forEach((win) => {
      if (win === settingsWin) return;
      win.loadFile(webIndex(), { query: { surface: "desktop", api: next } });
    });
  }
  return next;
}

function createWindow() {
  const api = currentApi();
  const win = new BrowserWindow({
    width: 1480,
    height: 920,
    minWidth: 1080,
    minHeight: 720,
    backgroundColor: "#16191F",
    title: "Thunder",
    icon: ICON,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.removeMenu();
  win.loadFile(webIndex(), { query: { surface: "desktop", api } });
  return win;
}

function openSettings() {
  if (settingsWin && !settingsWin.isDestroyed()) {
    settingsWin.show();
    settingsWin.focus();
    return;
  }
  settingsWin = new BrowserWindow({
    width: 460,
    height: 260,
    resizable: false,
    backgroundColor: "#1a1e26",
    title: "Thunder — Main URL",
    icon: ICON,
    parent: BrowserWindow.getFocusedWindow() || undefined,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  settingsWin.removeMenu();
  settingsWin.loadFile(path.join(__dirname, "settings.html"));
  settingsWin.on("closed", () => {
    settingsWin = null;
  });
}

function makeTray() {
  const image = nativeImage.createFromPath(ICON).resize({ width: 24, height: 24 });
  tray = new Tray(image);
  tray.setToolTip("Thunder");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "New chat window", click: () => createWindow() },
      {
        label: "Studio",
        click: () => {
          const w = createWindow();
          w.webContents.on("did-finish-load", () =>
            w.webContents.executeJavaScript("document.getElementById('tabStudio')?.click()")
          );
        },
      },
      { type: "separator" },
      { label: "Main URL…", click: () => openSettings() },
      { type: "separator" },
      { label: "Quit Thunder", click: () => app.quit() },
    ])
  );
  tray.on("click", () => {
    const existing = BrowserWindow.getAllWindows().find((w) => w !== settingsWin);
    if (existing) existing.show();
    else createWindow();
  });
}

app.whenReady().then(() => {
  createWindow();
  makeTray();
  globalShortcut.register("CommandOrControl+Shift+T", () => {
    const win = BrowserWindow.getAllWindows().find((w) => w !== settingsWin) || createWindow();
    win.show();
    win.focus();
  });
  app.on("activate", () => {
    if (!BrowserWindow.getAllWindows().length) createWindow();
  });
});

app.on("window-all-closed", (e) => {
  if (process.platform !== "darwin") e.preventDefault();
});

app.on("will-quit", () => globalShortcut.unregisterAll());

ipcMain.handle("new-window", () => {
  createWindow();
});

ipcMain.handle("get-api", () => currentApi());

ipcMain.handle("set-api", (_e, api) => applyApi(api));

ipcMain.handle("open-settings", () => openSettings());

ipcMain.handle("pick-files", async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog({
    properties: ["openFile", "multiSelections"],
    filters: [{ name: "Text / code", extensions: ["md", "txt", "py", "kt", "js", "ts", "json", "css", "html", "gradle"] }],
  });
  if (canceled) return [];
  return filePaths.slice(0, 6).map((filePath) => ({
    name: path.basename(filePath),
    text: fs.readFileSync(filePath, "utf8").slice(0, 120000),
  }));
});

ipcMain.handle("pick-folder", async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog({ properties: ["openDirectory", "createDirectory"] });
  return canceled ? null : filePaths[0];
});

ipcMain.handle("save-bytes", async (_e, folder, name, b64) => {
  if (!folder || !name) return false;
  const dest = path.join(folder, path.basename(name));
  fs.writeFileSync(dest, Buffer.from(b64, "base64"));
  return dest;
});

ipcMain.handle("open-path", async (_e, p) => {
  if (p) await shell.openPath(p);
});
