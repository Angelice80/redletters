// TODO: Sprint 4 - Generate from OpenAPI spec
// These types are manually defined based on src/redletters/engine_spine/models.py
// Keep in sync with Python models until OpenAPI generation is implemented.

// --- Enums ---

export type JobState =
  | "queued"
  | "running"
  | "cancelling"
  | "cancelled"
  | "completed"
  | "failed"
  | "archived";

/** Sprint 18: Job type discriminator */
export type JobType = "translation" | "scholarly";

export type EngineMode = "normal" | "safe";

export type EngineHealth = "healthy" | "degraded";

export type LogLevel = "trace" | "debug" | "info" | "warn" | "error";

// --- Request/Response Models ---

export interface JobConfig {
  job_type?: JobType; // Sprint 18: Job type discriminator
  input_paths: string[];
  output_dir?: string;
  style: string;
  options: Record<string, unknown>;
  // Sprint 18: Scholarly job fields (only used when job_type == "scholarly")
  reference?: string;
  mode?: "readable" | "traceable";
  force?: boolean;
  session_id?: string;
  include_schemas?: boolean;
  create_zip?: boolean;
}

export interface JobCreateRequest {
  config: JobConfig;
  idempotency_key?: string;
}

export interface JobResponse {
  job_id: string;
  state: JobState;
  created_at: string; // ISO datetime
  started_at?: string;
  completed_at?: string;
  config: JobConfig;
  progress_percent?: number;
  progress_phase?: string;
  error_code?: string;
  error_message?: string;
  // Sprint 18: Job result payload (populated for completed scholarly jobs)
  result?: ScholarlyJobResult | Record<string, unknown>;
}

/**
 * Sprint 19: Backend shape for GUI mismatch detection.
 * Populated by introspecting app.routes at startup.
 */
export interface BackendShape {
  backend_mode: "full" | "engine_only";
  has_translate: boolean;
  has_sources_status: boolean;
  has_acknowledge: boolean;
  has_variants_dossier: boolean;
}

export interface EngineStatus {
  version: string;
  build_hash: string;
  api_version: string;
  capabilities: string[];
  mode: EngineMode;
  health: EngineHealth;
  uptime_seconds: number;
  active_jobs: number;
  queue_depth: number;
  // Sprint 19: Backend shape for mismatch detection
  shape?: BackendShape;
}

// --- SSE Event Models ---

export interface BaseEvent {
  event_type: string;
  sequence_number: number;
  timestamp_utc: string;
}

export interface EngineHeartbeat extends BaseEvent {
  event_type: "engine.heartbeat";
  uptime_ms: number;
  health: EngineHealth;
  active_jobs: number;
  queue_depth: number;
}

export interface JobStateChanged extends BaseEvent {
  event_type: "job.state_changed";
  job_id: string;
  old_state?: JobState;
  new_state: JobState;
}

export interface JobProgress extends BaseEvent {
  event_type: "job.progress";
  job_id: string;
  job_sequence: number;
  phase: string;
  progress_percent?: number;
  items_completed?: number;
  items_total?: number;
  eta_seconds?: number;
}

export interface JobLog extends BaseEvent {
  event_type: "job.log";
  job_id: string;
  job_sequence: number;
  level: LogLevel;
  subsystem: string;
  message: string;
  payload?: Record<string, unknown>;
  correlation_id?: string;
}

export interface ReplayComplete extends BaseEvent {
  event_type: "replay.complete";
  replayed_count: number;
  now_live: boolean;
}

// Union type for all SSE events
export type SSEEvent =
  | EngineHeartbeat
  | JobStateChanged
  | JobProgress
  | JobLog
  | ReplayComplete;

// --- Receipt Models ---

export interface ArtifactInfo {
  path: string;
  size_bytes: number;
  sha256: string;
}

export interface ReceiptTimestamps {
  created: string;
  started?: string;
  completed?: string;
}

