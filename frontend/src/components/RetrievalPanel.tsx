import { Button, Space, Tag, Tabs, Typography } from "antd";
import type { Evidence } from "../types";
export type Comparison = Record<
  string,
  { results: Evidence[]; retrieval_ms: number; reranker_ms: number }
>;
export default function RetrievalPanel({
  comparison,
  onEvidence,
}: {
  comparison: Comparison;
  onEvidence: (evidence: Evidence) => void;
}) {
  const labels: Record<string, string> = {
    bm25: "关键词 BM25",
    dense: "向量 Dense",
    hybrid: "混合 Hybrid",
    hybrid_rerank: "混合 + 重排序",
  };
  return (
    <>
      <Typography.Paragraph type="secondary">
        各方案使用相同问题、候选数和源码版本。分数表示相关性，不代表答案正确率。
      </Typography.Paragraph>
      <Tabs
        items={Object.entries(comparison).map(([key, value]) => ({
          key,
          label: labels[key] ?? key,
          children: (
            <>
              <Typography.Text type="secondary">
                召回 {value.retrieval_ms.toFixed(0)} ms · 重排{" "}
                {value.reranker_ms.toFixed(0)} ms
              </Typography.Text>
              {value.results.map((item, index) => (
                <div className="retrieval-item" key={item.id}>
                  <Button type="link" onClick={() => onEvidence(item)}>
                    {index + 1}. {item.location.path}
                  </Button>
                  <Space wrap>
                    {Object.entries(item.scores ?? {}).map(([name, score]) => (
                      <Tag key={name}>
                        {name}: {score.toFixed(4)}
                      </Tag>
                    ))}
                    {Object.entries(item.ranks ?? {}).map(([name, rank]) => (
                      <Tag key={name}>
                        {name} 召回排名: {rank}
                      </Tag>
                    ))}
                  </Space>
                  <p>{item.text.slice(0, 500)}</p>
                </div>
              ))}
            </>
          ),
        }))}
      />
    </>
  );
}
