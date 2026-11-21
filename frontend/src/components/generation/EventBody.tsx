import { Space, Tag, Typography } from "antd";
import type { DetailEvent, Evidence } from "../../types";
import EvidenceBlock from "./EvidenceBlock";
import { PromptEvent, SystemPromptEvent } from "./PromptEvent";

function versionName(event: DetailEvent) {
  const value = event.version_label || event.version;
  if (!value) return "";
  return value.length > 16 ? value.slice(0, 10) : value;
}

export default function EventBody({
  event,
  onEvidence,
}: {
  event: DetailEvent;
  onEvidence: (evidence: Evidence) => void;
}) {
  if (event.type === "system_prompt") {
    return <SystemPromptEvent event={event} />;
  }
  if (event.type === "prompt") {
    return <PromptEvent event={event} />;
  }
  return (
    <>
      {event.query ? (
        <div className="detail-query">查询：{event.query}</div>
      ) : null}
      <Space wrap size={[6, 6]} className="detail-meta">
        {event.strategy ? <Tag>策略 {event.strategy}</Tag> : null}
        {event.top_k ? <Tag>Top K {event.top_k}</Tag> : null}
        {event.candidates ? <Tag>候选 {event.candidates}</Tag> : null}
        {event.rerank ? <Tag>重排序</Tag> : null}
        {event.cached ? <Tag color="gold">复用缓存</Tag> : null}
        {event.version_label || event.version ? (
          <Tag>版本 {versionName(event)}</Tag>
        ) : null}
        {event.retrieval_ms != null ? (
          <Tag>召回 {event.retrieval_ms.toFixed(0)} ms</Tag>
        ) : null}
        {event.reranker_ms != null ? (
          <Tag>重排 {event.reranker_ms.toFixed(0)} ms</Tag>
        ) : null}
        {event.results ? <Tag>返回 {event.results.length} 条</Tag> : null}
        {event.candidate_scores ? (
          <Tag>候选 {event.candidate_scores.length} 条</Tag>
        ) : null}
        {event.evidence_count != null ? (
          <Tag>证据总数 {event.evidence_count}</Tag>
        ) : null}
      </Space>
      {event.path_regex ? (
        <div className="detail-regex-line">
          路径筛选：<code>{event.path_regex}</code>
        </div>
      ) : null}
      {event.error ? (
        <div className="detail-error">检索错误：{event.error}</div>
      ) : null}
      {event.results?.length ? (
        <>
          <Typography.Text type="secondary" className="detail-heading">
            命中片段
          </Typography.Text>
          {event.results.map((item) => (
            <EvidenceBlock key={item.id} item={item} onEvidence={onEvidence} />
          ))}
        </>
      ) : null}
      {event.candidate_scores?.length ? (
        <>
          <Typography.Text type="secondary" className="detail-heading">
            候选与融合分数
          </Typography.Text>
          <div className="detail-candidates">
            {event.candidate_scores.map((item) => (
              <div className="detail-candidate" key={item.id}>
                <code>{item.id.slice(0, 12)}</code>
                <span>
                  {Object.entries(item.ranks ?? {})
                    .map(([name, rank]) => `${name}: ${rank}`)
                    .join(" · ")}
                </span>
                <span>
                  {Object.entries(item.scores ?? {})
                    .map(
                      ([name, value]) => `${name}: ${Number(value).toFixed(4)}`,
                    )
                    .join(" · ")}
                </span>
              </div>
            ))}
          </div>
        </>
      ) : null}
      {event.evidence_ids?.length ? (
        <div className="detail-ids">
          <Typography.Text type="secondary">
            证据 {event.evidence_ids.length} 条
          </Typography.Text>
          <div className="detail-id-list">
            {event.evidence_ids.map((id) => (
              <code key={id}>{id.slice(0, 12)}</code>
            ))}
          </div>
        </div>
      ) : null}
      {event.citation_ids?.length ? (
        <div className="detail-ids">
          <Typography.Text type="secondary">
            引用 {event.citation_ids.length} 条
          </Typography.Text>
          <div className="detail-id-list">
            {event.citation_ids.map((id) => (
              <code key={id}>{id.slice(0, 12)}</code>
            ))}
          </div>
        </div>
      ) : null}
    </>
  );
}
