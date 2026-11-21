import { Button, Space, Tag } from "antd";
import type { Evidence } from "../../types";

function scoreTags(item: Evidence) {
  return [
    ...Object.entries(item.scores ?? {}).map(([name, value]) => (
      <Tag key={"s-" + name}>
        {name}: {Number(value).toFixed(4)}
      </Tag>
    )),
    ...Object.entries(item.ranks ?? {}).map(([name, value]) => (
      <Tag key={"r-" + name}>
        {name} 排名: {value}
      </Tag>
    )),
  ];
}

export default function EvidenceBlock({
  item,
  onEvidence,
}: {
  item: Evidence;
  onEvidence: (evidence: Evidence) => void;
}) {
  const location = item.location;
  const label = location?.page
    ? `${location.path} · 第 ${location.page} 页`
    : location?.start_line != null
      ? `${location.path}:${location.start_line}–${location.end_line}`
      : location?.path || item.id;
  return (
    <div className="detail-evidence">
      <Button type="link" size="small" onClick={() => onEvidence(item)}>
        {label}
      </Button>
      <Space wrap size={[4, 4]}>
        {scoreTags(item)}
      </Space>
      <pre>{item.text}</pre>
    </div>
  );
}
