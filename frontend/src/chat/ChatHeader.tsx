import { Button, Space, Tag } from "antd";

export default function ChatHeader({
  title,
  rag,
  onExperiment,
  onSettings,
}: {
  title: string;
  rag: boolean;
  onExperiment: () => void;
  onSettings: () => void;
}) {
  return (
    <header className="topbar">
      <div>
        <span className="page-title">{title}</span>
        <Tag bordered={false} className="mode-tag">
          {rag ? "知识库检索" : "基础模型"}
        </Tag>
      </div>
      <Space>
        <Button type="text" onClick={onExperiment}>
          实验评估
        </Button>
        <Button onClick={onSettings}>问答设置</Button>
      </Space>
    </header>
  );
}
