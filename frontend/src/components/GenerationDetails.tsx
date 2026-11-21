import { Collapse, Empty, Typography } from "antd";
import { useEffect, useRef, useState } from "react";
import type { DetailEvent, Evidence } from "../types";
import EventBody from "./generation/EventBody";

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
