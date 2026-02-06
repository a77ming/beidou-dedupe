import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("api", {
  selectVideos: () => ipcRenderer.invoke("select-videos"),
  loadStrategies: () => ipcRenderer.invoke("load-strategies"),
  runDedupe: (payload) => ipcRenderer.invoke("run-dedupe", payload)
});
