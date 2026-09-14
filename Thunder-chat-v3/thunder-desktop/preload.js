const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("thunderDesktop", {
  isDesktop: true,
  newWindow: () => ipcRenderer.invoke("new-window"),
  getApi: () => ipcRenderer.invoke("get-api"),
  setApi: (api) => ipcRenderer.invoke("set-api", api),
  openSettings: () => ipcRenderer.invoke("open-settings"),
  pickFiles: () => ipcRenderer.invoke("pick-files"),
  pickFolder: () => ipcRenderer.invoke("pick-folder"),
  saveBytes: (folder, name, b64) => ipcRenderer.invoke("save-bytes", folder, name, b64),
  openPath: (p) => ipcRenderer.invoke("open-path", p),
});
