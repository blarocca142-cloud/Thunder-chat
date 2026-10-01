// Thunder Claims - the desktop program.
//
// A window onto the claims server on Main and nothing else. What makes it more
// than a browser tab is what it refuses to do:
//
// - It trusts exactly one certificate authority, the Thunder fleet CA bundled
//   with it (the same one the phone app carries). Windows' own trust store is
//   not consulted, so no other issuer - public or corporate - can stand in for
//   Main. The server certificate must be signed by that CA, be in date, and
//   name the address being dialled.
// - It will not load, navigate to, or open windows onto any other origin.
// - It keeps nothing on the laptop: an in-memory session, so no cookies,
//   cache or storage outlive the window. (Exports and prints are the office's
//   deliberate choice, and go where they choose.)
// - It grants the page no permissions (camera, location, notifications...).
//
// The server address defaults to https://10.168.168.10:8770 and can be changed
// in %APPDATA%/Thunder Claims/config.json ("server"), or THUNDER_CLAIMS_URL.
"use strict";
const { app, BrowserWindow, Menu, dialog, ipcMain, session, shell } = require("electron");
const { execFile } = require("child_process");
const os = require("os");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const DEFAULT_SERVER = "https://10.168.168.10:8770";

function readConfig() {
  const file = path.join(app.getPath("userData"), "config.json");
  let cfg = {};
  try { cfg = JSON.parse(fs.readFileSync(file, "utf8")); } catch (_) { /* first run */ }
  if (!cfg.server) {
    cfg.server = DEFAULT_SERVER;
    try { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, JSON.stringify(cfg, null, 2)); } catch (_) {}
  }
  return { file, server: process.env.THUNDER_CLAIMS_URL || cfg.server };
}

function caPath() {
  // A test CA, for the automated tests only. Ignored in the installed program,
  // which only ever trusts the bundled fleet CA.
  if (!app.isPackaged && process.env.THUNDER_CLAIMS_TEST_CA) return process.env.THUNDER_CLAIMS_TEST_CA;
  const packaged = path.join(process.resourcesPath || "", "thunder_ca.crt");
  return fs.existsSync(packaged) ? packaged : path.join(__dirname, "thunder_ca.crt");
}

let CA, SERVER, ORIGIN, HOST, win = null;
const CA_FINGERPRINT = () => CA.fingerprint256;

// Our own chain check, replacing Chromium's: signed by the fleet CA, in date,
// and issued for the host we dialled. Anything else is refused outright.
function certOk(hostname, pem) {
  if (hostname !== HOST) return false;
  const leaf = new crypto.X509Certificate(pem);
  if (!leaf.verify(CA.publicKey)) return false;
  const now = Date.now();
  if (now < Date.parse(leaf.validFrom) || now > Date.parse(leaf.validTo)) return false;
  const isIp = /^[0-9.]+$/.test(hostname) || hostname.includes(":");
  return isIp ? leaf.checkIP(hostname) !== undefined : leaf.checkHost(hostname) !== undefined;
}

function showOffline(reason) {
  if (!win) return;
  const q = new URLSearchParams({ server: SERVER, reason: String(reason || "") });
  win.loadFile(path.join(__dirname, "offline.html"), { search: q.toString() });
}

function createWindow() {
  const ses = session.fromPartition("thunder-claims"); // no "persist:" prefix: memory only
  ses.setCertificateVerifyProc((req, cb) => {
    let ok = false;
    try { ok = certOk(req.hostname, req.certificate.data); } catch (_) { ok = false; }
    cb(ok ? 0 : -2);
  });
  ses.setPermissionRequestHandler((_wc, _perm, cb) => cb(false));
  ses.setPermissionCheckHandler(() => false);
  ses.webRequest.onBeforeRequest({ urls: ["http://*/*", "https://*/*", "ws://*/*", "wss://*/*"] }, (d, cb) => {
    cb({ cancel: !d.url.startsWith(ORIGIN + "/") && d.url !== ORIGIN });
  });
  ses.on("will-download", (_e, item) => {
    item.setSaveDialogOptions({ title: "Save export", defaultPath: path.join(app.getPath("downloads"), item.getFilename()) });
  });

  win = new BrowserWindow({
    width: 1440, height: 920, minWidth: 900, minHeight: 600, show: false,
    title: "Thunder Claims", backgroundColor: "#efe8d8",
    icon: path.join(__dirname, "build", "icon.png"),
    webPreferences: {
      session: ses, contextIsolation: true, sandbox: true, nodeIntegration: false,
      preload: path.join(__dirname, "preload.js"), plugins: true,  // plugins: the built-in PDF viewer for scanned documents
      devTools: !app.isPackaged, spellcheck: false, webviewTag: false
    }
  });
  win.once("ready-to-show", () => { win.maximize(); win.show(); });
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.on("will-navigate", (e, url) => { if (!url.startsWith(ORIGIN + "/") && !url.startsWith("file:")) e.preventDefault(); });
  win.webContents.on("will-attach-webview", (e) => e.preventDefault());
  // The page asks before discarding unsaved claims; Electron would otherwise
  // cancel the close silently.
  win.webContents.on("will-prevent-unload", (e) => {
    const r = dialog.showMessageBoxSync(win, {
      type: "warning", buttons: ["Close without saving", "Go back"], defaultId: 1, cancelId: 1,
      title: "Thunder Claims", message: "Some records have unsaved changes.", detail: "Close anyway and lose them?"
    });
    if (r === 0) e.preventDefault();
  });
  win.webContents.on("did-fail-load", (_e, code, desc, url, isMain) => {
    if (isMain && url.startsWith(ORIGIN)) showOffline(desc + " (" + code + ")");
  });
  win.webContents.on("page-title-updated", (e, title) => { e.preventDefault(); win.setTitle(title.replace(/ - Thunder Claims$/, "") + " - Thunder Claims"); });
  win.on("closed", () => { win = null; });
  win.loadURL(ORIGIN + "/");
}

