import { Space, Tag, Typography } from "antd";
import type { DetailEvent } from "../../types";

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

export function SystemPromptEvent({ event }: { event: DetailEvent }) {
  return (
    <>
      <Space wrap size={[6, 6]} className="detail-meta">
        <Tag>{event.rag === false ? "基础模型" : "知识库问答"}</Tag>
      </Space>
      <pre className="detail-prompt-text">{event.text}</pre>
    </>
  );
}

export function PromptEvent({ event }: { event: DetailEvent }) {
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
