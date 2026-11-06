import { waitForJob, describeJob } from "../api/jobs";
import { useState } from "react";
import { Alert, Button, Input, Space, Table, Popconfirm, Tag } from "antd";
import { api } from "../api/client";
type Document = {
  id: string;
  path: string;
  commit: string;
  chunks: number;
  is_system: boolean;
};
export default function KnowledgePanel() {
  const [root, setRoot] = useState("data/labs"),
    [commit, setCommit] = useState(""),
    [busy, setBusy] = useState(false),
    [status, setStatus] = useState(""),
    [documents, setDocuments] = useState<Document[]>([]),
    [chunks, setChunks] = useState<unknown>();
  async function refresh() {
    setDocuments(await api<Document[]>("documents"));
  }
  const protectionColumn = {
    title: "文档保护",
    render: (_: unknown, row: Document) =>
      row.is_system ? (
        <Tag>系统文档</Tag>
      ) : (
        <Popconfirm
          title="删除此文档及全部片段？"
          onConfirm={async () => {
            try {
              await api("documents/" + row.id, undefined, "DELETE");
              await refresh();
              setChunks(undefined);
            } catch (e) {
              setStatus(String(e));
            }
          }}
        >
          <Button danger size="small">
            删除
          </Button>
        </Popconfirm>
      ),
  };
  async function ingest() {
    setBusy(true);
    setStatus("正在导入");
    try {
      const job = await api<{ id: string }>("import/jobs", {
        root,
        commit: commit || null,
      });
      const result = await waitForJob<{ chunks: number }>(job.id, (state) =>
        setStatus(describeJob(state)),
      );
      setStatus("导入完成，新增 " + result.chunks + " 个片段");
      await refresh();
    } catch (e) {
      setStatus(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Space direction="vertical" style={{ width: "100%" }}>
        <Input
          value={root}
          onChange={(e) => setRoot(e.target.value)}
          placeholder="本地数据目录"
        />
        <Input
          value={commit}
          onChange={(e) => setCommit(e.target.value)}
          placeholder="Git 原始提交；普通目录留空"
        />
        <Space>
          <Button loading={busy} onClick={ingest}>
            导入并索引
          </Button>
          <Button onClick={() => refresh().catch((e) => setStatus(String(e)))}>
            刷新文档
          </Button>
        </Space>
        {status && <Alert message={status} />}
      </Space>
      <Table
        rowKey="id"
        dataSource={documents}
        size="small"
        columns={[
          protectionColumn,
          { title: "文件", dataIndex: "path" },
          { title: "版本", dataIndex: "commit", ellipsis: true },
          { title: "片段", dataIndex: "chunks" },
          {
            title: "原文",
            render: (_, row) => (
              <Button
                onClick={() =>
                  api("documents/" + row.id + "/chunks")
                    .then(setChunks)
                    .catch((e) => setStatus(String(e)))
                }
              >
                查看
              </Button>
            ),
          },
        ]}
      />
      <pre style={{ whiteSpace: "pre-wrap" }}>
        {JSON.stringify(chunks, null, 2)}
      </pre>
    </>
  );
}
