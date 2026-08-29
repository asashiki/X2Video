export type JsonObject = Record<string, unknown>;

export interface RunRow {
  run_id: string;
  state: string;
  autonomy: string;
  format: string;
  summary: string;
  created_at: string;
  updated_at: string;
  is_paused: number;
  error?: string | null;
}

export interface TaskRow {
  task_id: string;
  task_type: string;
  target_state: string;
  tool_name?: string | null;
  status: string;
  attempt: number;
  max_attempts: number;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
}

export interface RunEvent {
  event_id: string;
  event_type: string;
  state: string;
  status?: string | null;
  summary: string;
  created_at: string;
  cost_usd: number;
  latency_ms: number;
  payload: JsonObject;
}

export interface EvidencePack extends JsonObject {
  evidence_pack_id: string;
  candidate_id: string;
  overall_confidence: number;
  context_completeness: number;
  risk_flags: string[];
  claims: Array<{ claim_id: string; normalized_claim: string; confidence: number }>;
  sources: Array<{ source_id: string; title: string; url: string; excerpt: string; trust_signals: string[] }>;
}

export interface Decision extends JsonObject {
  decision_id: string;
  candidate_id: string;
  selected: boolean;
  rank?: number | null;
  confidence: number;
  decision_summary: string;
  dimension_scores: Record<string, number>;
  risk_flags: string[];
  rejected_because: string[];
}

export interface Snapshot {
  run: RunRow & { budget: JsonObject; spent: JsonObject };
  goal: JsonObject & { query: string; target_duration_seconds: number; risk_tolerance: string };
  plan: JsonObject & { decision_summary: string };
  tasks: TaskRow[];
  events: RunEvent[];
  evidence: EvidencePack[];
  decisions: Decision[];
  script_issues: JsonObject[];
  quality_issues: JsonObject[];
  artifacts: JsonObject[];
  documents: Record<string, JsonObject>;
  media: { video?: string | null; cover?: string | null };
}

export interface MemoryCandidate {
  memory_id: string;
  run_id: string;
  memory_type: string;
  content: string;
  confidence: number;
  status: string;
  created_at: string;
}
