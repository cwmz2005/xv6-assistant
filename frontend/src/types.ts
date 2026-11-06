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
export type Message = { role: string; content: string; citations: Evidence[] };
