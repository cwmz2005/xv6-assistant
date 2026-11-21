import "highlight.js/styles/github.css";
import { Button, Space } from "antd";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import type { DetailEvent, Evidence, Message } from "../types";
import ProcessTrace from "./ProcessTrace";

export default function MessageCard({
  message,
  onCitation,
  onDetails,
  streaming = false,
}: {
  message: Message;
  onCitation: (evidence: Evidence) => void;
  onDetails?: (details: DetailEvent[]) => void;
  streaming?: boolean;
}) {
  const content = message.content.replace(
    /\[([0-9a-f]{8,64})\]/g,
    (_, id: string) => {
      const index = message.citations.findIndex((c) => c.id === id);
      return index >= 0 ? `[${index + 1}](#evidence-${id})` : "〔引用〕";
    },
  );
  const processSteps =
    message.trace?.filter((step) => step.type !== "answer") ?? [];
  const details = message.details ?? [];
  return (
    <article
      className={`message ${message.role === "user" ? "user" : "assistant"}`}
    >
      <div className="message-label">
        <span>{message.role === "user" ? "你" : "xv6"}</span>
        {message.role !== "user" && details.length && onDetails ? (
          <button
            type="button"
            className="message-details-link"
            onClick={() => onDetails(details)}
          >
            生成详情 · {details.length} 项
          </button>
        ) : null}
      </div>
      {processSteps.length ? (
        <ProcessTrace trace={processSteps} streaming={streaming} />
      ) : null}
      {message.content ? (
        <Markdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeHighlight]}
          components={{
            a: ({ href, children }) => {
              const evidence = message.citations.find(
                (c) => href === "#evidence-" + c.id,
              );
              return evidence ? (
                <button
                  className="inline-citation"
                  onClick={() => onCitation(evidence)}
                  title={evidence.location.path}
                >
                  {children}
                </button>
              ) : (
                <a href={href} target="_blank" rel="noreferrer">
                  {children}
                </a>
              );
            },
          }}
        >
          {content}
        </Markdown>
      ) : null}
      <Space wrap>
        {message.citations.map((c) => (
          <Button
            className="citation-chip"
            size="small"
            key={c.id}
            onClick={() => onCitation(c)}
          >
            {c.location.path}
            {c.location.page
              ? ` · 第 ${c.location.page} 页`
              : `:${c.location.start_line}–${c.location.end_line}`}
          </Button>
        ))}
      </Space>
    </article>
  );
}
