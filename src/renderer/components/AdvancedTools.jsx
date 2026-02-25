import React from "react";

export default function AdvancedTools({
  open,
  onToggle,
  strategies,
  strategyKey,
  onSelectStrategy,
  onRefreshStrategies,
  refreshingStrategies,
  onRandomPick,
  strategySource,
  strategyUrl,
  strategyError
}) {
  return (
    <div className="accordion">
      <button className="accordion__head" type="button" onClick={onToggle}>
        <span>高级工具</span>
        <span className="accordion__chev">{open ? "收起" : "展开"}</span>
      </button>

      {open ? (
        <div className="accordion__body">
          <div className="subcard">
            <div className="subcard__title">推荐策略</div>
            <div className="row row--gap" style={{ marginTop: 8 }}>
              <button className="ghost" onClick={onRefreshStrategies} disabled={refreshingStrategies}>
                {refreshingStrategies ? "刷新中..." : "刷新推荐策略"}
              </button>
              <button className="ghost" onClick={onRandomPick} disabled={strategies.length === 0}>
                随机抽选
              </button>
            </div>

            {strategyError ? (
              <div className="muted wrap-anywhere" style={{ marginTop: 8 }}>
                推荐策略加载错误：{strategyError}
              </div>
            ) : null}
            {/* Per UX: hide source/url by default to keep UI clean. */}

            <div className="strategy-grid" style={{ marginTop: 10 }}>
              {strategies.length === 0 ? (
                <div className="muted">暂无推荐策略</div>
              ) : (
                strategies.map((strategy, index) => (
                  <label key={strategy.key} className={`strategy ${strategy.key === strategyKey ? "active" : ""}`}>
                    <input
                      type="radio"
                      name="strategy"
                      value={strategy.key}
                      checked={strategy.key === strategyKey}
                      onChange={() => onSelectStrategy(strategy.key)}
                    />
                    <div>
                      <div className="strategy-title">{`推荐策略 #${index + 1}`}</div>
                    </div>
                  </label>
                ))
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
