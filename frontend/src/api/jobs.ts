import { api } from "./client";
export type Job<T> = {
  id: string;
  status: string;
  result?: T;
  error?: string;
  progress?: Record<string, unknown>;
};
export function describeJob<T>(job: Job<T>): string {
  const labels: Record<string, string> = {
    queued: "等待执行",
    running: "正在处理",
    completed: "已完成",
    failed: "执行失败",
  };
  const progress = job.progress ?? {};
  const detail = progress.current_path ?? progress.case_id ?? "";
  const count = progress.completed_answers ?? progress.processed;
  return [
    labels[job.status] ?? job.status,
    detail,
    count !== undefined ? `已处理 ${count} 项` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}
export async function waitForJob<T>(
  id: string,
  onProgress: (job: Job<T>) => void,
): Promise<T> {
  while (true) {
    const job = await api<Job<T>>("jobs/" + id);
    onProgress(job);
    if (job.status === "completed") return job.result!;
    if (job.status === "failed") throw Error(job.error || "任务失败");
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}
