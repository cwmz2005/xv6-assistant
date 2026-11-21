import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { streamChat } from "../api/stream";
import type { Comparison } from "../components/RetrievalPanel";
import type { DetailEvent, Evidence, Message, TraceStep } from "../types";
import ChatComposer from "./ChatComposer";
import ChatHeader from "./ChatHeader";
import ConversationView from "./ConversationView";
import DetailsDrawer from "./DetailsDrawer";
import PanelDrawer from "./PanelDrawer";
import SessionSidebar from "./SessionSidebar";
import type { ChatSettings, DetailSource, Panel } from "./types";

const initialSettings: ChatSettings = {
  rag: true,
  tools: false,
  rerank: true,
  strategy: "hybrid",
  top: 5,
  candidates: 20,
  rrf: 60,
  version: undefined,
  toolLimit: null,
};

export default function ChatWorkspace() {
  const [sessions, setSessions] = useState<{ id: string; title: string }[]>([]);
  const [sid, setSid] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [versions, setVersions] = useState<
    { version: string; label: string }[]
  >([]);
  const [question, setQuestion] = useState("");
  const [settings, setSettings] = useState<ChatSettings>(initialSettings);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [panel, setPanel] = useState<Panel>();
  const [evidence, setEvidence] = useState<Evidence>();
  const [retrieval, setRetrieval] = useState<Comparison>();
  const [liveTrace, setLiveTrace] = useState<TraceStep[]>([]);
  const [liveDetails, setLiveDetails] = useState<DetailEvent[]>([]);
  const [detailSource, setDetailSource] = useState<DetailSource>();
  const bottom = useRef<HTMLDivElement>(null);

  const refresh = () =>
    api<{ id: string; title: string }[]>("sessions").then(setSessions);
  const updateSettings = (patch: Partial<ChatSettings>) =>
    setSettings((previous) => ({ ...previous, ...patch }));

  useEffect(() => {
    refresh().catch((cause) => setError(String(cause)));
    api<{ version: string; label: string }[]>("versions/details")
      .then(setVersions)
      .catch((cause) => setError(String(cause)));
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [draft, messages, liveTrace]);

  const query = () => ({
    query: question,
    strategy: settings.strategy,
    rerank: settings.rerank,
    top_k: settings.top,
    candidates: Math.max(settings.top, settings.candidates),
    rrf_k: settings.rrf,
    version: settings.version,
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

  async function loadSession(id: string) {
    if (busy) return;
    try {
      setSid(id);
      resetLive();
      resetDetails();
      setMessages(await api<Message[]>("sessions/" + id + "/messages"));
    } catch (cause) {
      setError(String(cause));
    }
  }

  async function send() {
    if (!question.trim() || busy) return;
    setBusy(true);
    setError("");
    const text = question;
    try {
      const id = sid || (await create());
      setMessages((previous) => [
        ...previous,
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
          rag: settings.rag,
          tools: settings.tools,
          tool_call_limit: settings.toolLimit,
        },
        {
          onToken: (token) => setDraft((previous) => previous + token),
          onTrace: upsertTrace,
          onDetail: (event) =>
            setLiveDetails((previous) => [...previous, event]),
        },
      );
      setMessages((previous) => [
        ...previous,
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
    } catch (cause) {
      setError(String(cause));
    } finally {
      setBusy(false);
    }
  }

  async function debug() {
    setBusy(true);
    try {
      setRetrieval(await api<Comparison>("search/compare", query()));
      setPanel("retrieval");
    } catch (cause) {
      setError(String(cause));
    } finally {
      setBusy(false);
    }
  }

  function newChat() {
    setSid("");
    setMessages([]);
    setQuestion("");
    resetLive();
    resetDetails();
  }

  async function deleteCurrentSession() {
    if (!sid) return;
    try {
      await api("sessions/" + sid, undefined, "DELETE");
      setSid("");
      setMessages([]);
      setQuestion("");
      resetLive();
      resetDetails();
      await refresh();
      setPanel(undefined);
    } catch (cause) {
      setError(String(cause));
    }
  }

  const openEvidence = (item: Evidence) => {
    setEvidence(item);
    setPanel("evidence");
  };

  const title =
    sessions.find((session) => session.id === sid)?.title || "知识问答";

  return (
    <div className="app-shell">
      <SessionSidebar
        sessions={sessions}
        sid={sid}
        busy={busy}
        onNew={newChat}
        onLoad={(id) => {
          void loadSession(id);
        }}
        onOpenKnowledge={() => setPanel("knowledge")}
      />
      <main className="main-pane">
        <ChatHeader
          title={title}
          rag={settings.rag}
          onExperiment={() => setPanel("experiment")}
          onSettings={() => setPanel("settings")}
        />
        <ConversationView
          messages={messages}
          draft={draft}
          liveTrace={liveTrace}
          liveDetails={liveDetails}
          busy={busy}
          error={error}
          onDismissError={() => setError("")}
          onCitation={openEvidence}
          onDetails={openDetails}
          onLiveDetails={openLiveDetails}
          onPickQuestion={setQuestion}
          bottomRef={bottom}
        />
        <ChatComposer
          question={question}
          onQuestionChange={setQuestion}
          rag={settings.rag}
          tools={settings.tools}
          busy={busy}
          onRagChange={(rag) => updateSettings({ rag })}
          onToolsChange={(tools) => updateSettings({ tools })}
          onSend={send}
          onDebug={debug}
        />
      </main>
      <PanelDrawer
        panel={panel}
        onClose={() => setPanel(undefined)}
        versions={versions}
        settings={settings}
        onChangeSettings={updateSettings}
        sid={sid}
        onDeleteSession={deleteCurrentSession}
        evidence={evidence}
        retrieval={retrieval}
        onEvidence={openEvidence}
      />
      <DetailsDrawer
        open={detailOpen}
        events={shownDetails}
        onClose={resetDetails}
        onEvidence={openEvidence}
      />
    </div>
  );
}
