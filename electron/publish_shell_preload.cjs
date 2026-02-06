const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("publishShell", {
  nav: (action) => ipcRenderer.invoke("publish-nav", action),
  state: () => ipcRenderer.invoke("publish-nav-state")
});

