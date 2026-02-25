import React, { useMemo, useState } from "react";

function Step({ number, title, required, children }) {
  return (
    <div className="step">
      <div className="step__badge">{number}</div>
      <div className="step__content">
        <div className="step__title">
          <span>{title}</span>
          {required ? <span className="tag tag--req">必填</span> : null}
        </div>
        <div className="step__body">{children}</div>
      </div>
    </div>
  );
}

export default function QuickStart({
  files,
  outputDir,
  onSelectVideos,
  onRemoveVideo,
  onClearVideos,
  onSelectOutputDir,
  onOpenPath
}) {
  const [manageOpen, setManageOpen] = useState(false);
  const pickedCount = files.length;

  const firstFew = useMemo(() => files.slice(0, 5), [files]);

  return (
    <div className="card">
      <div className="card__title">快速开始</div>
      <div className="card__subtitle">按 3 步操作：先选视频和输出目录，再开始去重。</div>

      <div className="steps">
        <Step number={1} title="选择视频" required>
          <div className="row row--gap">
            <button onClick={onSelectVideos}>选择视频</button>
            <div className="muted">
              {pickedCount === 0 ? "未选择" : `已选择 ${pickedCount} 个视频`}
            </div>
          </div>

          <div className="collapse">
            <button
              className="link"
              onClick={() => setManageOpen((v) => !v)}
              disabled={pickedCount === 0}
              type="button"
            >
              {manageOpen ? "收起已选文件" : "管理已选文件"}
            </button>

            {manageOpen ? (
              <div className="file-list" style={{ marginTop: 8 }}>
                {firstFew.map((file) => (
                  <div key={file} className="file-item">
                    <span className="file-path" title={file}>
                      {file}
                    </span>
                    <button className="mini" onClick={() => onRemoveVideo(file)}>
                      移除
                    </button>
                  </div>
                ))}
                {pickedCount > 5 ? <div className="muted">还有 {pickedCount - 5} 个文件...</div> : null}
                <div style={{ marginTop: 10 }}>
                  <button className="ghost" onClick={onClearVideos} disabled={pickedCount === 0}>
                    清空视频
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </Step>

        <Step number={2} title="选择输出目录" required>
          <div className="row row--gap">
            <button className="ghost" onClick={onSelectOutputDir}>
              选择输出目录
            </button>
            <button className="ghost" onClick={() => onOpenPath(outputDir)} disabled={!outputDir}>
              打开目录
            </button>
          </div>
          <div className="output-box" style={{ marginTop: 8 }}>
            {outputDir || "未选择"}
          </div>
          <div className="muted" style={{ marginTop: 6 }}>
            输出会直接写入你选择的目录。
          </div>
        </Step>
      </div>
    </div>
  );
}
