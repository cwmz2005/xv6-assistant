import { Button } from "antd";

export default function SessionSidebar({
  sessions,
  sid,
  busy,
  onNew,
  onLoad,
  onOpenKnowledge,
}: {
  sessions: { id: string; title: string }[];
  sid: string;
  busy: boolean;
  onNew: () => void;
  onLoad: (id: string) => void;
  onOpenKnowledge: () => void;
}) {
  return (
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
        onClick={onNew}
      >
        ＋ 新会话
      </Button>
      <div className="section-label">最近会话</div>
      <nav className="history">
        {sessions.length ? (
          sessions.map((session) => (
            <button
              key={session.id}
              className={
                sid === session.id ? "history-item active" : "history-item"
              }
              onClick={() => onLoad(session.id)}
            >
              {session.title}
            </button>
          ))
        ) : (
          <div className="history-empty">还没有会话</div>
        )}
      </nav>
      <div className="sidebar-bottom">
        <Button type="text" block onClick={onOpenKnowledge}>
          知识库文档
        </Button>
        <div className="sidebar-footnote">MIT · xv6-riscv · 2022</div>
      </div>
    </aside>
  );
}
