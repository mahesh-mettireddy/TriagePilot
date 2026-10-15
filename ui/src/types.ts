export type TicketClass =
  | 'CODE_DEFECT'
  | 'CONFIG_ENV'
  | 'DATA_ISSUE'
  | 'KNOWN_ERROR'
  | 'THIRD_PARTY'
  | 'PERFORMANCE_CAPACITY'
  | 'ACCESS_PERMISSION'
  | 'HOW_TO_USER_ERROR'
  | 'INSUFFICIENT_INFO'
  | 'SECURITY_SENSITIVE';

export type Severity = 'P1' | 'P2' | 'P3' | 'P4';

export type SourceType = 'log' | 'code' | 'ticket' | 'doc' | 'record' | 'visual';

export type Stance = 'supports' | 'contradicts' | 'context';

export type VerificationStatus = 'pending' | 'verified' | 'dropped';

export type ContradictionKind =
  | 'TIME_MISMATCH'
  | 'BEHAVIOUR_MISMATCH'
  | 'SCOPE_MISMATCH'
  | 'CHANGE_MISMATCH'
  | 'STATE_MISMATCH'
  | 'STALE_DOC_FLAG';

export type DecisionBand = 'HIGH' | 'MEDIUM' | 'LOW';

export type PolicyAction =
  | 'CONCLUDE'
  | 'CONCLUDE_WITH_CAVEAT'
  | 'ABSTAIN'
  | 'ESCALATE_SECURITY';

export interface HumanContext {
  source: 'CLIENT_REPLY' | 'DEV_STEER';
  message: string;
  parent_investigation_id?: string;
  pinned_card_ids?: string[];
}

export interface InvestigationCreateRequest {
  scenario_id?: string;
  text?: string;
  attachments?: string[];
  mode?: 'live' | 'replay';
  human_context?: HumanContext;
}

export interface TicketDTO {
  id: string;
  scenario_id?: string;
  channel?: string;
  reporter_role?: string;
  created_at: string;
  text: string;
  masked_text?: string;
  pii_redacted_count?: number;
  attachments?: string[];
  product_hint?: string;
  human_context?: HumanContext;
}

export interface AgentRoutingPlan {
  ticket_class: TicketClass;
  severity: Severity;
  extracted_entities: Record<string, any>;
  active_agents: Array<'HistoryAgent' | 'KnowledgeAgent' | 'LogsAgent' | 'CodeAgent' | 'RecordAgent'>;
  skipped_agents: Record<string, string>;
  max_tool_calls: number;
  tool_calls_used?: number;
  tool_budget_rejections?: number;
  injection_detected: boolean;
  injection_note?: string;
}

export interface VerificationResult {
  status: VerificationStatus;
  reason?: string;
}

export interface EvidenceCard {
  card_id: string;
  specialist: string;
  source_type: SourceType;
  pointer: Record<string, any>;
  snippet: string;
  claim: string;
  stance: Stance;
  observed_at?: string;
  github_permalink?: string;
  verification: VerificationResult;
}

export interface Contradiction {
  kind: ContradictionKind;
  deterministic: boolean;
  card_a?: string;
  card_b?: string;
  note: string;
}

export interface Hypothesis {
  hypothesis_id: string;
  statement: string;
  culprit_files: string[];
  culprit_commit?: string;
  supporting_card_ids: string[];
  contradicting_card_ids: string[];
  score: number;
}

export interface TrustComponents {
  c_ver: number;
  c_div: number;
  c_spec: number;
  c_time: number;
  p_contra: number;
  p_unver: number;
}

export interface TrustSummary {
  score: number;
  band: DecisionBand;
  policy_action: PolicyAction;
  components: TrustComponents;
  rationale: string;
}

export interface ClientQuestion {
  text: string;
  discriminates: string[];
}

export interface LeakCheckResult {
  passed: boolean;
  notes: string[];
}

export interface JiraDraft {
  title: string;
  description: string;
  repro_steps: string[];
  evidence_links: string[];
  labels: string[];
}

export interface KBGap {
  page_id: string;
  issue: string;
}

export interface HumanDecision {
  status: 'pending' | 'approved' | 'edited' | 'rejected';
  by?: string;
  reason?: string;
  edits_diff?: string;
  write_back_ref?: string;
  report_revision?: number;
  report_hash?: string;
  decision_id?: string;
}

export interface ExecutionMetadata {
  provider: string;
  mode: 'vertex_ai' | 'api_key' | 'fallback' | 'replay';
  configured: boolean;
  models: string[];
  calls: Array<{ operation: string; model: string; mode: string; error?: string }>;
  fallback_reason?: string;
}

export interface ReportOutput {
  investigation_id: string;
  ticket_id: string;
  scenario_id?: string;
  mode_used: 'live' | 'replay';
  ticket_class: TicketClass;
  severity: Severity;
  owner_team: string;
  summary: string;
  routing_plan: AgentRoutingPlan;
  probable_root_cause?: Hypothesis;
  alternatives: Hypothesis[];
  contradictions: Contradiction[];
  trust: TrustSummary;
  verified_cards: EvidenceCard[];
  dropped_cards: EvidenceCard[];
  verified_claims_count: number;
  dropped_claims_count: number;
  recommended_actions: string[];
  workaround?: string;
  questions_for_client: ClientQuestion[];
  customer_reply_draft: string;
  leak_check: LeakCheckResult;
  jira_draft?: JiraDraft;
  kb_gap?: KBGap;
  suggested_diagnostic_queries: string[];
  decision: HumanDecision;
  audit_ref: string;
  execution: ExecutionMetadata;
  report_revision: number;
  report_hash: string;
  write_back_allowed?: boolean;
  needs_human_edit?: boolean;
  metrics: {
    tool_calls: number;
    tokens: number;
    latency_ms: number;
    cost_usd: number;
    model_calls?: number;
    tool_budget_limit?: number;
    tool_budget_rejections?: number;
  };
}

export interface SSEEvent {
  seq: number;
  ts: string;
  type: string;
  data: Record<string, any>;
}

export interface AuditChainEntry {
  seq: number;
  ts: string;
  investigation_id: string;
  step: string;
  payload_summary: Record<string, any>;
  prev_hash: string;
  hash: string;
}

export interface ScenarioMeta {
  id: string;
  title: string;
  ticket_class: TicketClass;
  tags: string[];
  description: string;
}
