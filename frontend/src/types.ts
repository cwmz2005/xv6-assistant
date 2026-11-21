export type Evidence = {
  id: string;
  text: string;
  scores?: Record<string, number>;
  ranks?: Record<string, number>;
  location: {
    path: string;
    start_line: number | null;
    end_line: number | null;
    page?: number;
    page_label?: string;
    section?: string;
    commit?: string;
    source?: string;
  };
};

export type TraceTop = {
  id?: string;
  label?: string;
  score?: number | null;
};

export type TraceStep = {
  id: string;
  type: "thinking" | "search" | "retrieval" | "answer";
  status?: "delta" | "running" | "done" | "skipped";
  text?: string;
  query?: string;
  path_regex?: string | null;
  version?: string | null;
  version_label?: string | null;
  round?: number;
  count?: number;
  added?: number;
  total?: number;
  candidates?: number;
  cached?: boolean;
  reason?: string;
  citations?: number;
  finish_reason?: string | null;
  complete?: boolean | null;
  strategy?: string;
  rerank?: boolean;
  retrieval_ms?: number;
  reranker_ms?: number;
  top?: TraceTop[];
};

export type CandidateScore = {
  id: string;
  ranks?: Record<string, number>;
  scores?: Record<string, number>;
};

export type PromptMessage = {
  type: string;
  content: unknown;
  tool_calls?: unknown[];
  tool_call_id?: string;
  name?: string;
};

export type DetailEvent = {
  id: string;
  type:
    | "rag_context"
    | "tool_call"
    | "tool_result"
    | "final_context"
    | "system_prompt"
    | "prompt";
  text?: string;
  rag?: boolean;
  messages?: PromptMessage[];
  query?: string;
  path_regex?: string | null;
  error?: string;
  round?: number;
  strategy?: string;
  top_k?: number;
  candidates?: number;
  rerank?: boolean;
  rrf_k?: number;
  version?: string | null;
  version_label?: string | null;
  retrieval_ms?: number;
  reranker_ms?: number;
  added?: number;
  cached?: boolean;
  results?: Evidence[];
  candidate_scores?: CandidateScore[];
  evidence_count?: number;
  evidence_ids?: string[];
  citation_ids?: string[];
  finish_reason?: string | null;
};

export type Message = {
  role: string;
  content: string;
  citations: Evidence[];
  trace?: TraceStep[];
  details?: DetailEvent[];
};
