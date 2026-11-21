import { Spin } from "antd";
import { useState } from "react";
import type { TraceStep } from "../types";

function TraceStepView({ step }: { step: TraceStep }) {
  if (step.type === "thinking") {
    if (!step.text) return null;
    return (
      <div className="trace-thinking">
        <span className="trace-kind">思考</span>
        {step.text}
      </div>
    );
  }
  if (step.type === "retrieval") {
    return (
      <div className="trace-row">
        <span className="trace-kind">检索</span>
        <div>
          <div className="trace-label">{step.query}</div>
          <div className="trace-meta">
            命中 {step.count ?? 0} 条 · {step.strategy || "hybrid"}
            {step.rerank ? " · 重排序" : ""}
            {step.retrieval_ms != null
              ? ` · ${step.retrieval_ms.toFixed(0)} ms`
              : ""}
          </div>
        </div>
      </div>
    );
  }
  if (step.type === "search") {
    if (step.status === "skipped") {
      return (
        <div className="trace-row">
          <span className="trace-kind skipped">跳过</span>
          <div>
            <div className="trace-label">{step.query || "无效查询"}</div>
            {step.path_regex ? (
              <div className="trace-meta">
                路径筛选：<code>{step.path_regex}</code>
              </div>
            ) : null}
            {step.version_label || step.version ? (
              <div className="trace-meta">
                版本筛选：<code>{step.version_label || step.version}</code>
              </div>
            ) : null}
            <div className="trace-meta">{step.reason}</div>
          </div>
        </div>
      );
    }
    return (
      <div className="trace-row">
        <span
          className={`trace-kind${step.status === "running" ? " active" : ""}`}
        >
          {step.status === "running" ? <Spin size="small" /> : "补充检索"}
        </span>
        <div className="trace-search">
          <div className="trace-label">{step.query}</div>
          {step.path_regex ? (
            <div className="trace-meta">
              路径筛选：<code>{step.path_regex}</code>
            </div>
          ) : null}
          {step.version_label || step.version ? (
            <div className="trace-meta">
              版本筛选：<code>{step.version_label || step.version}</code>
            </div>
          ) : null}
          {step.status === "running" ? (
            <div className="trace-meta">正在搜索知识库…</div>
          ) : (
            <div className="trace-meta">
              新增 {step.added ?? 0} 条证据 · 证据累计 {step.total ?? 0} 条
              {step.candidates ? ` · 候选 ${step.candidates}` : ""}
              {step.cached ? " · 复用结果" : ""}
              {step.retrieval_ms != null
                ? ` · ${step.retrieval_ms.toFixed(0)} ms`
                : ""}
            </div>
          )}
          {step.top?.length ? (
            <ul className="trace-tops">
              {step.top.map((item) => (
                <li key={item.id || item.label}>
                  {item.label}
                  {item.score != null ? ` · ${item.score.toFixed(4)}` : ""}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
    );
  }
  return (
    <div className="trace-row">
      <span className="trace-kind">完成</span>
      <div className="trace-meta">
        生成结束 · {step.citations ?? 0} 条引用
        {step.complete === false ? " · 输出达到上限" : ""}
      </div>
    </div>
  );
}

export default function ProcessTrace({
  trace,
  streaming,
}: {
  trace: TraceStep[];
  streaming?: boolean;
}) {
  const [open, setOpen] = useState(!!streaming);
  const active = trace.some(
    (step) => step.status === "running" || step.status === "delta",
  );
  return (
    <section className={`process-block${open ? " open" : ""}`}>
      <button
        type="button"
        className="process-head"
        onClick={() => setOpen((value) => !value)}
      >
        <span className={`process-dot${active ? " active" : ""}`} />
        <span>{active ? "正在思考与检索…" : "思考与检索过程"}</span>
        <span className="process-count">{trace.length} 步</span>
        <span className="process-action">{open ? "收起" : "展开"}</span>
      </button>
      {open && (
        <div className="process-body">
          {trace.map((step) => (
            <TraceStepView key={step.id} step={step} />
          ))}
        </div>
      )}
    </section>
  );
}