// Scanning: the page asks, this computer's scanner answers through Windows'
// own scanner service (WIA, scan.ps1). Pages go back to the page as data and
// the temporary folder is deleted at once - nothing stays on the laptop.
function scanResource() {
  const packaged = path.join(process.resourcesPath || "", "scan.ps1");
  return fs.existsSync(packaged) ? packaged : path.join(__dirname, "scan.ps1");
}
ipcMain.handle("thunder-scan", async (event) => {
  if (!event.senderFrame || !event.senderFrame.url.startsWith(ORIGIN + "/")) return { error: "not allowed" };
  if (process.platform !== "win32") return { error: "Scanning works on the office Windows computers." };
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "thunder-scan-"));
  try {
    const out = await new Promise((resolve) => {
      execFile("powershell.exe", ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", scanResource(), "-OutDir", dir],
        { timeout: 10 * 60 * 1000, windowsHide: true, maxBuffer: 1024 * 1024 }, (err, stdout) => resolve(String(stdout || "") + (err && !stdout ? "ERROR: " + err.message : "")));
    });
    const lines = out.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    const bad = lines.find((l) => l.startsWith("ERROR:"));
    const files = lines.filter((l) => l.toLowerCase().endsWith(".jpg") && path.dirname(l) === dir && fs.existsSync(l));
    if (!files.length) return { error: bad ? bad.slice(6).trim() : "Nothing was scanned." };
    return { pages: files.map((f) => ({ type: "image/jpeg", data: fs.readFileSync(f).toString("base64") })) };
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

function buildMenu() {
  const about = () => dialog.showMessageBox(win, {
    type: "info", title: "About Thunder Claims",
    message: "Thunder Claims " + app.getVersion(),
    detail: "Server: " + SERVER + "\nTrusts only: " + CA.subject.replace(/\n/g, ", ") +
      "\nCA fingerprint (SHA-256):\n" + CA_FINGERPRINT() +
      "\n\nNothing is stored on this computer. Nothing is ever sent to a payer."
  });
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { label: "File", submenu: [
      { label: "Reconnect", accelerator: "F5", click: () => win && win.loadURL(ORIGIN + "/") },
      { type: "separator" },
      { label: "Server Address…", click: () => {
        const { file } = readConfig();
        dialog.showMessageBox(win, { type: "info", title: "Server address", message: SERVER,
          detail: "To change it, edit \"server\" in:\n" + file + "\nthen restart Thunder Claims.", buttons: ["OK", "Open folder"] })
          .then((r) => { if (r.response === 1) shell.showItemInFolder(file); });
      } },
      { type: "separator" },
      { role: "quit", label: "Exit" }
    ] },
    { label: "Edit", submenu: [{ role: "undo" }, { role: "redo" }, { type: "separator" }, { role: "cut" }, { role: "copy" }, { role: "paste" }, { role: "selectAll" }] },
    { label: "View", submenu: [{ role: "resetZoom" }, { role: "zoomIn" }, { role: "zoomOut" }, { type: "separator" }, { role: "togglefullscreen" }] },
    { label: "Help", submenu: [{ label: "About Thunder Claims", click: about }] }
  ]));
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => { if (win) { if (win.isMinimized()) win.restore(); win.focus(); } });
  app.whenReady().then(() => {
    CA = new crypto.X509Certificate(fs.readFileSync(caPath()));
    SERVER = readConfig().server.replace(/\/+$/, "");
    const u = new URL(SERVER);
    if (u.protocol !== "https:") {
      dialog.showErrorBox("Thunder Claims", "The server address must start with https://\n\n" + SERVER);
      app.quit(); return;
    }
    ORIGIN = u.origin; HOST = u.hostname.replace(/^\[|\]$/g, "");
    buildMenu();
    createWindow();
    // Offline page asks to retry via a custom scheme-free trick: it reloads
    // itself with #retry, which we watch for here.
    win.webContents.on("did-navigate-in-page", (_e, url) => { if (url.endsWith("#retry")) win.loadURL(ORIGIN + "/"); });
  });
  app.on("window-all-closed", () => app.quit());
  app.on("before-quit", () => {
    const ses = session.fromPartition("thunder-claims");
    ses.clearStorageData().catch(() => {}); ses.clearCache().catch(() => {});
  });
}
