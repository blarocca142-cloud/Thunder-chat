const { app, BrowserWindow, Tray, Menu, globalShortcut, ipcMain, dialog, shell, nativeImage } = require("electron");
const fs = require("fs");
const path = require("path");

const ICON = path.join(__dirname, "icon.png");
const WEB = path.join(__dirname, "..", "thunder-web", "index.html");
const PREFS = path.join(app.getPath("userData"), "thunder-desktop.json");

let tray = null;

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

function loadTarget() {
  const api = prefs().api || "http://127.0.0.1:8080";
  return { api, query: `?surface=desktop&api=${encodeURIComponent(api)}` };
}

function createWindow() {
  const { api, query } = loadTarget();
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
  const remote = `${api.replace(/\/$/, "")}/${query}`;
  win.loadURL(remote).catch(() => {
    win.loadFile(WEB, { query: { surface: "desktop", api } });
  });
  return win;
}

function makeTray() {
  const image = nativeImage.createFromPath(ICON).resize({ width: 24, height: 24 });
  tray = new Tray(image);
  tray.setToolTip("Thunder");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "New chat window", click: () => createWindow() },
      { label: "Studio", click: () => { const w = createWindow(); w.webContents.on("did-finish-load", () => w.webContents.executeJavaScript("document.getElementById('tabStudio')?.click()")); } },
      { type: "separator" },
      {
        label: "Main URL…",
        click: async () => {
          const current = prefs();
          const { response } = await dialog.showMessageBox({
            type: "question",
            buttons: ["Keep", "Use 127.0.0.1:8080"],
            message: `Current Main: ${current.api}`,
          });
          if (response === 1) {
            savePrefs({ ...current, api: "http://127.0.0.1:8080" });
          }
        },
      },
      { type: "separator" },
      { label: "Quit Thunder", click: () => app.quit() },
    ])
  );
  tray.on("click", () => {
    const existing = BrowserWindow.getAllWindows()[0];
    if (existing) existing.show();
    else createWindow();
  });
}

app.whenReady().then(() => {
  createWindow();
  makeTray();
  globalShortcut.register("CommandOrControl+Shift+T", () => {
    const win = BrowserWindow.getAllWindows()[0] || createWindow();
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
