// The one door between the claims page and this computer: "scan". The page
// cannot reach files, USB or anything else - only ask for a scan, and only
// the claims server's own page gets even that (checked in main.js).
"use strict";
const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("thunder", {
  scan: (opts) => ipcRenderer.invoke("thunder-scan", opts || {})
});
