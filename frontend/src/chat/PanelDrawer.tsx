import { Drawer, Spin } from "antd";
import { lazy, Suspense } from "react";
import type { Comparison } from "../components/RetrievalPanel";
import type { Evidence } from "../types";
import EvidencePanel from "./EvidencePanel";
import SettingsPanel from "./SettingsPanel";
import type { ChatSettings, Panel } from "./types";

const KnowledgePanel = lazy(() => import("../components/KnowledgePanel"));
const EvaluationPanel = lazy(() => import("../components/EvaluationPanel"));
const RetrievalPanel = lazy(() => import("../components/RetrievalPanel"));

const panelTitles: Record<Exclude<Panel, undefined>, string> = {
  knowledge: "知识库",
  settings: "问答设置",
  experiment: "实验评估",
  evidence: "引用原文",
  retrieval: "检索结果",
};

export default function PanelDrawer({
  panel,
  onClose,
  versions,
  settings,
  onChangeSettings,
  sid,
  onDeleteSession,
  evidence,
  retrieval,
  onEvidence,
}: {
  panel: Panel;
  onClose: () => void;
  versions: { version: string; label: string }[];
  settings: ChatSettings;
  onChangeSettings: (patch: Partial<ChatSettings>) => void;
  sid: string;
  onDeleteSession: () => void;
  evidence?: Evidence;
  retrieval?: Comparison;
  onEvidence: (evidence: Evidence) => void;
}) {
  return (
    <Drawer
      title={panel ? panelTitles[panel] : ""}
      width={panel === "knowledge" ? 920 : 720}
      open={!!panel}
      onClose={onClose}
      destroyOnHidden
    >
      <Suspense fallback={<Spin />}>
        {panel === "knowledge" && <KnowledgePanel />}
        {panel === "experiment" && <EvaluationPanel />}
        {panel === "settings" && (
          <SettingsPanel
            settings={settings}
            onChange={onChangeSettings}
            versions={versions}
            sid={sid}
            onDeleteSession={onDeleteSession}
          />
        )}
        {panel === "evidence" && evidence && (
          <EvidencePanel evidence={evidence} />
        )}
        {panel === "retrieval" && retrieval && (
          <RetrievalPanel comparison={retrieval} onEvidence={onEvidence} />
        )}
      </Suspense>
    </Drawer>
  );
}
