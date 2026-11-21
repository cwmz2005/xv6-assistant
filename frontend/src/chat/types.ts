import type { DetailEvent } from "../types";

export type Panel =
  | "knowledge"
  | "settings"
  | "experiment"
  | "evidence"
  | "retrieval"
  | undefined;

export type DetailSource =
  | { kind: "live" }
  | { kind: "message"; events: DetailEvent[] };

export type ChatSettings = {
  rag: boolean;
  tools: boolean;
  rerank: boolean;
  strategy: string;
  top: number;
  candidates: number;
  rrf: number;
  version?: string;
  toolLimit: number | null;
};
