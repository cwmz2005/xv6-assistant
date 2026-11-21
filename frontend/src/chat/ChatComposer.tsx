import { Button, Input, Space, Switch } from "antd";

export default function ChatComposer({
  question,
  onQuestionChange,
  rag,
  tools,
  busy,
  onRagChange,
  onToolsChange,
  onSend,
  onDebug,
}: {
  question: string;
  onQuestionChange: (value: string) => void;
  rag: boolean;
  tools: boolean;
  busy: boolean;
  onRagChange: (value: boolean) => void;
  onToolsChange: (value: boolean) => void;
  onSend: () => void;
  onDebug: () => void;
}) {
  return (
    <div className="composer-area">
      <div className="composer">
        <Input.TextArea
          variant="borderless"
          autoSize={{ minRows: 2, maxRows: 7 }}
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          placeholder="向 xv6 学习助手提问"
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
              event.preventDefault();
              onSend();
            }
          }}
        />
        <div className="composer-footer">
          <Space size={16}>
            <label className="inline-toggle">
              <Switch size="small" checked={rag} onChange={onRagChange} />
              知识库
            </label>
            <label className="inline-toggle">
              <Switch
                size="small"
                checked={tools}
                disabled={!rag}
                onChange={onToolsChange}
              />
              补充搜索
            </label>
          </Space>
          <Space>
            <Button
              type="text"
              disabled={!question.trim() || busy}
              onClick={onDebug}
            >
              检索调试
            </Button>
            <Button
              type="primary"
              disabled={!question.trim()}
              loading={busy}
              onClick={onSend}
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
  );
}
