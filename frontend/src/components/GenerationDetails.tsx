import { Button, Collapse, Empty, Space, Tag, Typography } from "antd";
import { useEffect, useRef, useState } from "react";
import type { DetailEvent, Evidence } from "../types";

function scoreTags(item: Evidence) {
  return [
    ...Object.entries(item.scores ?? {}).map(([name, value]) => (
      <Tag key={"s-" + name}>
        {name}: {Number(value).toFixed(4)}
      </Tag>
    )),
    ...Object.entries(item.ranks ?? {}).map(([name, value]) => (
      <Tag key={"r-" + name}>
        {name} 排名: {value}
      </Tag>
    )),
  ];
}

function EvidenceBlock({
  item,
  onEvidence,
}: {
  item: Evidence;
  onEvidence: (evidence: Evidence) => void;
}) {
  const location = item.location;
  const label = location?.page
    ? `${location.path} · 第 ${location.page} 页`
    : location?.start_line != null
      ? `${location.path}:${location.start_line}–${location.end_line}`
      : location?.path || item.id;
  return (
    <div className="detail-evidence">
      <Button type="link" size="small" onClick={() => onEvidence(item)}>
        {label}
      </Button>
      <Space wrap size={[4, 4]}>
        {scoreTags(item)}
      </Space>
      <pre>{item.text}</pre>
    </div>
  );
}

const roles: Record<string, string> = {
  system: "系统",
  human: "用户",
  ai: "助手",
  tool: "工具",
};

function formatContent(content: unknown) {
  if (typeof content !== "string") return JSON.stringify(content, null, 2);
  const text = content.trim();
  if (!text || (text[0] !== "{" && text[0] !== "[")) return content;
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return content;
  }
}

function EventBody({
  event,
  onEvidence,
}: {
  event: DetailEvent;
  onEvidence: (evidence: Evidence) => void;
}) {
  if (event.type === "system_prompt") {
    return (
      <>
        <Space wrap size={[6, 6]} className="detail-meta">
          <Tag>{event.rag === false ? "基础模型" : "知识库问答"}</Tag>
        </Space>
        <pre className="detail-prompt-text">{event.text}</pre>
      </>
    );
  }
  if (event.type === "prompt") {
    const messages = event.messages ?? [];
    return (
      <>
        <Space wrap size={[6, 6]} className="detail-meta">
          <Tag>{event.rag === false ? "基础模型" : "知识库问答"}</Tag>
          <Tag>{messages.length} 条消息</Tag>
        </Space>
        <div className="detail-prompt-messages">
          {messages.map((message, index) => (
            <div className="detail-prompt-message" key={index}>
              <div className="detail-prompt-head">
                <Tag>{roles[message.type] ?? message.type}</Tag>
                {message.tool_call_id ? (
                  <Typography.Text type="secondary" ellipsis>
                    tool_call_id {message.tool_call_id}
                  </Typography.Text>
                ) : null}
              </div>
              <pre className="detail-prompt-text">
                {formatContent(message.content)}
              </pre>
              {message.tool_calls?.length ? (
                <pre className="detail-prompt-text">
                  {JSON.stringify(message.tool_calls, null, 2)}
                </pre>
              ) : null}
            </div>
          ))}
        </div>
      </>
    );
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
        {event.version ? <Tag>版本 {event.version.slice(0, 10)}</Tag> : null}
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
                    .map(([name, value]) => `${name}: ${Number(value).toFixed(4)}`)
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

const labels: Record<DetailEvent["type"], string> = {
  system_prompt: "系统 Prompt",
  prompt: "完整 Prompt",
  rag_context: "RAG 注入内容",
  tool_call: "工具调用",
  tool_result: "检索结果",
  final_context: "最终上下文",
};

export default function GenerationDetails({
  events,
  onEvidence,
}: {
  events: DetailEvent[];
  onEvidence: (evidence: Evidence) => void;
}) {
  const [activeKeys, setActiveKeys] = useState<string[]>(
    events.map((event) => event.id),
  );
  const seen = useRef(new Set(events.map((event) => event.id)));
  useEffect(() => {
    const additions = events
      .map((event) => event.id)
      .filter((id) => !seen.current.has(id));
    if (!additions.length) return;
    additions.forEach((id) => seen.current.add(id));
    setActiveKeys((previous) => [...previous, ...additions]);
  }, [events]);
  if (!events.length)
    return <Empty description="本次生成暂无详情。" />;
  return (
    <div className="generation-details">
      <Typography.Paragraph type="secondary" className="detail-intro">
        以下为本次生成过程中的系统 Prompt、完整模型输入、检索证据、工具调用与候选分数，随该条消息保存。
      </Typography.Paragraph>
      <Collapse
        size="small"
        activeKey={activeKeys}
        onChange={(keys) =>
          setActiveKeys(Array.isArray(keys) ? keys : [keys])
        }
        items={events.map((event) => ({
          key: event.id,
          label: (
            <span className="detail-label">
              <span className="detail-name">{labels[event.type]}</span>
              {event.round ? (
                <span className="detail-round">第 {event.round} 轮</span>
              ) : null}
              {event.query ? (
                <Typography.Text
                  className="detail-query-label"
                  type="secondary"
                  ellipsis={{ tooltip: event.query }}
                >
                  {event.query}
                </Typography.Text>
              ) : null}
            </span>
          ),
          children: <EventBody event={event} onEvidence={onEvidence} />,
        }))}
      />
    </div>
  );
}
