from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class TicketClass(str, Enum):
    CODE_DEFECT = "CODE_DEFECT"
    CONFIG_ENV = "CONFIG_ENV"
    DATA_ISSUE = "DATA_ISSUE"
    KNOWN_ERROR = "KNOWN_ERROR"
    THIRD_PARTY = "THIRD_PARTY"
    PERFORMANCE_CAPACITY = "PERFORMANCE_CAPACITY"
    ACCESS_PERMISSION = "ACCESS_PERMISSION"
    HOW_TO_USER_ERROR = "HOW_TO_USER_ERROR"
    INSUFFICIENT_INFO = "INSUFFICIENT_INFO"
    SECURITY_SENSITIVE = "SECURITY_SENSITIVE"


class Severity(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class SourceType(str, Enum):
    LOG = "log"
    CODE = "code"
    TICKET = "ticket"
    DOC = "doc"
    RECORD = "record"
    VISUAL = "visual"


class Stance(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXT = "context"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    DROPPED = "dropped"


class ContradictionKind(str, Enum):
    TIME_MISMATCH = "TIME_MISMATCH"
    BEHAVIOUR_MISMATCH = "BEHAVIOUR_MISMATCH"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    CHANGE_MISMATCH = "CHANGE_MISMATCH"
    STATE_MISMATCH = "STATE_MISMATCH"
    STALE_DOC_FLAG = "STALE_DOC_FLAG"


class DecisionBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PolicyAction(str, Enum):
    CONCLUDE = "CONCLUDE"
    CONCLUDE_WITH_CAVEAT = "CONCLUDE_WITH_CAVEAT"
    ABSTAIN = "ABSTAIN"
    ESCALATE_SECURITY = "ESCALATE_SECURITY"


class HumanContext(BaseModel):
    source: Literal["CLIENT_REPLY", "DEV_STEER"]
    message: str = Field(..., max_length=1000)
    parent_investigation_id: Optional[str] = None
    pinned_card_ids: List[str] = Field(default_factory=list)


class InvestigationCreateRequest(BaseModel):
    scenario_id: Optional[str] = None
    text: Optional[str] = Field(default=None, max_length=1500)
    attachments: List[str] = Field(default_factory=list)
    mode: Literal["live", "replay"] = "live"
    human_context: Optional[HumanContext] = None


class TicketDTO(BaseModel):
    id: str
    scenario_id: Optional[str] = None
    channel: str = "portal"
    reporter_role: str = "client"
    created_at: str
    text: str
    masked_text: Optional[str] = None
    pii_redacted_count: int = 0
    attachments: List[str] = Field(default_factory=list)
    product_hint: str = "transfers"
    human_context: Optional[HumanContext] = None


class AgentRoutingPlan(BaseModel):
    ticket_class: TicketClass
    severity: Severity
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    active_agents: List[Literal["HistoryAgent", "KnowledgeAgent", "LogsAgent", "CodeAgent", "RecordAgent"]]
    skipped_agents: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of skipped agent name to reason (e.g. {'CodeAgent': 'Pruned: How-To query requires docs only'})"
    )
    max_tool_calls: int = 12
    injection_detected: bool = False
    injection_note: Optional[str] = None


class VerificationResult(BaseModel):
    status: VerificationStatus = VerificationStatus.PENDING
    reason: Optional[str] = None


class EvidenceCard(BaseModel):
    card_id: str
    specialist: str
    source_type: SourceType
    pointer: Dict[str, Any] = Field(
        ...,
        description="log:{log_id,ts,service} | code:{repo,path,line_start,line_end,sha} | ticket:{system,id,field} | doc:{space,page_id,section,last_updated} | record:{table,id,field} | visual:{attachment_id}"
    )
    snippet: str = Field(..., max_length=400)
    claim: str = Field(..., max_length=200)
    stance: Stance = Stance.SUPPORTS
    observed_at: Optional[str] = None
    github_permalink: Optional[str] = None
    verification: VerificationResult = Field(default_factory=VerificationResult)


class Contradiction(BaseModel):
    kind: ContradictionKind
    deterministic: bool = True
    card_a: Optional[str] = None
    card_b: Optional[str] = None
    note: str


class Hypothesis(BaseModel):
    hypothesis_id: str
    statement: str
    culprit_files: List[str] = Field(default_factory=list)
    culprit_commit: Optional[str] = None
    supporting_card_ids: List[str] = Field(default_factory=list)
    contradicting_card_ids: List[str] = Field(default_factory=list)
    score: float = 0.0


class TrustComponents(BaseModel):
    c_ver: float = 0.0
    c_div: float = 0.0
    c_spec: float = 0.0
    c_time: float = 0.0
    p_contra: float = 0.0
    p_unver: float = 0.0


class TrustSummary(BaseModel):
    score: float
    band: DecisionBand
    policy_action: PolicyAction
    components: TrustComponents
    rationale: str


class ClientQuestion(BaseModel):
    text: str
    discriminates: List[str] = Field(default_factory=list)


class LeakCheckResult(BaseModel):
    passed: bool
    notes: List[str] = Field(default_factory=list)


class JiraDraft(BaseModel):
    title: str
    description: str
    repro_steps: List[str] = Field(default_factory=list)
    evidence_links: List[str] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)


class KBGap(BaseModel):
    page_id: str
    issue: str


class HumanDecision(BaseModel):
    status: Literal["pending", "approved", "edited", "rejected"] = "pending"
    by: Optional[str] = None
    reason: Optional[str] = None
    edits_diff: Optional[str] = None
    write_back_ref: Optional[str] = None


class ReportOutput(BaseModel):
    investigation_id: str
    ticket_id: str
    scenario_id: Optional[str] = None
    mode_used: Literal["live", "replay"] = "live"
    ticket_class: TicketClass
    severity: Severity
    owner_team: str
    summary: str
    routing_plan: AgentRoutingPlan
    probable_root_cause: Optional[Hypothesis] = None
    alternatives: List[Hypothesis] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    trust: TrustSummary
    verified_cards: List[EvidenceCard] = Field(default_factory=list)
    dropped_cards: List[EvidenceCard] = Field(default_factory=list)
    verified_claims_count: int = 0
    dropped_claims_count: int = 0
    recommended_actions: List[str] = Field(default_factory=list)
    workaround: Optional[str] = None
    questions_for_client: List[ClientQuestion] = Field(default_factory=list)
    customer_reply_draft: str
    leak_check: LeakCheckResult
    jira_draft: Optional[JiraDraft] = None
    kb_gap: Optional[KBGap] = None
    suggested_diagnostic_queries: List[str] = Field(default_factory=list)
    decision: HumanDecision = Field(default_factory=HumanDecision)
    audit_ref: str
    metrics: Dict[str, Any] = Field(
        default_factory=lambda: {"tool_calls": 0, "tokens": 0, "latency_ms": 0, "cost_usd": 0.0}
    )


class SSEEvent(BaseModel):
    seq: int
    ts: str
    type: Literal[
        "masking_done",
        "plan_created",
        "agent_skipped",
        "tool_started",
        "tool_finished",
        "card_added",
        "verifier_result",
        "contradiction_found",
        "hypothesis_update",
        "trust_update",
        "abstain",
        "report_ready",
        "awaiting_approval",
        "decision",
        "write_back_done",
        "replay_fallback",
        "error",
    ]
    data: Dict[str, Any]


class AuditChainEntry(BaseModel):
    seq: int
    ts: str
    investigation_id: str
    step: str
    payload_summary: Dict[str, Any]
    prev_hash: str
    hash: str