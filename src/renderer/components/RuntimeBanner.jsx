import React from "react";

export default function RuntimeBanner({
  runtime,
  checkingRuntime,
  installingRuntime,
  onInstallRuntime
}) {
  const stateText = checkingRuntime
    ? "检测中..."
    : runtime == null
      ? "未检测"
      : runtime?.ok
        ? "就绪"
        : "未就绪（需要初始化）";

  if (checkingRuntime) {
    return (
      <div className="callout callout--neutral">
        <div className="callout__title">运行环境</div>
        <div className="callout__body">{stateText}</div>
      </div>
    );
  }

  if (runtime?.ok === false) {
    return (
      <div className="callout callout--warn">
        <div className="callout__title">运行环境未就绪（需要初始化）</div>
        <div className="callout__body">
          <div className="muted" style={{ marginTop: 6 }}>
            {runtime?.error ? `原因：${runtime.error}` : null}
          </div>
          {runtime?.activePython ? (
            <div className="muted" style={{ marginTop: 6 }}>
              Python：{runtime.activePython}
            </div>
          ) : null}
          <div style={{ marginTop: 10 }}>
            <button className="ghost" onClick={onInstallRuntime} disabled={installingRuntime}>
              {installingRuntime ? "初始化中..." : "初始化环境"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // runtime ok or unknown: keep it compact.
  return (
    <div className="inline-status">
      <span className="inline-status__label">环境：</span>
      <span className="inline-status__value">{stateText}</span>
    </div>
  );
}
