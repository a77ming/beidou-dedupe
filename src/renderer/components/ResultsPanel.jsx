import React, { useMemo } from "react";

function shortenPath(path, maxLen = 90) {
  if (!path || path.length <= maxLen) return path;
  const keepHead = Math.floor((maxLen - 3) * 0.55);
  const keepTail = maxLen - 3 - keepHead;
  return `${path.slice(0, keepHead)}...${path.slice(-keepTail)}`;
}

export default function ResultsPanel({
  result,
  loading,
  outputDir,
  onOpenPath,
  onShowItemInFolder
}) {
  const processedCount = useMemo(
    () => (result?.processedFiles ? result.processedFiles.length : 0),
    [result]
  );
  const failedCount = useMemo(
    () => (result?.failedFiles ? result.failedFiles.length : 0),
    [result]
  );
  const effectiveOutputDir = result?.outputSummary?.outputDir || outputDir || "";

  return (
    <section className="panel">
      <h2>结果区</h2>

      {loading ? (
        <div className="loading-panel">
          <div className="loading-panel__spinner">
            <div className="spinner-ring"></div>
            <div className="spinner-ring"></div>
            <div className="spinner-ring"></div>
          </div>
          <div className="loading-panel__title">正在处理中</div>
          <div className="loading-panel__steps">
            <div className="loading-step loading-step--done">
              <span className="step-icon">✓</span>
              <span>读取视频文件</span>
            </div>
            <div className="loading-step loading-step--active">
              <span className="step-icon"></span>
              <span>分析视频特征</span>
            </div>
            <div className="loading-step">
              <span className="step-icon"></span>
              <span>应用去重策略</span>
            </div>
            <div className="loading-step">
              <span className="step-icon"></span>
              <span>生成输出文件</span>
            </div>
          </div>
          <div className="loading-panel__progress">
            <div className="progress-bar"></div>
          </div>
          <div className="loading-panel__hint">请勿关闭软件，处理完成后会自动显示结果</div>
        </div>
      ) : null}

      {result ? (
        <div className="result">
          {/* 完成状态卡片 */}
          <div className="completion-card">
            <div className="completion-card__icon">
              <svg viewBox="0 0 24 24" fill="none" className="check-icon">
                <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.15" />
                <path d="M8 12l3 3 5-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="completion-card__content">
              <div className="completion-card__title">去重完成</div>
              <div className="completion-card__subtitle">视频已成功处理，可以进行发布</div>
            </div>
          </div>

          <div className="summary">
            <div>
              <div className="value">{result.total}</div>
              <div className="muted">输入文件</div>
            </div>
            <div className="summary--success">
              <div className="value">{processedCount}</div>
              <div className="muted">去重成功</div>
            </div>
            <div>
              <div className="value">{failedCount}</div>
              <div className="muted">失败</div>
            </div>
          </div>

          <div className="result-meta">
            <div className="result-meta__label">输出目录：</div>
            <div className="result-meta__value" title={effectiveOutputDir}>
              {effectiveOutputDir || "-"}
            </div>
            <button className="mini" onClick={() => onOpenPath(effectiveOutputDir)} disabled={!effectiveOutputDir}>
              打开目录
            </button>
          </div>

          {processedCount === 0 ? (
            <div className="empty">暂无处理结果。</div>
          ) : (
            <div className="output-section">
              <div className="output-section__header">
                <span className="output-section__title">去重后的视频</span>
                <span className="output-section__badge">{processedCount} 个文件</span>
              </div>
              <div className="groups">
                {result.processedFiles.slice(0, 5).map((file, index) => (
                  <div key={file} className="output-file">
                    <div className="output-file__index">{index + 1}</div>
                    <div className="output-file__path" title={file}>
                      {shortenPath(file, 70)}
                    </div>
                    <button className="mini" onClick={() => onShowItemInFolder(file)}>
                      查看
                    </button>
                  </div>
                ))}
                {result.processedFiles.length > 5 ? (
                  <div className="output-more">还有 {result.processedFiles.length - 5} 个文件...</div>
                ) : null}
              </div>
            </div>
          )}

          {failedCount > 0 && Array.isArray(result.failedFiles) ? (
            <div className="block">
              <p className="label">失败详情</p>
              <div className="file-list">
                {result.failedFiles.slice(0, 3).map((f) => (
                  <details key={f.file} className="file-details" open>
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
        <div className="empty">
          <div>按左侧 3 步操作：选择视频与输出目录，然后开始去重。</div>
          <div style={{ marginTop: 8 }}>输出会直接写入你选择的输出目录。</div>
        </div>
      )}
    </section>
  );
}
