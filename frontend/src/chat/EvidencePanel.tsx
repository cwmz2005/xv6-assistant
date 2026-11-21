import { Space, Tag, Typography } from "antd";
import type { Evidence } from "../types";

export default function EvidencePanel({ evidence }: { evidence: Evidence }) {
  return (
    <>
      <Typography.Title level={5}>{evidence.location.path}</Typography.Title>
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
        来源：{evidence.location.source} · 版本：{evidence.location.commit}
      </Typography.Paragraph>
      <Typography.Text type="secondary" copyable>
        {evidence.id}
      </Typography.Text>
    </>
  );
}
