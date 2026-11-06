import { useState } from "react";
import {
  Button,
  Input,
  InputNumber,
  Space,
  Table,
  Typography,
  Alert,
  Collapse,
} from "antd";
import type { Evidence } from "../types";
import { api } from "../api/client";
import { waitForJob } from "../api/jobs";
type Row = {
  case_id: string;
  strategy: string;
  rerank?: boolean;
  answer?: string;
  reference_answer?: string;
  accuracy?: number;
  results?: Evidence[];
  citations?: Evidence[];
  llm_judge?: {
    score: number;
    rationale: string;
    limitations: string;
    independent_model: boolean;
  };
  human_review?: { score: number; reviewer: string; notes: string };
};
export type ExperimentResult = {
  id: string;
  summary: {
    variant: string;
    cases: number;
    recall: number | null;
    mrr: number | null;
    ndcg: number | null;
    retrieval_ms: number | null;
    reranker_ms: number | null;
    human_score: number | null;
    human_reviewed: number;
    judge_score?: number | null;
  }[];
  records: Row[];
};
export default function EvaluationResults({
  result,
  onChange,
}: {
  result: ExperimentResult;
  onChange: (result: ExperimentResult) => void;
}) {
  const [reviewer, setReviewer] = useState(""),
    [notes, setNotes] = useState(""),
    [score, setScore] = useState(1),
    [error, setError] = useState("");
  const [judging, setJudging] = useState(false);
  const number = (v: number | null | undefined) =>
    v == null ? "—" : v.toFixed(3);
  async function judge() {
    setJudging(true);
    try {
      const job = await api<{ id: string }>(
        "evaluation/" + result.id + "/judge",
        {},
      );
      onChange(await waitForJob<ExperimentResult>(job.id, () => {}));
    } catch (e) {
      setError(String(e));
    } finally {
      setJudging(false);
    }
  }
  async function review(index: number) {
    try {
      const updated = await api<ExperimentResult>(
        "evaluation/" + result.id + "/reviews",
        { record_index: index, reviewer, notes, score },
      );
      onChange({ ...updated, id: result.id });
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <>
      <Typography.Title level={5}>方案汇总</Typography.Title>
      <Typography.Paragraph type="secondary">
        模型辅助评分可能使用同一生成模型，存在自评偏差，不等同于人工准确率。
      </Typography.Paragraph>
      <Button
        loading={judging}
        disabled={!result.records.some((row) => row.answer)}
        onClick={judge}
      >
        模型辅助核验
      </Button>
      <Table
        size="small"
        pagination={false}
        rowKey="variant"
        dataSource={result.summary}
        scroll={{ x: 700 }}
        columns={[
          { title: "方案", dataIndex: "variant" },
          { title: "Recall", dataIndex: "recall", render: number },
          { title: "MRR", dataIndex: "mrr", render: number },
          { title: "nDCG", dataIndex: "ndcg", render: number },
          { title: "召回 ms", dataIndex: "retrieval_ms", render: number },
          { title: "重排 ms", dataIndex: "reranker_ms", render: number },
          { title: "人工评分", dataIndex: "human_score", render: number },
          { title: "模型辅助分", dataIndex: "judge_score", render: number },
          { title: "已核验", dataIndex: "human_reviewed" },
        ]}
      />
      <Typography.Title level={5}>逐题核验</Typography.Title>
      <Typography.Paragraph type="secondary">
        评分范围 0–1：错误为 0，部分正确可取 0.5，正确完整为
        1。请依据参考答案和实际证据独立判断。
      </Typography.Paragraph>
      <Input
        value={reviewer}
        onChange={(e) => setReviewer(e.target.value)}
        placeholder="核验人"
      />
      <Input.TextArea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="评分依据"
        style={{ margin: "10px 0" }}
      />
      <Space>
        答案评分
        <InputNumber
          min={0}
          max={1}
          step={0.1}
          value={score}
          onChange={(v) => setScore(v ?? 0)}
        />
      </Space>
      {error && <Alert type="error" message={error} />}
      <Table
        rowKey="index"
        size="small"
        dataSource={result.records.map((r, index) => ({ ...r, index }))}
        columns={[
          { title: "问题", dataIndex: "case_id" },
          {
            title: "方案",
            render: (_, r) => r.strategy + (r.rerank ? " + 重排" : ""),
          },
          {
            title: "评分",
            dataIndex: "accuracy",
            render: (v) => v ?? "待核验",
          },
          {
            title: "核验",
            render: (_, r) => (
              <Button
                size="small"
                disabled={!r.answer || !reviewer.trim() || !notes.trim()}
                onClick={() => review(r.index)}
              >
                保存评分
              </Button>
            ),
          },
        ]}
        expandable={{
          expandedRowRender: (r) => (
            <>
              <Typography.Text strong>参考答案</Typography.Text>
              <p>{r.reference_answer || "未生成回答"}</p>
              <Typography.Text strong>实际回答</Typography.Text>
              <p style={{ whiteSpace: "pre-wrap" }}>{r.answer}</p>
              <Collapse
                size="small"
                items={(r.results ?? r.citations ?? []).map((evidence) => ({
                  key: evidence.id,
                  label:
                    evidence.location.path +
                    (evidence.location.page
                      ? ` · 第 ${evidence.location.page} 页`
                      : `:${evidence.location.start_line}–${evidence.location.end_line}`),
                  children: (
                    <>
                      <pre className="source-content">{evidence.text}</pre>
                      <Typography.Text type="secondary" copyable>
                        {evidence.id}
                      </Typography.Text>
                    </>
                  ),
                }))}
              />
              {r.llm_judge && (
                <Alert
                  type="info"
                  message={`模型辅助分：${r.llm_judge.score}`}
                  description={
                    r.llm_judge.rationale + " " + r.llm_judge.limitations
                  }
                />
              )}
              {r.human_review && (
                <p>
                  {r.human_review.reviewer}：{r.human_review.notes}
                </p>
              )}
            </>
          ),
        }}
      />
    </>
  );
}
