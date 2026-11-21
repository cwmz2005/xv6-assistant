import {
  Button,
  Divider,
  InputNumber,
  Popconfirm,
  Select,
  Space,
  Switch,
} from "antd";
import type { ChatSettings } from "./types";

export default function SettingsPanel({
  settings,
  onChange,
  versions,
  sid,
  onDeleteSession,
}: {
  settings: ChatSettings;
  onChange: (patch: Partial<ChatSettings>) => void;
  versions: { version: string; label: string }[];
  sid: string;
  onDeleteSession: () => void | Promise<void>;
}) {
  return (
    <div className="settings-stack">
      <div>
        <h3>检索策略</h3>
        <p>选择召回方式，比较不同检索阶段的效果。</p>
        <Select
          value={settings.strategy}
          onChange={(strategy) => onChange({ strategy })}
          options={[
            { value: "hybrid", label: "混合检索 · Dense + BM25" },
            { value: "dense", label: "向量检索 · Dense" },
            { value: "bm25", label: "关键词检索 · BM25" },
          ]}
          style={{ width: "100%" }}
        />
      </div>
      <div>
        <h3>源码版本</h3>
        <p>仅检索所选源码版本；教材与实验指导始终参与检索。</p>
        <Select
          style={{ width: "100%" }}
          placeholder="默认 · util 原始版本"
          allowClear
          value={settings.version}
          onChange={(version?: string) => onChange({ version })}
          options={versions.map((item) => ({
            value: item.version,
            label: item.label + " · " + item.version.slice(0, 10),
          }))}
        />
      </div>
      <div className="setting-row">
        <div>
          <h3>本地重排序</h3>
          <p>使用 Cross-Encoder 重排候选，CPU 推理需要额外时间。</p>
        </div>
        <Switch
          checked={settings.rerank}
          onChange={(rerank) => onChange({ rerank })}
        />
      </div>
      <Divider />
      <InputNumber
        min={1}
        max={100}
        value={settings.toolLimit}
        onChange={(toolLimit) => onChange({ toolLimit })}
        placeholder="检索次数上限，留空不限"
        style={{ width: 180 }}
      />
      <Space size={24} wrap>
        <label>
          返回片段数
          <InputNumber
            min={1}
            max={30}
            value={settings.top}
            onChange={(top) => onChange({ top: top ?? 5 })}
          />
        </label>
        <label>
          候选数
          <InputNumber
            min={settings.top}
            max={100}
            value={settings.candidates}
            onChange={(candidates) => onChange({ candidates: candidates ?? 20 })}
          />
        </label>
        <label>
          RRF 参数
          <InputNumber
            min={1}
            value={settings.rrf}
            onChange={(rrf) => onChange({ rrf: rrf ?? 60 })}
          />
        </label>
      </Space>
      <p className="setting-note">
        初始 RAG 仅取 Top K 个候选；候选数用于补充检索与检索调试。
      </p>
      {sid && (
        <Popconfirm
          title="删除当前会话和消息？"
          onConfirm={onDeleteSession}
        >
          <Button danger>删除当前会话</Button>
        </Popconfirm>
      )}
    </div>
  );
}
