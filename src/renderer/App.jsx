import React, { useEffect, useMemo, useRef, useState } from "react";
import RuntimeBanner from "./components/RuntimeBanner.jsx";
import QuickStart from "./components/QuickStart.jsx";
import AdvancedTools from "./components/AdvancedTools.jsx";
import ResultsPanel from "./components/ResultsPanel.jsx";
import appLogo from "../../beidou.png";

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
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [showPublishModal, setShowPublishModal] = useState(false);

  const strategySectionRef = useRef(null);

  const api = window.api;

  const selectedStrategy = useMemo(
    () => strategies.find((s) => s.key === strategyKey) || null,
    [strategies, strategyKey]
  );

  const selectedStrategyIndex = useMemo(() => {
    const idx = strategies.findIndex((s) => s.key === strategyKey);
    return idx >= 0 ? idx + 1 : null;
  }, [strategies, strategyKey]);

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

  const handleOpenPath = async (targetPath) => {
    if (!targetPath) return;
    if (!api?.openPath) {
      // Fallback: no-op (older builds). We still keep UI stable.
      setStatus("当前版本不支持打开目录。");
      return;
    }
    try {
      const res = await api.openPath(targetPath);
      if (res?.ok === false) setStatus(`打开失败：${res?.error || "Unknown error"}`);
    } catch (e) {
      setStatus(`打开失败：${String(e)}`);
    }
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
        // 任务完成后显示发布弹窗
        setShowPublishModal(true);
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

  const blockers = useMemo(() => {
    const items = [];
    if (files.length === 0) items.push("视频：未选择");
    else items.push(`视频：已选择 ${files.length} 个`);

    if (!outputDir) items.push("输出目录：未选择");
    else items.push("输出目录：已选择");

    if (!selectedStrategy?.payload) items.push("策略：未加载/未选择");
    else items.push(`策略：已选择（#${selectedStrategyIndex ?? "?"}）`);

    if (runtime && runtime.ok === false) items.push("环境：未就绪（请先初始化）");
    else if (checkingRuntime) items.push("环境：检测中...");
    else if (runtime == null) items.push("环境：未检测");
    else items.push("环境：就绪");

    if (loading) items.push("执行：进行中");
    return items;
  }, [checkingRuntime, files.length, loading, outputDir, runtime, selectedStrategy, selectedStrategyIndex]);

  const canRun = useMemo(() => {
    if (loading) return false;
    if (files.length === 0) return false;
    if (!outputDir) return false;
    if (!selectedStrategy?.payload) return false;
    if (runtime && runtime.ok === false) return false;
    return true;
  }, [files.length, loading, outputDir, runtime, selectedStrategy]);

  const handleChangeStrategy = () => {
    setAdvancedOpen(true);
    // allow the panel to open before scrolling
    requestAnimationFrame(() => {
      strategySectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  return (
    <div className="app">
      <header className="hero">
        <div className="brand">
          <div className="brand__logo-wrap">
            <img className="brand__logo" src={appLogo} alt="北斗视频去重 Logo" />
          </div>
          <div>
            <p className="eyebrow">Video Dedupe Desktop</p>
            <h1>北斗视频去重</h1>
            {version ? <p className="muted">{version}</p> : null}
          </div>
        </div>
        <div className="status">
          <span className="dot" />
          <span>{status}</span>
        </div>
      </header>

      <main className="grid">
        <section className="panel">
          <h2>开始去重</h2>

          <RuntimeBanner
            runtime={runtime}
            checkingRuntime={checkingRuntime}
            installingRuntime={installingRuntime}
            onInstallRuntime={handleInstallRuntime}
          />

          <QuickStart
            files={files}
            outputDir={outputDir}
            onSelectVideos={handleSelectVideos}
            onRemoveVideo={handleRemoveVideo}
            onClearVideos={handleClearVideos}
            onSelectOutputDir={handleSelectOutputDir}
            onOpenPath={handleOpenPath}
          />

          <div className="card" style={{ marginTop: 12 }}>
            <div className="row row--between">
              <div>
                <div className="card__title">当前策略</div>
                <div className="muted" style={{ marginTop: 4 }}>
                  {selectedStrategyIndex ? `策略 #${selectedStrategyIndex}` : "策略未加载"}
                </div>
              </div>
              <button className="ghost" onClick={handleChangeStrategy}>
                更换策略
              </button>
            </div>
          </div>

          <div className="card" style={{ marginTop: 12 }}>
            <div className="card__title">第 3 步：开始去重</div>
            <div className="card__subtitle">确认信息无误后点击开始。</div>

            <button className="primary" onClick={handleRun} disabled={!canRun}>
              {loading ? "执行中..." : "开始去重"}
            </button>

            <div className="checklist" style={{ marginTop: 10 }}>
              {blockers.map((line) => (
                <div key={line} className="checklist__item">
                  {line}
                </div>
              ))}
            </div>
          </div>

          <div ref={strategySectionRef} style={{ marginTop: 12 }}>
            <AdvancedTools
              open={advancedOpen}
              onToggle={() => setAdvancedOpen((v) => !v)}
              strategies={strategies}
              strategyKey={strategyKey}
              onSelectStrategy={(k) => setStrategyKey(k)}
              onRefreshStrategies={refreshStrategies}
              refreshingStrategies={refreshingStrategies}
              onRandomPick={handleRandomPick}
              strategySource={strategySource}
              strategyUrl={strategyUrl}
              strategyError={strategyError}
            />
          </div>

          <div className="card" style={{ marginTop: 12 }}>
            <div className="card__title">发布</div>
            <div className="row row--gap" style={{ marginTop: 8 }}>
              <button className="ghost" onClick={handleOpenPublish}>
                打开发布窗口
              </button>
              <button className="ghost" onClick={handleClosePublish}>
                关闭发布窗口
              </button>
            </div>
          </div>
        </section>

        <ResultsPanel
          result={result}
          loading={loading}
          outputDir={outputDir}
          onOpenPath={handleOpenPath}
          onShowItemInFolder={handleShowItemInFolder}
        />
      </main>

      {/* 去重完成弹窗 */}
      {showPublishModal && (
        <div className="modal-overlay">
          <div className="modal modal--success" onClick={(e) => e.stopPropagation()}>
            <div className="success-icon">
              <svg viewBox="0 0 52 52" className="checkmark-svg">
                <circle className="checkmark-circle" cx="26" cy="26" r="24" fill="none" />
                <path className="checkmark-check" fill="none" d="M14 27l8 8 16-16" />
              </svg>
            </div>
            <div className="modal__title success-title">处理完成</div>
            <div className="success-stats">
              <div className="success-stat">
                <span className="success-stat__value">{result?.total || files.length || 0}</span>
                <span className="success-stat__label">输入文件</span>
              </div>
              <div className="success-stat success-stat--highlight">
                <span className="success-stat__value">{result?.processedFiles?.length || 0}</span>
                <span className="success-stat__label">处理成功</span>
              </div>
              <div className="success-stat">
                <span className="success-stat__value">{result?.failedFiles?.length || 0}</span>
                <span className="success-stat__label">失败</span>
              </div>
            </div>
            <div className="success-message">
              视频去重已完成，所有文件已保存到输出目录
            </div>
            <div className="modal__actions modal__actions--center">
              <button className="ghost" onClick={() => setShowPublishModal(false)}>
                查看结果
              </button>
              <button className="primary primary--large" onClick={() => {
                setShowPublishModal(false);
                handleOpenPublish();
              }}>
                <span className="btn-icon">🚀</span>
                立即发布
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
