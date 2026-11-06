import { waitForJob, describeJob } from "../api/jobs";
import { useState, useEffect } from "react";
import { Alert, Button, Input, Space, Switch, Typography, Select } from "antd";
import { api } from "../api/client";
import EvaluationResults, { type ExperimentResult } from "./EvaluationResults";
export default function EvaluationPanel() {
  const [history, setHistory] = useState<
    { id: string; cases: number; scope: string; created_at: string }[]
  >([]);
  const refresh = () => api<typeof history>("evaluation").then(setHistory);
  const [generate, setGenerate] = useState(false);
  const [progress, setProgress] = useState("");
  const [dataset, setDataset] = useState(""),
    [rerank, setRerank] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [result, setResult] = useState<ExperimentResult>();
  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
  }, []);
  async function run() {
    setBusy(true);
    setError("");
    try {
      const cases = dataset
        .split("\n")
        .filter((v) => v.trim())
        .map((v) => JSON.parse(v));
      const job = await api<{ id: string }>("evaluation/jobs", {
        cases,
        include_reranker: rerank,
        generate_answers: generate,
      });
      setResult(
        await waitForJob<ExperimentResult>(job.id, (state) =>
          setProgress(describeJob(state)),
        ),
      );
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  function download() {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "retrieval-experiment.json";
    link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <>
      <Typography.Title level={5}>检索消融实验</Typography.Title>
      <Select
        style={{ width: "100%", marginBottom: 16 }}
        placeholder="查看历史实验"
        options={history.map((item) => ({
          value: item.id,
          label: `${item.cases} 题 · ${item.scope === "retrieval_only" ? "检索对比" : "问答对比"} · ${item.created_at ? new Date(item.created_at).toLocaleString("zh-CN") : item.id.slice(0, 8)}`,
        }))}
        onChange={(id) =>
          api<ExperimentResult>("evaluation/" + id)
            .then((value) => setResult({ ...value, id }))
            .catch((e) => setError(String(e)))
        }
      />
      <Typography.Paragraph>
        粘贴已完成相关性标注的
        JSONL。检索指标与答案评分分别统计，模型辅助评分需结合人工核验。
      </Typography.Paragraph>
      <Input.TextArea
        rows={8}
        value={dataset}
        onChange={(e) => setDataset(e.target.value)}
      />
      <Space style={{ margin: "16px 0" }}>
        <label className="inline-toggle">
          <Switch checked={generate} onChange={setGenerate} />
          同时生成回答（含基础模型）
        </label>
        <label className="inline-toggle">
          <Switch checked={rerank} onChange={setRerank} />
          纳入重排序方案
        </label>
        <Button loading={busy} disabled={!dataset.trim()} onClick={run}>
          运行实验
        </Button>
        <Button disabled={!result} onClick={download}>
          导出 JSON
        </Button>
      </Space>
      {progress && (
        <Typography.Paragraph type="secondary">{progress}</Typography.Paragraph>
      )}
      {error && <Alert type="error" message={error} />}
      {result && <EvaluationResults result={result} onChange={setResult} />}
    </>
  );
}
