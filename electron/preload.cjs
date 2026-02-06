const { contextBridge, ipcRenderer } = require("electron");
const { pathToFileURL } = require("node:url");

contextBridge.exposeInMainWorld("api", {
  selectVideos: () => ipcRenderer.invoke("select-videos"),
  selectOutputDir: () => ipcRenderer.invoke("select-output-dir"),
  loadStrategies: () => ipcRenderer.invoke("load-strategies"),
  getAppVersion: () => ipcRenderer.invoke("app-version"),
  runtimeStatus: () => ipcRenderer.invoke("runtime-status"),
  runtimeInstall: () => ipcRenderer.invoke("runtime-install"),
  runDedupe: (payload) => ipcRenderer.invoke("run-dedupe", payload),
  openPublishLogin: () => ipcRenderer.invoke("open-publish-login"),
  openPublishPage: () => ipcRenderer.invoke("open-publish-page"),
  closePublish: () => ipcRenderer.invoke("close-publish"),
  publishFiles: (payload) => ipcRenderer.invoke("publish-files", payload),
  showItemInFolder: (filePath) => ipcRenderer.invoke("show-item-in-folder", filePath),
  openVideoPreview: (filePath) => ipcRenderer.invoke("open-video-preview", filePath),
  toFileUrl: (filePath) => {
    try {
      if (!filePath) return "";
      return pathToFileURL(String(filePath)).href;
    } catch {
      return "";
    }
  }
});
