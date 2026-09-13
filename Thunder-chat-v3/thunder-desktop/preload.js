const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("thunderDesktop", {
  isDesktop: true,
  newWindow: () => ipcRenderer.invoke("new-window"),
  pickFiles: () => ipcRenderer.invoke("pick-files"),
  pickFolder: () => ipcRenderer.invoke("pick-folder"),
  saveBytes: (folder, name, b64) => ipcRenderer.invoke("save-bytes", folder, name, b64),
  openPath: (p) => ipcRenderer.invoke("open-path", p),
});