export interface JobReceipt {
  schema_version: string;
  job_id: string;
  run_id: string;
  receipt_status: "completed" | "failed" | "cancelled";
  exit_code?: string;
  timestamps: ReceiptTimestamps;
  config_snapshot: Record<string, unknown>;
  source_pins: Record<string, string>;
  outputs: ArtifactInfo[];
  inputs_summary: Record<string, unknown>;
  error_code?: string;
  error_message?: string;
  error_details?: Record<string, unknown>;
}

// --- Diagnostics Models ---

export interface IntegritySummary {
  ok: number;
  warn: number;
  fail: number;
  skipped: number;
}

export interface DiagnosticsReport {
  path: string;
  report: {
    generated_at: string;
    full_integrity_mode: boolean;
    size_threshold_bytes: number;
    summary: IntegritySummary;
    failures: Array<{
      job_id: string;
      path: string;
      expected?: string;
      actual?: string;
      reason: string;
    }>;
  };
}

// --- Error Response ---

export interface ErrorResponse {
  error: string;
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// --- Connection State ---

export type ConnectionState = "connected" | "degraded" | "disconnected";

// --- Sprint 19: SSE Connection Health ---

/** SSE connection health state for the connection badge */
export type SSEHealthState = "connected" | "reconnecting" | "disconnected";

/** SSE health info for diagnostics */
export interface SSEHealthInfo {
  state: SSEHealthState;
  baseUrl: string;
  lastEventId: number | null;
  lastMessageAt: Date | null;
  reconnectAttempt: number;
}

// --- Sprint 19: Job UI State Machine ---

/**
 * Job UI state for ExportView and Jobs screen.
 * Represents the client-side view of a job's lifecycle.
 */
export type JobUIState =
  | { status: "idle" }
  | { status: "enqueued"; jobId: string }
  | {
      status: "streaming";
      jobId: string;
      stage: string;
      percent: number;
      message: string;
    }
  | { status: "cancel_requested"; jobId: string }
  | { status: "completed_success"; jobId: string; result: ScholarlyJobResult }
  | { status: "completed_gate_blocked"; jobId: string; pendingGates: string[] }
  | { status: "completed_failed"; jobId: string; errors: string[] }
  | { status: "canceled"; jobId: string };

// --- API Capabilities (Sprint 16: Compatibility Handshake) ---

export interface ApiCapabilities {
  version: string;
  api_version: string;
  min_gui_version: string;
  endpoints: {
    engine_status: string;
    stream: string;
    jobs: string;
    gates_pending: string;
    run_scholarly: string;
    translate: string;
    acknowledge: string;
    sources: string;
    sources_status: string;
    variants_dossier: string;
  };
  features: string[];
  initialized: boolean;
}

// Sprint 17/19: Error categories for structured error handling
export type ErrorCategory =
  | "network"
  | "auth"
  | "not_found"
  | "backend_mismatch" // Sprint 19: Backend running in wrong mode
  | "gate_blocked"
  | "service_unavailable"
  | "server"
  | "unknown";

/**
 * Sprint 19: Backend mismatch detection result.
 * Used when a 404 is detected for /translate or /sources/status.
 */
export interface BackendMismatchInfo {
  detected: boolean;
  backendMode?: "full" | "engine_only";
  missingRoutes: string[];
  correctStartCommand: string;
}

// Error detail types for ApiErrorPanel
export interface ApiErrorDetail {
  method: string;
  url: string;
  status: number | null;
  statusText: string;
  responseSnippet: string;
  suggestedFix: string;
  timestamp: string;
  // Sprint 17: Enhanced diagnostics
  category: ErrorCategory;
  likelyCause: string;
  suggestions: string[];
  raw?: unknown;
  // Sprint 17: Contract diagnostics for debugging endpoint resolution
  contractDiagnostics?: {
    baseUrl: string;
    hasCapabilities: boolean;
    capabilities?: {
      version: string;
      api_version: string;
      min_gui_version: string;
      features: string[];
      initialized: boolean;
    };
    resolvedEndpoints?: Record<string, string>;
  };
  // Sprint 19: Backend mismatch info (populated async for 404 errors)
  mismatchInfo?: BackendMismatchInfo;
}

// Sprint 17: Capability validation result
export interface CapabilitiesValidation {
  valid: boolean;
  error?: string;
  missingEndpoints?: string[];
  versionMismatch?: {
    required: string;
    current: string;
  };
}

// Sprint 17: GUI version for compatibility checks
export const GUI_VERSION = "0.17.0";

// --- Translation Types (Sprint 5) ---

export type TranslationMode = "readable" | "traceable";
export type TranslatorType = "fake" | "literal" | "fluent" | "traceable";

export interface TranslateRequest {
  reference: string;
  mode: TranslationMode;
  session_id: string;
  translator: TranslatorType;
  options?: Record<string, unknown>;
}

export interface AcknowledgeRequest {
  session_id: string;
  variant_ref: string;
  reading_index: number;
}

export interface AcknowledgeResponse {
  success: boolean;
  session_id: string;
  variant_ref: string;
  reading_index: number;
}

export interface GateOption {
  id: string;
  label: string;
  description: string;
  is_default: boolean;
  reading_index?: number;
}

export interface AlternateReading {
  index: number;
  surface_text: string;
  witnesses: string;
  has_papyri: boolean;
  has_primary_uncials: boolean;
}

export interface VariantDisplay {
  ref: string;
  position: number;
  sblgnt_reading: string;
  sblgnt_witnesses: string;
  alternate_readings: AlternateReading[];
  significance: string;
  requires_acknowledgement: boolean;
  acknowledged: boolean;
}

export interface RequiredAck {
  verse_id: string;
  variant_ref: string;
  reading_index: number | null;
  significance: string;
  message: string;
  // Sprint 7: Reason classification (B4)
  reason?: string;
  reason_detail?: string | null;
}

// Sprint 7: Multi-ack support (B3)
export interface AckItem {
  variant_ref: string;
  reading_index: number;
}

export interface AcknowledgeMultiRequest {
  session_id: string;
  variant_ref?: string;
  reading_index?: number;
  acks?: AckItem[];
  scope?: "verse" | "passage" | "book";
}

export interface AcknowledgeMultiResponse {
  success: boolean;
  session_id: string;
  acknowledged: string[];
  count: number;
  scope: string;
  errors: string[];
}

export interface GateResponse {
  response_type: "gate";
  gate_id: string;
  gate_type: string;
  title: string;
  message: string;
  prompt: string;
  options: GateOption[];
  required_dependencies: string[];
  variants_side_by_side: VariantDisplay[];
  escalation_target_mode: string | null;
  reference: string;
  required_acks: RequiredAck[];
  verse_ids: string[];
  session_id: string;
}

export interface DependencyInfo {
  dep_type: string;
  ref: string;
  choice: string;
  rationale: string;
  alternatives: string[];
}

export interface ClaimResult {
  content: string;
  claim_type: number;
  claim_type_label: string;
  classification_confidence: number;
  signals: string[];
  enforcement_allowed: boolean;
  enforcement_reason: string;
  warnings: string[];
  rewrite_suggestions: string[];
  dependencies: DependencyInfo[];
  hypothesis_markers_required: boolean;
}

export interface LayerScore {
  score: number;
  rationale: string;
}

export interface ConfidenceResult {
  composite: number;
  weakest_layer: string;
  layers: {
    textual: LayerScore;
    grammatical: LayerScore;
    lexical: LayerScore;
    interpretive: LayerScore;
  };
  weights: Record<string, number>;
  explanations: string[];
  improvement_suggestions: string[];
}

export interface ProvenanceInfo {
  spine_source: string;
  spine_marker: string;
  sources_used: string[];
  variant_unit_ids: string[];
  witness_summaries: Array<{ ref: string; reading_count: number }>;
}

export interface ReceiptSummary {
  checks_run: string[];
  gates_satisfied: string[];
  gates_pending: string[];
  enforcement_results: Array<{
    claim_preview: string;
    allowed: boolean;
    type: string;
  }>;
  timestamp: string;
}

export interface VerseBlock {
  verse_id: string;
  sblgnt_text: string;
  translation_text: string;
  variants: VariantDisplay[];
  tokens: Record<string, unknown>[];
  confidence: ConfidenceResult | null;
}

export interface TranslateResponse {
  response_type: "translation";
  reference: string;
  normalized_ref: string;
  verse_ids: string[];
  mode: TranslationMode;
  sblgnt_text: string;
  translation_text: string;
  verse_blocks: VerseBlock[];
  variants: VariantDisplay[];
  claims: ClaimResult[];
  confidence: ConfidenceResult | null;
  provenance: ProvenanceInfo;
  receipts: ReceiptSummary;
  tokens: Record<string, unknown>[];
  session_id: string;
  translator_type: TranslatorType;
  // Sprint 10: Traceable ledger (token-level evidence)
  ledger: VerseLedger[] | null;
}

export type TranslateResult = TranslateResponse | GateResponse;

export function isGateResponse(
  result: TranslateResult,
): result is GateResponse {
  return result.response_type === "gate";
}

export function isTranslateResponse(
  result: TranslateResult,
): result is TranslateResponse {
  return result.response_type === "translation";
}

// --- Source Management Types (Sprint 6) ---

export type SourceRole =
  | "canonical_spine"
  | "lexicon_primary"
  | "lexicon_secondary"
  | "lexicon_semantic_domains"
  | "comparative_layer"
  | "witness_anchor"
  | "variant_collation";

export interface SourceStatus {
  source_id: string;
  name: string;
  role: SourceRole;
  license: string;
  requires_eula: boolean;
  installed: boolean;
  install_path: string | null;
  installed_at: string | null;
  version: string | null;
  eula_accepted: boolean | null;
}

export interface SourcesListResponse {
  data_root: string;
  sources: SourceStatus[];
}

export interface SourcesStatusResponse {
  data_root: string;
  manifest_path: string;
  spine_installed: boolean;
  spine_source_id: string | null;
  sources: Record<string, SourceStatus>;
}

export interface InstallSourceRequest {
  source_id: string;
  accept_eula?: boolean;
}

export interface InstallSourceResponse {
  success: boolean;
  source_id: string;
  message: string;
  install_path: string | null;
  eula_required: boolean;
  error: string | null;
}

export interface UninstallSourceRequest {
  source_id: string;
}

export interface UninstallSourceResponse {
  success: boolean;
  source_id: string;
  message: string;
  error: string | null;
}

export interface LicenseInfoResponse {
  source_id: string;
  name: string;
  license: string;
  license_url: string | null;
  requires_eula: boolean;
  eula_summary: string | null;
  notes: string | null;
}

// --- Sprint 8: Dossier Types (B4/B5) ---

export interface DossierWitnessInfo {
  siglum: string;
  type: string;
  century: number | null;
}

export interface DossierWitnessSummary {
  editions: string[];
  papyri: string[];
  uncials: string[];
  minuscules: string[];
  versions: string[];
  fathers: string[];
}

export interface DossierReading {
  index: number;
  text: string;
  is_spine: boolean;
  witnesses: DossierWitnessInfo[];
  witness_summary: DossierWitnessSummary;
  source_packs: string[];
}

export interface DossierReason {
  code: string;
  summary: string;
  detail: string | null;
}

export interface DossierAcknowledgement {
  required: boolean;
  acknowledged: boolean;
  acknowledged_reading: number | null;
  session_id: string | null;
}

export interface DossierVariant {
  ref: string;
  position: number;
  classification: string;
  significance: string;
  gating_requirement: string;
  reason: DossierReason;
  readings: DossierReading[];
  acknowledgement: DossierAcknowledgement;
}

export interface DossierSpine {
  source_id: string;
  text: string;
  is_default: boolean;
}

export interface DossierProvenance {
  spine_source: string;
  comparative_packs: string[];
  build_timestamp: string;
}

export interface DossierResponse {
  reference: string;
  scope: string;
  generated_at: string;
  spine: DossierSpine;
  variants: DossierVariant[];
  provenance: DossierProvenance;
  witness_density_note: string | null;
}

export type DossierScope = "verse" | "passage" | "chapter" | "book";

// --- Sprint 10: Traceable Ledger Types ---

export interface TokenConfidence {
  textual: number;
  grammatical: number;
  lexical: number;
  interpretive: number;
  explanations: Record<string, string>;
}

export interface TokenLedger {
  position: number;
  surface: string;
  normalized: string;
  lemma: string | null;
  morph: string | null;
  gloss: string;
  gloss_source: string;
  notes: string[];
  confidence: TokenConfidence;
}

export interface SegmentLedger {
  token_range: [number, number];
  greek_phrase: string;
  english_phrase: string;
  alignment_type: string;
  transformation_notes: string[];
}

export interface EvidenceClassSummary {
  manuscript_count: number;
  edition_count: number;
  tradition_count: number;
  other_count: number;
}

export interface LedgerProvenance {
  spine_source_id: string;
  comparative_sources_used: string[];
  evidence_class_summary: EvidenceClassSummary;
}

export interface VerseLedger {
  verse_id: string;
  normalized_ref: string;
  tokens: TokenLedger[];
  translation_segments: SegmentLedger[];
  provenance: LedgerProvenance;
}

// --- Sprint 15: Gate Pending Check Types ---

export interface PendingGateInfo {
  ref: string;
  significance: string;
  message: string;
  reason?: string;
  reason_detail?: string | null;
}

export interface PendingGatesResponse {
  reference: string;
  session_id: string;
  pending_gates: PendingGateInfo[];
  total_variants: number;
}

// --- Sprint 14: Scholarly Run Types ---

export interface ScholarlyRunRequest {
  reference: string;
  mode?: "readable" | "traceable";
  force?: boolean;
  session_id?: string;
  include_schemas?: boolean;
  create_zip?: boolean;
}

export interface ScholarlyRunFile {
  path: string;
  artifact_type: string;
  sha256: string;
  schema_version?: string;
}

export interface ScholarlyRunValidation {
  check: string;
  passed: boolean;
  errors?: string[];
  warnings?: string[];
}

export interface ScholarlyRunGates {
  pending_count: number;
  pending_refs: string[];
  forced?: boolean;
  forced_responsibility?: string;
}

export interface ScholarlyRunLog {
  schema_version: string;
  tool_version: string;
  started_at: string;
  completed_at: string;
  reference: string;
  mode: string;
  verse_ids: string[];
  files_created: ScholarlyRunFile[];
  validations: ScholarlyRunValidation[];
  gates?: ScholarlyRunGates;
  success: boolean;
  errors?: string[];
  content_hash?: string;
}

export interface ScholarlyRunResponse {
  success: boolean;
  gate_blocked: boolean;
  pending_gates: string[];
  message: string;
  reference: string;
  mode: string;
  output_dir?: string;
  bundle_path?: string;
  run_log?: ScholarlyRunLog;
  errors: string[];
}

// --- Sprint 18: Async Scholarly Jobs ---

/** Response for POST /v1/run/scholarly (async job mode) */
export interface ScholarlyJobResponse {
  success: boolean;
  job_id: string;
  reference: string;
  mode: string;
  force: boolean;
  session_id: string;
  message: string;
}

/** Result payload stored in job receipt for scholarly jobs */
export interface ScholarlyJobResult {
  success: boolean;
  gate_blocked?: boolean;
  pending_gates?: string[];
  output_dir?: string;
  bundle_path?: string;
  run_log_summary?: {
    reference: string;
    mode: string;
    verse_count: number;
    file_count: number;
    content_hash?: string;
  };
  errors?: string[];
  started_at?: string;
  completed_at?: string;
}

/** Extended job config for scholarly jobs */
export interface ScholarlyJobConfig extends JobConfig {
  job_type: "scholarly";
  reference: string;
  mode: "readable" | "traceable";
  force: boolean;
  session_id: string;
  include_schemas: boolean;
  create_zip: boolean;
}
