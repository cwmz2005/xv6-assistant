import { Alert, Spin } from "antd";
import { lazy, Suspense, type RefObject } from "react";
import type { DetailEvent, Evidence, Message, TraceStep } from "../types";

const MessageCard = lazy(() => import("../components/MessageCard"));

const starters = [
  "walkaddr 为什么检查 PTE_U？",
  "fork 如何复制父进程的地址空间？",
  "持有自旋锁时，为什么要关闭中断？",
];

export default function ConversationView({
  messages,
  draft,
  liveTrace,
  liveDetails,
  busy,
  error,
  onDismissError,
  onCitation,
  onDetails,
  onLiveDetails,
  onPickQuestion,
  bottomRef,
}: {
  messages: Message[];
  draft: string;
  liveTrace: TraceStep[];
  liveDetails: DetailEvent[];
  busy: boolean;
  error: string;
  onDismissError: () => void;
  onCitation: (evidence: Evidence) => void;
  onDetails: (details: DetailEvent[]) => void;
  onLiveDetails: () => void;
  onPickQuestion: (question: string) => void;
  bottomRef: RefObject<HTMLDivElement | null>;
}) {
  return (
    <div className="conversation">
      {error && (
        <Alert type="error" message={error} closable onClose={onDismissError} />
      )}
      {!messages.length && !draft && !liveTrace.length ? (
        <div className="welcome">
          <div className="eyebrow">XV6 / RISCV</div>
          <h1>深挖源码，为你的 xv6 学习旅程保驾护航。</h1>
          <p>结合教材、实验指导与原始源码，追溯每一处依据。</p>
          <div className="starter-grid">
            {starters.map((starter) => (
              <button key={starter} onClick={() => onPickQuestion(starter)}>
                {starter}
                <span>↗</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <Suspense fallback={<Spin />}>
          {messages.map((message, index) => (
            <MessageCard
              key={index}
              message={message}
              onCitation={onCitation}
              onDetails={onDetails}
            />
          ))}
          {(draft || liveTrace.length > 0) && (
            <MessageCard
              key="live"
              streaming
              message={{
                role: "assistant",
                content: draft,
                citations: [],
                trace: liveTrace,
                details: liveDetails,
              }}
              onCitation={onCitation}
              onDetails={onLiveDetails}
            />
          )}
        </Suspense>
      )}
      {busy && !draft && !liveTrace.length && (
        <div className="thinking">
          <Spin size="small" /> 正在处理
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
