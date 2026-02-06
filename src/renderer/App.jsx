import React, { useEffect, useMemo, useState } from "react";

const fallbackStrategies = {
  source: "remote",
  strategies: []
};

export default function App() {
  const [version, setVersion] = useState("");
  const [files, setFiles] = useState([]);
  const [outputDir, setOutputDir] = useState("");

  const [strategies, setStrategies] = useState(fallbackStrategies.strategies);
  const [strategySource, setStrategySource] = useState(fallbackStrategies.source);
  const [strategyKey, setStrategyKey] = useState("");
  const [strategyUrl, setStrategyUrl] = useState("");
  const [strategyError, setStrategyError] = useState("");

  const [runtime, setRuntime] = useState(null);
  const [checkingRuntime, setCheckingRuntime] = useState(false);
  const [installingRuntime, setInstallingRuntime] = useState(false);

  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("等待选择视频...");
  const [loading, setLoading] = useState(false);
  const [refreshingStrategies, setRefreshingStrategies] = useState(false);

  const api = window.api;

  const selectedStrategy = useMemo(
    () => strategies.find((s) => s.key === strategyKey) || null,
    [strategies, strategyKey]
  );

  const processedCount = useMemo(
    () => (result?.processedFiles ? result.processedFiles.length : 0),
    [result]
  );

  const failedCount = useMemo(
    () => (result?.failedFiles ? result.failedFiles.length : 0),
    [result]
  );

  useEffect(() => {
    if (!api) {
      setStatus("初始化失败：无法加载本地 API（preload）。");
      return;
    }

    if (api.getAppVersion) {
      api
        .getAppVersion()
        .then((v) => setVersion(v?.version ? `v${v.version}` : ""))
        .catch(() => setVersion(""));
    }

    void refreshStrategies();
    void refreshRuntimeStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshRuntimeStatus = async () => {
    if (!api?.runtimeStatus) return;
    setCheckingRuntime(true);
    try {
      const res = await api.runtimeStatus();
      setRuntime(res || null);
    } catch (e) {
      setRuntime({ ok: false, error: String(e) });
    } finally {
      setCheckingRuntime(false);
    }
  };

  const handleInstallRuntime = async () => {
    if (!api?.runtimeInstall) return;
    setInstallingRuntime(true);
    setStatus("正在初始化运行环境（首次可能需要几分钟）...");
    try {
      const res = await api.runtimeInstall();
      if (res?.ok) setStatus("运行环境初始化完成。");
      else setStatus(`运行环境初始化失败：${res?.error || "Unknown error"}`);
    } catch (e) {
      setStatus(`运行环境初始化失败：${String(e)}`);
    } finally {
      setInstallingRuntime(false);
      void refreshRuntimeStatus();
    }
  };

  const refreshStrategies = async () => {
    if (!api?.loadStrategies) return;
    setRefreshingStrategies(true);
    try {
      const data = await api.loadStrategies();
      setStrategyUrl(data?.remoteUrl || "");
      setStrategyError(data?.error || "");

      if (Array.isArray(data?.strategies) && data.strategies.length > 0) {
        setStrategies(data.strategies);
        setStrategySource(data.source || "remote/local");
        setStrategyKey((prev) => data.strategies.find((s) => s.key === prev)?.key || data.strategies[0].key);
        setStatus("策略已更新。");
      } else {
        setStrategies([]);
        setStrategyKey("");
        setStrategySource(data?.source || "remote");
        setStatus("策略列表为空。");
      }
    } catch (e) {
      setStrategyError(String(e));
      setStatus(`策略更新失败。原因: ${String(e)}`);
    } finally {
      setRefreshingStrategies(false);
    }
  };

  const handleSelectVideos = async () => {
    if (!api?.selectVideos) return;
    const picked = await api.selectVideos();
    if (!picked || picked.length === 0) {
      setStatus("未选择视频。");
      return;
    }
    setFiles(picked);
    setResult(null);
    setStatus(`已选择 ${picked.length} 个视频。`);
  };

  const handleClearVideos = () => {
    setFiles([]);
    setResult(null);
    setStatus("已清空选择的视频。");
  };

  const handleRemoveVideo = (file) => {
    setFiles((prev) => prev.filter((p) => p !== file));
  };

  const handleSelectOutputDir = async () => {
    if (!api?.selectOutputDir) return;
    const selected = await api.selectOutputDir();
    if (!selected) {
      setStatus("未选择输出目录。");
      return;
    }
    setOutputDir(selected);
    setStatus("已选择输出目录。");
  };

  const handleOpenPublish = async () => {
    if (!api?.openPublishLogin) return;
    await api.openPublishLogin();
    setStatus("已打开发布页面，请在新窗口登录并发布。");
  };

  const handleClosePublish = async () => {
    if (!api?.closePublish) return;
    await api.closePublish();
    setStatus("已关闭发布窗口。");
  };

  const handleRandomPick = () => {
    if (strategies.length === 0) {
      setStatus("暂无策略可抽选。");
      return;
    }
    const picked = strategies[Math.floor(Math.random() * strategies.length)];
    setStrategyKey(picked.key);
    const pickedIndex = strategies.findIndex((s) => s.key === picked.key);
    setStatus(`已随机抽选：策略 #${pickedIndex >= 0 ? pickedIndex + 1 : "?"}`);
  };

  const handleRun = async () => {
    if (!api?.runDedupe) return;
    if (files.length === 0) {
      setStatus("请先选择视频。");
      return;
    }
    if (!strategyKey) {
      setStatus("请先选择策略。");
      return;
    }
    if (!outputDir) {
      setStatus("请先选择输出目录。");
      return;
    }
    if (runtime && runtime.ok === false) {
      setStatus("运行环境未就绪，请先点击「初始化环境」。");
      return;
    }

    setLoading(true);
    setStatus("去重处理中...");
    try {
      const res = await api.runDedupe({
        files,
        strategyKey,
        outputDir,
        strategyPayload: selectedStrategy?.payload || null
      });
      if (res?.error) setStatus(res.error);
      else {
        setResult(res);
        setStatus("去重完成。");
      }
    } catch (e) {
      setStatus(`去重失败，请重试。${e ? ` 原因: ${String(e)}` : ""}`);
    } finally {
      setLoading(false);
    }
  };

  const handleShowItemInFolder = async (filePath) => {
    if (!api?.showItemInFolder) return;
    try {
      await api.showItemInFolder(filePath);
    } catch {
      // ignore
    }
  };

  return (
    <div className="app">
      <header className="hero">
        <div>
          <p className="eyebrow">Video Dedupe Desktop</p>
          <h1>北斗视频去重</h1>
          {version ? <p className="muted">{version}</p> : null}
        </div>
        <div className="status">
          <span className="dot" />
          <span>{status}</span>
        </div>
      </header>

      <main className="grid">
        <section className="panel">
          <h2>操作区</h2>

          <div className="actions">
            <button onClick={handleSelectVideos}>选择视频</button>
            <button className="ghost" onClick={refreshStrategies} disabled={refreshingStrategies}>
              {refreshingStrategies ? "刷新中..." : "刷新策略"}
            </button>
            <button className="ghost" onClick={handleRandomPick} disabled={strategies.length === 0}>
              随机抽选
            </button>
            <button className="ghost" onClick={handleSelectOutputDir}>
              选择输出目录
            </button>
            <button className="ghost" onClick={handleClearVideos} disabled={files.length === 0}>
              清空视频
            </button>
            <button className="ghost" onClick={handleOpenPublish}>
              一键发布
            </button>
            <button className="ghost" onClick={handleClosePublish}>
              返回软件
            </button>
          </div>

          <div className="block">
            <p className="label">运行环境</p>
            <div className="output-box">
              {checkingRuntime ? "检测中..." : runtime?.ok ? "就绪" : "未就绪（需要初始化）"}
            </div>
            {runtime?.activePython ? <div className="source">Python：{runtime.activePython}</div> : null}
            {runtime?.ok === false ? (
              <>
                <div className="source">原因：{runtime.error || "Unknown error"}</div>
                <button className="ghost" onClick={handleInstallRuntime} disabled={installingRuntime}>
                  {installingRuntime ? "初始化中..." : "初始化环境"}
                </button>
              </>
            ) : null}
          </div>

          <div className="block">
            <p className="label">已选视频</p>
            <div className="file-list">
              {files.length === 0 ? (
                <span className="muted">暂无文件</span>
              ) : (
                files.slice(0, 5).map((file) => (
                  <div key={file} className="file-item">
                    <span className="file-path">{file}</span>
                    <button className="mini" onClick={() => handleRemoveVideo(file)}>
                      移除
                    </button>
                  </div>
                ))
              )}
              {files.length > 5 ? <div className="muted">还有 {files.length - 5} 个文件...</div> : null}
            </div>
          </div>

          <div className="block">
            <p className="label">输出目录</p>
            <div className="output-box">{outputDir || "未选择"}</div>
          </div>

          <div className="block">
            <p className="label">去重策略</p>
            <div className="strategy-grid">
              {strategies.map((strategy, index) => (
                <label key={strategy.key} className={`strategy ${strategy.key === strategyKey ? "active" : ""}`}>
                  <input
                    type="radio"
                    name="strategy"
                    value={strategy.key}
                    checked={strategy.key === strategyKey}
                    onChange={() => setStrategyKey(strategy.key)}
                  />
                  <div>
                    <div className="strategy-title">{`策略 #${index + 1}`}</div>
                  </div>
                </label>
              ))}
            </div>

            {/* Intentionally hide strategy details (params/source/url/current payload) from the UI. */}
            {/* Keeping the state variables so behavior (runDedupe payload) stays the same. */}
            {false ? (
              <div className="source">
                {strategySource} {strategyUrl} {strategyError}
              </div>
            ) : null}
          </div>

          <button className="primary" onClick={handleRun} disabled={loading || (runtime && runtime.ok === false)}>
            {loading ? "执行中..." : "开始去重"}
          </button>
        </section>

        <section className="panel">
          <h2>结果区</h2>
          {result ? (
            <div className="result">
              <div className="summary">
                <div>
                  <div className="value">{result.total}</div>
                  <div className="muted">输入文件</div>
                </div>
                <div>
                  <div className="value">{processedCount}</div>
                  <div className="muted">已处理</div>
                </div>
                <div>
                  <div className="value">{failedCount}</div>
                  <div className="muted">失败</div>
                </div>
              </div>

              {processedCount === 0 ? (
                <div className="empty">暂无处理结果。</div>
              ) : (
                <div className="groups">
                  {result.processedFiles.slice(0, 5).map((file) => (
                    <div key={file} className="group">
                      <div className="group-item keep">
                        <div className="file-item">
                          <span className="file-path" title={file} style={{ flex: 1, minWidth: 0 }}>
                            {file}
                          </span>
                          <button className="mini" onClick={() => handleShowItemInFolder(file)}>
                            文件夹
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                  {result.processedFiles.length > 5 ? (
                    <div className="muted">还有 {result.processedFiles.length - 5} 个输出文件...</div>
                  ) : null}
                </div>
              )}

              {/* Keep outputSummary in data for any future features, but hide it from UI per delivery requirement. */}

              {failedCount > 0 && Array.isArray(result.failedFiles) ? (
                <div className="block">
                  <p className="label">失败详情</p>
                  <div className="file-list">
                    {result.failedFiles.slice(0, 3).map((f) => (
                      <details key={f.file} className="file-item" open>
                        <summary className="file-path">{f.file}</summary>
                        <pre className="code-box" style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>
                          {f.error || "未知错误"}
                        </pre>
                      </details>
                    ))}
                    {result.failedFiles.length > 3 ? (
                      <div className="muted">还有 {result.failedFiles.length - 3} 个失败文件。</div>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="empty">暂无结果，开始去重后显示。</div>
          )}
        </section>
      </main>
    </div>
  );
}
