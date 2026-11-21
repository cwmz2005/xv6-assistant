import { Drawer, Spin } from "antd";
import { lazy, Suspense } from "react";
import type { DetailEvent, Evidence } from "../types";

const GenerationDetails = lazy(() => import("../components/GenerationDetails"));

export default function DetailsDrawer({
  open,
  events,
  onClose,
  onEvidence,
}: {
  open: boolean;
  events: DetailEvent[];
  onClose: () => void;
  onEvidence: (evidence: Evidence) => void;
}) {
  return (
    <Drawer
      title="生成详情"
      width={640}
      open={open}
      onClose={onClose}
      destroyOnHidden
    >
      <Suspense fallback={<Spin />}>
        <GenerationDetails events={events} onEvidence={onEvidence} />
      </Suspense>
    </Drawer>
  );
}
