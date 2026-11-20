import type { Comparison } from "./components/RetrievalPanel";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  Drawer,
  Input,
  InputNumber,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
  Popconfirm,
  Spin,
  Divider,
} from "antd";
import { api } from "./api/client";
import { streamChat } from "./api/stream";
import type { DetailEvent, Evidence, Message, TraceStep } from "./types";
const MessageCard = lazy(() => import("./components/MessageCard"));
const KnowledgePanel = lazy(() => import("./components/KnowledgePanel"));
const EvaluationPanel = lazy(() => import("./components/EvaluationPanel"));
const GenerationDetails = lazy(
  () => import("./components/GenerationDetails"),
);
type Panel =
  | "knowledge"
  | "settings"
  | "experiment"
  | "evidence"
  | "retrieval"
  | undefined;
type DetailSource =
  | { kind: "live" }
  | { kind: "message"; events: DetailEvent[] };
const RetrievalPanel = lazy(() => import("./components/RetrievalPanel"));
export default function ChatWorkspace() {
  const [sessions, setSessions] = useState<{ id: string; title: string }[]>([]),
    [sid, setSid] = useState(""),
    [messages, setMessages] = useState<Message[]>([]);
  const [versions, setVersions] = useState<
      { version: string; label: string }[]
    >([]),
    [version, setVersion] = useState<string>(),
    [question, setQuestion] = useState("");
  const [toolLimit, setToolLimit] = useState<number | null>(null);
  const [rag, setRag] = useState(true),
    [tools, setTools] = useState(false),
    [rerank, setRerank] = useState(true),
    [strategy, setStrategy] = useState("hybrid");
  const [top, setTop] = useState(5),
    [candidates, setCandidates] = useState(20),
    [rrf, setRrf] = useState(60);
  const [busy, setBusy] = useState(false),
    [draft, setDraft] = useState(""),
    [error, setError] = useState(""),
    [panel, setPanel] = useState<Panel>();
  const [evidence, setEvidence] = useState<Evidence>(),
    [retrieval, setRetrieval] = useState<Comparison>();
  const [liveTrace, setLiveTrace] = useState<TraceStep[]>([]),
    [liveDetails, setLiveDetails] = useState<DetailEvent[]>([]),
    [detailSource, setDetailSource] = useState<DetailSource>();
  const bottom = useRef<HTMLDivElement>(null);
  const refresh = () =>
    api<{ id: string; title: string }[]>("sessions").then(setSessions);
  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
    api<{ version: string; label: string }[]>("versions/details")
      .then(setVersions)
      .catch((e) => setError(String(e)));
  }, []);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [draft, messages, liveTrace]);
  const query = () => ({
    query: question,
    strategy,
    rerank,
    top_k: top,
    candidates: Math.max(top, candidates),
    rrf_k: rrf,
    version,
  });
  const resetLive = () => {
    setDraft("");
    setLiveTrace([]);
    setLiveDetails([]);
  };
  const resetDetails = () => setDetailSource(undefined);
  const openDetails = (items: DetailEvent[]) =>
    setDetailSource({ kind: "message", events: items });
  const openLiveDetails = () => setDetailSource({ kind: "live" });
  const detailOpen = detailSource !== undefined;
  const shownDetails =
    detailSource?.kind === "live" ? liveDetails : (detailSource?.events ?? []);
  const upsertTrace = (step: TraceStep) =>
    setLiveTrace((previous) => {
      const index = previous.findIndex((item) => item.id === step.id);
      if (index < 0) return [...previous, step];
      const next = [...previous];
      const current = next[index];
      next[index] =
        step.status === "delta"
          ? {
              ...current,
              ...step,
              text: (current.text ?? "") + (step.text ?? ""),
            }
          : { ...current, ...step };
      return next;
    });
  async function create() {
    const session = await api<{ id: string }>("sessions", {});
    setSid(session.id);
    setMessages([]);
    resetLive();
    resetDetails();
    await refresh();
    return session.id;
  }
  async function load(id: string) {
    if (busy) return;
    setSid(id);
    resetLive();
    resetDetails();
    setMessages(await api<Message[]>("sessions/" + id + "/messages"));
  }
  async function send() {
    if (!question.trim() || busy) return;
    setBusy(true);
    setError("");
    const text = question;
    try {
      const id = sid || (await create());
      setMessages((v) => [
        ...v,
        { role: "user", content: text, citations: [] },
      ]);
      setQuestion("");
      resetLive();
      resetDetails();
      const result = await streamChat(
        {
          ...query(),
          query: text,
          session_id: id,
          rag,
          tools,
          tool_call_limit: toolLimit,
        },
        {
          onToken: (token) => setDraft((v) => v + token),
          onTrace: upsertTrace,
          onDetail: (event) =>
            setLiveDetails((previous) => [...previous, event]),
        },
      );
      setMessages((v) => [
        ...v,
        {
          role: "assistant",
          content: result.answer,
          citations: result.citations,
          trace: result.trace ?? [],
          details: result.details ?? [],
        },
      ]);
      setDetailSource((current) =>
        current?.kind === "live"
          ? { kind: "message", events: result.details ?? [] }
          : current,
      );
      resetLive();
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function debug() {
    setBusy(true);
    try {
      setRetrieval(await api<Comparison>("search/compare", query()));
      setPanel("retrieval");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  const openEvidence = (item: Evidence) => {
    setEvidence(item);
    setPanel("evidence");
  };
  const panelTitle = {
    knowledge: "知识库",
    settings: "问答设置",
    experiment: "实验评估",
    evidence: "引用原文",
    retrieval: "检索结果",
  };
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">xv6</span>
          <div>
            知识库<span>操作系统学习空间</span>
          </div>
        </div>
        <Button
          className="new-chat"
          block
          disabled={busy}
          onClick={() => {
            setSid("");
            setMessages([]);
            setQuestion("");
            resetLive();
            resetDetails();
          }}
        >
          ＋ 新会话
        </Button>
        <div className="section-label">最近会话</div>
        <nav className="history">
          {sessions.length ? (
            sessions.map((s) => (
              <button
                key={s.id}
                className={
                  sid === s.id ? "history-item active" : "history-item"
                }
                onClick={() => load(s.id).catch((e) => setError(String(e)))}
              >
                {s.title}
              </button>
            ))
          ) : (
            <div className="history-empty">还没有会话</div>
          )}
        </nav>
        <div className="sidebar-bottom">
          <Button type="text" block onClick={() => setPanel("knowledge")}>
            知识库文档
          </Button>
          <div className="sidebar-footnote">MIT · xv6-riscv · 2022</div>
        </div>
      </aside>
      <main className="main-pane">
        <header className="topbar">
          <div>
            <span className="page-title">
              {sessions.find((s) => s.id === sid)?.title || "知识问答"}
            </span>
            <Tag bordered={false} className="mode-tag">
              {rag ? "知识库检索" : "基础模型"}
            </Tag>
          </div>
          <Space>
            <Button type="text" onClick={() => setPanel("experiment")}>
              实验评估
            </Button>
            <Button onClick={() => setPanel("settings")}>问答设置</Button>
          </Space>
        </header>
        <div className="conversation">
          {error && (
            <Alert
              type="error"
              message={error}
              closable
              onClose={() => setError("")}
            />
          )}
          {!messages.length && !draft && !liveTrace.length ? (
            <div className="welcome">
              <div className="eyebrow">XV6 / RISCV</div>
              <h1>从一个问题，读懂内核。</h1>
              <p>结合教材、实验指导与原始源码，追溯每一处依据。</p>
              <div className="starter-grid">
                {[
                  "walkaddr 为什么检查 PTE_U？",
                  "fork 如何复制父进程的地址空间？",
                  "持有自旋锁时，为什么要关闭中断？",
                ].map((q) => (
                  <button key={q} onClick={() => setQuestion(q)}>
                    {q}
                    <span>↗</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <Suspense fallback={<Spin />}>
              {messages.map((m, i) => (
                <MessageCard
                  key={i}
                  message={m}
                  onCitation={openEvidence}
                  onDetails={openDetails}
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
                  onCitation={openEvidence}
                  onDetails={openLiveDetails}
                />
              )}
            </Suspense>
          )}
          {busy && !draft && !liveTrace.length && (
            <div className="thinking">
              <Spin size="small" /> 正在处理
            </div>
          )}
          <div ref={bottom} />
        </div>
        <div className="composer-area">
          <div className="composer">
            <Input.TextArea
              variant="borderless"
              autoSize={{ minRows: 2, maxRows: 7 }}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="提问 xv6"
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            <div className="composer-footer">
              <Space size={16}>
                <label className="inline-toggle">
                  <Switch size="small" checked={rag} onChange={setRag} />
                  知识库
                </label>
                <label className="inline-toggle">
                  <Switch
                    size="small"
                    checked={tools}
                    disabled={!rag}
                    onChange={setTools}
                  />
                  补充搜索
                </label>
              </Space>
              <Space>
                <Button
                  type="text"
                  disabled={!question.trim() || busy}
                  onClick={debug}
                >
                  检索调试
                </Button>
                <Button
                  type="primary"
                  disabled={!question.trim()}
                  loading={busy}
                  onClick={send}
                >
                  发送 ↑
                </Button>
              </Space>
            </div>
          </div>
          <div className="composer-note">
            {rag
              ? "回答基于检索证据，引用可查看原文。"
              : "当前使用基础模型，不检索知识库。"}
            <span>Ctrl + Enter 发送</span>
          </div>
        </div>
      </main>
      <Drawer
        title={panel ? panelTitle[panel] : ""}
        width={panel === "knowledge" ? 920 : 720}
        open={!!panel}
        onClose={() => setPanel(undefined)}
        destroyOnHidden
      >
        <Suspense fallback={<Spin />}>
          {panel === "knowledge" && <KnowledgePanel />}
          {panel === "experiment" && <EvaluationPanel />}
          {panel === "settings" && (
            <div className="settings-stack">
              <div>
                <h3>检索策略</h3>
                <p>选择召回方式，比较不同检索阶段的效果。</p>
                <Select
                  value={strategy}
                  onChange={setStrategy}
                  options={[
                    { value: "hybrid", label: "混合检索 · Dense + BM25" },
                    { value: "dense", label: "向量检索 · Dense" },
                    { value: "bm25", label: "关键词检索 · BM25" },
                  ]}
                  style={{ width: "100%" }}
                />
              </div>
              <div>
                <h3>源码版本</h3>
                <p>仅检索所选源码版本；教材与实验指导始终参与检索。</p>
                <Select
                  style={{ width: "100%" }}
                  placeholder="默认 · util 原始版本"
                  allowClear
                  value={version}
                  onChange={setVersion}
                  options={versions.map((v) => ({
                    value: v.version,
                    label: v.label + " · " + v.version.slice(0, 10),
                  }))}
                />
              </div>
              <div className="setting-row">
                <div>
                  <h3>本地重排序</h3>
                  <p>使用 Cross-Encoder 重排候选，CPU 推理需要额外时间。</p>
                </div>
                <Switch checked={rerank} onChange={setRerank} />
              </div>
              <Divider />
              <InputNumber
                min={1}
                max={100}
                value={toolLimit}
                onChange={(v) => setToolLimit(v)}
                placeholder="检索次数上限，留空不限"
                style={{ width: 180 }}
              />
              <Space size={24} wrap>
                <label>
                  返回片段数
                  <InputNumber
                    min={1}
                    max={30}
                    value={top}
                    onChange={(v) => setTop(v ?? 5)}
                  />
                </label>
                <label>
                  候选数
                  <InputNumber
                    min={top}
                    max={100}
                    value={candidates}
                    onChange={(v) => setCandidates(v ?? 20)}
                  />
                </label>
                <label>
                  RRF 参数
                  <InputNumber
                    min={1}
                    value={rrf}
                    onChange={(v) => setRrf(v ?? 60)}
                  />
                </label>
              </Space>
              <p className="setting-note">
                初始 RAG 仅取 Top K 个候选；候选数用于补充检索与检索调试。
              </p>
              {sid && (
                <Popconfirm
                  title="删除当前会话和消息？"
                  onConfirm={async () => {
                    await api("sessions/" + sid, undefined, "DELETE");
                    setSid("");
                    setMessages([]);
                    await refresh();
                    setPanel(undefined);
                  }}
                >
                  <Button danger>删除当前会话</Button>
                </Popconfirm>
              )}
            </div>
          )}
          {panel === "evidence" && evidence && (
            <>
              <Typography.Title level={5}>
                {evidence.location.path}
              </Typography.Title>
              <Space wrap>
                <Tag>
                  {evidence.location.page
                    ? `第 ${evidence.location.page} 页`
                    : `行 ${evidence.location.start_line}–${evidence.location.end_line}`}
                </Tag>
                <Typography.Text type="secondary">
                  {evidence.location.section}
                </Typography.Text>
              </Space>
              <pre className="source-content">{evidence.text}</pre>
              <Typography.Paragraph type="secondary">
                来源：{evidence.location.source} · 版本：
                {evidence.location.commit}
              </Typography.Paragraph>
              <Typography.Text type="secondary" copyable>
                {evidence.id}
              </Typography.Text>
            </>
          )}
          {panel === "retrieval" && retrieval && (
            <RetrievalPanel comparison={retrieval} onEvidence={openEvidence} />
          )}
        </Suspense>
      </Drawer>
      <Drawer
        title="生成详情"
        width={640}
        open={detailOpen}
        onClose={() => setDetailSource(undefined)}
        destroyOnHidden
      >
        <Suspense fallback={<Spin />}>
          <GenerationDetails events={shownDetails} onEvidence={openEvidence} />
        </Suspense>
      </Drawer>
    </div>
  );
}
