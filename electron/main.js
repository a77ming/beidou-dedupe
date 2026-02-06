import { app, BrowserWindow, BrowserView, dialog, ipcMain, Menu, shell } from "electron";
import path from "node:path";
import fs from "node:fs";
import { spawn } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { groupDuplicates } from "./dedupe.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isDev = !app.isPackaged;
const publishPartition = "persist:publish";
let mainWindow = null;
let publishWindow = null;
let publishView = null;
let previewWindow = null;

const PUBLISH_TOOLBAR_HEIGHT = 44;

function setPublishViewBounds() {
  if (!publishWindow || publishWindow.isDestroyed()) return;
  if (!publishView) return;

  const b = publishWindow.getContentBounds();
  publishView.setBounds({
    x: 0,
    y: PUBLISH_TOOLBAR_HEIGHT,
    width: b.width,
    height: Math.max(0, b.height - PUBLISH_TOOLBAR_HEIGHT)
  });
}

function attachPublishNavigation(win, view) {
  const wc = view.webContents;

  // Add browser-like navigation without changing the page UI:
  // - keyboard shortcuts (Cmd/Ctrl + [ / ] / R)
  // - right-click context menu (Back/Forward/Reload)
  win.webContents.on("before-input-event", (event, input) => {
    const key = String(input.key || "");
    const isMac = process.platform === "darwin";
    const cmdOrCtrl = isMac ? input.meta : input.control;

    // Back/Forward
    if (!input.alt && cmdOrCtrl && !input.shift && (key === "[" || key === "]")) {
      if (key === "[" && wc.canGoBack()) wc.goBack();
      if (key === "]" && wc.canGoForward()) wc.goForward();
      event.preventDefault();
      return;
    }

    // Reload / Force reload
    if (!input.alt && cmdOrCtrl && key.toLowerCase() === "r") {
      if (input.shift) wc.reloadIgnoringCache();
      else wc.reload();
      event.preventDefault();
      return;
    }

    // Windows/Linux common shortcuts
    if (!isMac && input.alt && !input.control && !input.meta && (key === "Left" || key === "Right")) {
      if (key === "Left" && wc.canGoBack()) wc.goBack();
      if (key === "Right" && wc.canGoForward()) wc.goForward();
      event.preventDefault();
      return;
    }

    // F5 reload
    if (key === "F5") {
      if (input.shift) wc.reloadIgnoringCache();
      else wc.reload();
      event.preventDefault();
    }
  });

  wc.on("context-menu", () => {
    const template = [
      {
        label: "Back",
        enabled: wc.canGoBack(),
        accelerator: process.platform === "darwin" ? "Command+[" : "Alt+Left",
        click: () => wc.goBack()
      },
      {
        label: "Forward",
        enabled: wc.canGoForward(),
        accelerator: process.platform === "darwin" ? "Command+]" : "Alt+Right",
        click: () => wc.goForward()
      },
      { type: "separator" },
      {
        label: "Reload",
        accelerator: "CmdOrCtrl+R",
        click: () => wc.reload()
      },
      {
        label: "Force Reload",
        accelerator: "CmdOrCtrl+Shift+R",
        click: () => wc.reloadIgnoringCache()
      },
      { type: "separator" },
      {
        label: "Close Window",
        accelerator: "CmdOrCtrl+W",
        click: () => win.close()
      }
    ];

    if (isDev) {
      template.push(
        { type: "separator" },
        {
          label: "DevTools",
          accelerator: process.platform === "darwin" ? "Alt+Command+I" : "Ctrl+Shift+I",
          click: () => wc.openDevTools({ mode: "detach" })
        }
      );
    }

    Menu.buildFromTemplate(template).popup({ window: win });
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 760,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  if (isDev) {
    const devUrl = process.env.VITE_DEV_SERVER_URL || "http://localhost:5173";
    mainWindow.loadURL(devUrl);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    mainWindow.loadFile(path.join(app.getAppPath(), "renderer", "index.html"));
  }

  return mainWindow;
}

function openPublishWindow(url) {
  if (publishWindow && !publishWindow.isDestroyed()) {
    if (publishView && !publishView.webContents.isDestroyed()) {
      publishView.webContents.loadURL(url);
    }
    publishWindow.show();
    publishWindow.focus();
    return publishWindow;
  }

  publishWindow = new BrowserWindow({
    width: 1100,
    height: 760,
    webPreferences: {
      preload: path.join(__dirname, "publish_shell_preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  publishWindow.setMenuBarVisibility(false);

  publishWindow.on("closed", () => {
    publishWindow = null;
    publishView = null;
  });

  publishWindow.on("resize", setPublishViewBounds);
  publishWindow.on("maximize", setPublishViewBounds);
  publishWindow.on("unmaximize", setPublishViewBounds);
  publishWindow.on("enter-full-screen", setPublishViewBounds);
  publishWindow.on("leave-full-screen", setPublishViewBounds);

  // Shell window hosts a fixed toolbar and a BrowserView for the remote publish site.
  publishWindow.loadFile(path.join(__dirname, "publish_shell.html"));

  publishView = new BrowserView({
    webPreferences: {
      partition: publishPartition,
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  // Keep navigation inside the same publish view so users don't get stuck
  // in newly-opened windows without controls.
  publishView.webContents.setWindowOpenHandler(({ url: targetUrl }) => {
    if (targetUrl) publishView.webContents.loadURL(targetUrl);
    return { action: "deny" };
  });
  publishWindow.setBrowserView(publishView);
  setPublishViewBounds();

  attachPublishNavigation(publishWindow, publishView);
  publishView.webContents.loadURL(url);

  return publishWindow;
}

function waitForLoad(webContents) {
  return new Promise((resolve, reject) => {
    const done = () => {
      cleanup();
      resolve();
    };
    const fail = (_event, _code, desc) => {
      cleanup();
      reject(new Error(desc));
    };
    const cleanup = () => {
      webContents.removeListener("did-finish-load", done);
      webContents.removeListener("did-fail-load", fail);
    };
    webContents.once("did-finish-load", done);
    webContents.once("did-fail-load", fail);
  });
}

app.whenReady().then(() => {
  // Ensure STRATEGY_URL is available as early as possible, but do not rely on it.
  // The packaged app may not have environment variables (Finder launch),
  // so we also support config.json as the source of the remote URL.
  bootstrapStrategyUrlFromConfig();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

function getEffectiveProcessorRoot() {
  const envRoot = process.env.SHORT_VIDEO_PROCESSOR_ROOT;
  if (envRoot && fs.existsSync(envRoot)) return envRoot;

  // Packaged app ships a minimal processor runtime in app.asar.unpacked/processor
  if (app.isPackaged) {
    const bundled = resolveUnpackedPath("processor");
    if (fs.existsSync(bundled)) return bundled;
    return null;
  }

  // Dev: prefer the local bundled processor if present.
  const localBundled = path.join(app.getAppPath(), "processor");
  if (fs.existsSync(localBundled)) return localBundled;

  return null;
}

function findBasePython() {
  const candidates = [
    process.env.PYTHON_PATH,
    "/opt/homebrew/bin/python3",
    "/usr/local/bin/python3",
    "/usr/bin/python3"
  ].filter(Boolean);

  for (const p of candidates) {
    try {
      if (fs.existsSync(p)) return p;
    } catch {
      // ignore
    }
  }
  return "python3";
}

function getVenvDir() {
  return path.join(app.getPath("userData"), "python-runtime");
}

function getVenvPython(venvDir) {
  if (process.platform === "win32") return path.join(venvDir, "Scripts", "python.exe");
  return path.join(venvDir, "bin", "python");
}

function spawnCapture(command, args, opts = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, { ...opts, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d.toString()));
    child.stderr.on("data", (d) => (stderr += d.toString()));
    child.on("error", (err) => resolve({ ok: false, code: null, stdout, stderr: stderr + String(err) }));
    child.on("close", (code) => resolve({ ok: code === 0, code, stdout, stderr }));
  });
}

async function checkPythonDeps(pythonPath, processorRoot) {
  const code = `
import json, sys
try:
    sys.path.insert(0, ${JSON.stringify(processorRoot)})
    from core.video_processor import VideoProcessor  # noqa: F401
    import numpy  # noqa: F401
    import cv2  # noqa: F401
    from moviepy import VideoFileClip  # noqa: F401
    from PIL import Image  # noqa: F401
    print(json.dumps({"ok": True}))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
    raise
`;
  const res = await spawnCapture(pythonPath, ["-c", code], { cwd: app.getPath("userData") });
  if (!res.ok) {
    // Try to extract the JSON error for a cleaner message.
    try {
      const line = (res.stdout || "").trim().split("\n").pop();
      const parsed = JSON.parse(line);
      if (parsed && parsed.ok === false && parsed.error) return { ok: false, error: parsed.error, raw: res };
    } catch {
      // ignore
    }
    return { ok: false, error: (res.stderr || res.stdout || "Unknown python error").trim(), raw: res };
  }
  return { ok: true };
}

async function ensureRuntime() {
  const processorRoot = getEffectiveProcessorRoot();
  if (!processorRoot) {
    return {
      ok: false,
      error: "Processor runtime not found.",
      processorRoot: null
    };
  }

  const basePython = findBasePython();
  const venvDir = getVenvDir();
  const venvPython = getVenvPython(venvDir);

  // Prefer venv if already created.
  if (fs.existsSync(venvPython)) {
    const dep = await checkPythonDeps(venvPython, processorRoot);
    return {
      ok: dep.ok,
      error: dep.ok ? null : dep.error,
      processorRoot,
      basePython,
      venvDir,
      venvPython,
      activePython: venvPython
    };
  }

  // Fall back to base python if deps are already present (developer machines).
  const dep = await checkPythonDeps(basePython, processorRoot);
  return {
    ok: dep.ok,
    error: dep.ok ? null : dep.error,
    processorRoot,
    basePython,
    venvDir,
    venvPython,
    activePython: basePython
  };
}

async function installRuntime() {
  const processorRoot = getEffectiveProcessorRoot();
  if (!processorRoot) {
    return { ok: false, error: "Processor runtime not found." };
  }

  const basePython = findBasePython();
  const venvDir = getVenvDir();
  const venvPython = getVenvPython(venvDir);

  // 1) create venv
  if (!fs.existsSync(venvPython)) {
    const mk = await spawnCapture(basePython, ["-m", "venv", venvDir], { cwd: app.getPath("userData") });
    if (!mk.ok) {
      return { ok: false, error: `Failed to create venv. ${mk.stderr || mk.stdout}`.trim() };
    }
  }

  // 2) install deps into venv
  const pipArgs = [
    "-m",
    "pip",
    "install",
    "--upgrade",
    "pip",
    "setuptools",
    "wheel",
    "moviepy>=2.0.0",
    "opencv-python>=4.8.0",
    "Pillow>=10.0.0",
    "numpy>=1.24.0",
    "imageio-ffmpeg>=0.4.9"
  ];
  const pip = await spawnCapture(venvPython, pipArgs, { cwd: app.getPath("userData") });
  if (!pip.ok) {
    return { ok: false, error: `pip install failed. ${pip.stderr || pip.stdout}`.trim() };
  }

  // 3) verify
  const dep = await checkPythonDeps(venvPython, processorRoot);
  if (!dep.ok) {
    return { ok: false, error: `Runtime installed, but import check failed: ${dep.error}` };
  }

  return { ok: true };
}

ipcMain.handle("select-videos", async () => {
  const result = await dialog.showOpenDialog({
    title: "Select Videos",
    properties: ["openFile", "multiSelections"],
    filters: [
      { name: "Videos", extensions: ["mp4", "mov", "mkv", "avi", "webm", "flv", "m4v"] },
      { name: "All Files", extensions: ["*"] }
    ]
  });

  if (result.canceled) return [];
  return result.filePaths;
});

ipcMain.handle("select-output-dir", async () => {
  const result = await dialog.showOpenDialog({
    title: "Select Output Folder",
    properties: ["openDirectory", "createDirectory"]
  });

  if (result.canceled) return null;
  return result.filePaths[0] || null;
});

ipcMain.handle("show-item-in-folder", async (_event, filePath) => {
  if (!filePath || typeof filePath !== "string") return false;
  try {
    // If it's a directory, open it directly; if it's a file, reveal it in the folder.
    if (fs.existsSync(filePath)) {
      try {
        const st = fs.statSync(filePath);
        if (st.isDirectory()) {
          await shell.openPath(filePath);
          return true;
        }
      } catch {
        // fall back to reveal
      }
    }

    shell.showItemInFolder(filePath);
    return true;
  } catch {
    return false;
  }
});

ipcMain.handle("open-video-preview", async (_event, filePath) => {
  if (!filePath || typeof filePath !== "string") return false;
  try {
    if (!previewWindow || previewWindow.isDestroyed()) {
      previewWindow = new BrowserWindow({
        width: 860,
        height: 540,
        title: "视频预览",
        autoHideMenuBar: true,
        webPreferences: {
          contextIsolation: true,
          nodeIntegration: false
        }
      });
      previewWindow.on("closed", () => {
        previewWindow = null;
      });
    }

    const href = pathToFileURL(filePath).href;
    await previewWindow.loadURL(href);
    previewWindow.show();
    previewWindow.focus();
    return true;
  } catch {
    return false;
  }
});

ipcMain.handle("open-publish-login", async () => {
  openPublishWindow("https://publish.inbeidou.cn/publish/login");
  return true;
});

ipcMain.handle("open-publish-page", async () => {
  openPublishWindow("https://publish.inbeidou.cn/publish/release");
  return true;
});

ipcMain.handle("publish-nav", async (_event, action) => {
  if (!publishWindow || publishWindow.isDestroyed() || !publishView) return false;
  const wc = publishView.webContents;
  if (wc.isDestroyed()) return false;

  switch (action) {
    case "back":
      if (wc.canGoBack()) wc.goBack();
      return true;
    case "forward":
      if (wc.canGoForward()) wc.goForward();
      return true;
    case "reload":
      wc.reload();
      return true;
    case "force-reload":
      wc.reloadIgnoringCache();
      return true;
    case "back-to-app":
      // Close the publish window and bring the main window to front.
      if (publishWindow && !publishWindow.isDestroyed()) publishWindow.close();
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.show();
        mainWindow.focus();
      } else if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
      }
      return true;
    default:
      return false;
  }
});

ipcMain.handle("publish-nav-state", async () => {
  if (!publishWindow || publishWindow.isDestroyed() || !publishView) {
    return { canGoBack: false, canGoForward: false, url: "" };
  }
  const wc = publishView.webContents;
  if (wc.isDestroyed()) return { canGoBack: false, canGoForward: false, url: "" };
  return { canGoBack: wc.canGoBack(), canGoForward: wc.canGoForward(), url: wc.getURL() || "" };
});

ipcMain.handle("close-publish", async () => {
  if (publishWindow && !publishWindow.isDestroyed()) {
    publishWindow.close();
  }
  publishWindow = null;
  publishView = null;
  return true;
});

ipcMain.handle("publish-files", async (_event, payload) => {
  const { filePaths, caption } = payload || {};
  if (!Array.isArray(filePaths) || filePaths.length === 0) {
    return { error: "No publish files." };
  }

  openPublishWindow("https://publish.inbeidou.cn/publish/release");
  if (!publishView) return { error: "Publish view not available." };
  await waitForLoad(publishView.webContents);

  await publishView.webContents.executeJavaScript(
    `(function(){const el=document.querySelector('textarea');if(el){el.value=${JSON.stringify(
      caption || ""
    )};el.dispatchEvent(new Event('input',{bubbles:true}));return true;}const ed=document.querySelector('[contenteditable=\"true\"]');if(ed){ed.innerText=${JSON.stringify(
      caption || ""
    )};ed.dispatchEvent(new Event('input',{bubbles:true}));return true;}return false;})()`
  );

  const inputFound = await publishView.webContents.executeJavaScript(
    `(function(){const input=document.querySelector('input[type=\"file\"]');if(input){input.focus();return true;}return false;})()`
  );

  if (!inputFound) {
    return { error: "File input not found on publish page." };
  }

  publishView.webContents.setFileInputFiles(filePaths);
  return { ok: true };
});

ipcMain.handle("load-strategies", async () => {
  const remoteUrl = getEffectiveStrategyUrl();
  if (!remoteUrl) {
    return {
      source: "remote",
      strategies: [],
      remoteUrl: null,
      error: "No strategy URL configured (STRATEGY_URL/config.json)."
    };
  }
  if (remoteUrl) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 6000);
      const res = await fetch(remoteUrl, { signal: controller.signal });
      clearTimeout(timeout);
      if (res.ok) {
        const text = await res.text();
        const remote = parseStrategies(text, "remote");
        if (remote.strategies.length > 0) return { ...remote, remoteUrl };
        return {
          source: "remote",
          strategies: [],
          remoteUrl,
          error: "Fetched strategy file, but parsed 0 strategies."
        };
      }
      return {
        source: "remote",
        strategies: [],
        remoteUrl,
        error: `Fetch failed: HTTP ${res.status}`
      };
    } catch (err) {
      return {
        source: "remote",
        strategies: [],
        remoteUrl,
        error: `Fetch error: ${String(err)}`
      };
    }
  }

  return { source: "remote", strategies: [] };
});

ipcMain.handle("app-version", () => {
  return {
    name: app.getName(),
    version: app.getVersion()
  };
});

ipcMain.handle("runtime-status", async () => {
  const status = await ensureRuntime();
  return status;
});

ipcMain.handle("runtime-install", async () => {
  const res = await installRuntime();
  return res;
});

function bootstrapStrategyUrlFromConfig() {
  if (process.env.STRATEGY_URL) return;

  const { url } = readStrategyUrlFromConfig();
  if (url) process.env.STRATEGY_URL = url;
}

function getEffectiveStrategyUrl() {
  // 1) Explicit env override (useful in dev/CI)
  if (process.env.STRATEGY_URL) return process.env.STRATEGY_URL;

  // 2) userData/config.json (lets users update URL without reinstall)
  // 3) app.asar/config.json (default shipped with the app)
  const { url } = readStrategyUrlFromConfig();
  return url || null;
}

function readStrategyUrlFromConfig() {
  const candidates = [
    path.join(app.getPath("userData"), "config.json"),
    path.join(app.getAppPath(), "config.json")
  ];

  for (const p of candidates) {
    try {
      if (!fs.existsSync(p)) continue;
      const raw = fs.readFileSync(p, "utf-8");
      const json = JSON.parse(raw);
      if (typeof json?.strategyUrl === "string" && json.strategyUrl.trim()) {
        return { url: json.strategyUrl.trim(), from: p };
      }
    } catch (err) {
      // keep trying other candidates
    }
  }
  return { url: null, from: null };
}

ipcMain.handle("run-dedupe", async (_event, payload) => {
  const { files, strategyKey, outputDir, strategyPayload } = payload || {};
  if (!Array.isArray(files) || files.length === 0) {
    return { error: "No files selected." };
  }
  if (!outputDir) {
    return { error: "No output directory selected." };
  }
  if (!strategyPayload) {
    return { error: "No strategy selected." };
  }

  const processorRoot = getEffectiveProcessorRoot();
  if (!processorRoot) {
    return {
      error:
        "Processor runtime not found. Please set SHORT_VIDEO_PROCESSOR_ROOT or use a build that bundles the processor."
    };
  }

  const runtime = await ensureRuntime();
  if (!runtime.ok) {
    return {
      error: `运行环境未就绪：${runtime.error || "Unknown error"}。请先点击「初始化环境」安装依赖。`
    };
  }
  const pythonPath = runtime.activePython;
  const processorScript = resolveUnpackedPath(path.join("tools", "process_video.py"));
  // Deliver outputs directly into the selected output directory (no extra "deduped" folder).
  await fs.promises.mkdir(outputDir, { recursive: true });

  const processedFiles = [];
  const failedFiles = [];

  for (const filePath of files) {
    try {
      const outputPath = await runPythonProcessor({
        pythonPath,
        scriptPath: processorScript,
        processorRoot,
        inputPath: filePath,
        outputDir,
        strategyPayload
      });
      processedFiles.push(outputPath);
    } catch (err) {
      failedFiles.push({ file: filePath, error: String(err) });
    }
  }

  return {
    total: files.length,
    processedFiles,
    failedFiles,
    outputSummary: {
      outputDir,
      processedCount: processedFiles.length,
      failedCount: failedFiles.length
    }
  };
});

async function uniqueCopyTarget(directory, sourcePath) {
  const base = path.basename(sourcePath);
  const ext = path.extname(base);
  const name = ext ? base.slice(0, -ext.length) : base;
  let candidate = path.join(directory, base);
  let counter = 1;
  while (true) {
    try {
      await fs.promises.access(candidate);
      candidate = path.join(directory, `${name}-${counter}${ext}`);
      counter += 1;
    } catch {
      return candidate;
    }
  }
}

function runPythonProcessor({ pythonPath, scriptPath, processorRoot, inputPath, outputDir, strategyPayload }) {
  return new Promise((resolve, reject) => {
    const args = [
      scriptPath,
      "--input",
      inputPath,
      "--output-dir",
      outputDir,
      "--strategy-json",
      JSON.stringify(strategyPayload),
      "--processor-root",
      processorRoot
    ];

    // MoviePy sometimes writes temp audio files using relative paths (TEMP_MPY_*),
    // so we must run from a writable directory (the output directory).
    const child = spawn(pythonPath || "python3", args, {
      stdio: ["ignore", "pipe", "pipe"],
      cwd: outputDir
    });
    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (data) => {
      stdout += data.toString();
    });
    child.stderr.on("data", (data) => {
      stderr += data.toString();
    });
    child.on("error", (err) => {
      reject(new Error(`Failed to start processor: ${String(err)}`));
    });
    child.on("close", (code) => {
      if (code !== 0) {
        const combined = [
          `Processor exited with code ${code}.`,
          stderr ? `--- stderr ---\n${stderr.trim()}` : "",
          stdout ? `--- stdout ---\n${stdout.trim()}` : ""
        ]
          .filter(Boolean)
          .join("\n");
        reject(new Error(combined));
        return;
      }
      try {
        const result = JSON.parse(stdout.trim());
        if (!result.output_path) {
          reject(new Error("Processor returned no output path."));
          return;
        }
        resolve(result.output_path);
      } catch (err) {
        const details = [
          `Failed to parse processor output: ${String(err)}`,
          stderr ? `--- stderr ---\n${stderr.trim()}` : "",
          stdout ? `--- stdout ---\n${stdout.trim()}` : ""
        ]
          .filter(Boolean)
          .join("\n");
        reject(new Error(details));
      }
    });
  });
}

function resolveUnpackedPath(relativePath) {
  const resourcesBase = process.resourcesPath;
  const candidate = path.join(resourcesBase, "app.asar.unpacked", relativePath);
  if (fs.existsSync(candidate)) return candidate;

  const appPath = app.getAppPath();
  const asarUnpackedBase = appPath.replace(/app\\.asar$/, "app.asar.unpacked");
  const fallback = path.join(asarUnpackedBase, relativePath);
  return fallback;
}

function parseStrategies(text, source) {
  const trimmed = (text || "").trim();
  if (!trimmed) return { source, strategies: [] };

  // Try full JSON first (object or array)
  try {
    const parsed = JSON.parse(trimmed);
    if (Array.isArray(parsed)) {
      return normalizeStrategies(parsed, source);
    }
    if (Array.isArray(parsed?.strategies)) {
      return normalizeStrategies(parsed.strategies, parsed.source || source, parsed.version);
    }
  } catch (err) {
    // fall through to line-based parsing
  }

  const lines = trimmed.split(/\r?\n/);
  const strategies = [];
  for (const line of lines) {
    const cleaned = line.trim();
    if (!cleaned || cleaned.startsWith("#")) continue;
    try {
      const obj = JSON.parse(cleaned);
      strategies.push(obj);
    } catch (err) {
      // ignore invalid lines
    }
  }

  return normalizeStrategies(strategies, source);
}

function normalizeStrategies(items, source, version) {
  const strategies = items
    .map((item, index) => {
      if (!item || typeof item !== "object") return null;
      const key = `strategy-${index + 1}`;
      const name = item.name || `策略 #${index + 1}`;
      const preview = summarizeStrategy(item);
      return {
        key,
        name,
        description: preview,
        payload: item
      };
    })
    .filter(Boolean);

  return {
    source,
    version,
    strategies
  };
}

function summarizeStrategy(item) {
  const entries = Object.entries(item)
    .filter(([key]) => key !== "enable")
    .slice(0, 4)
    .map(([key, value]) => {
      if (typeof value === "object") return `${key}: {..}`;
      return `${key}: ${value}`;
    });

  if (entries.length === 0) return "已启用";
  return entries.join(" | ");
}
