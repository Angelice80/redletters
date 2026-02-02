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

export type EngineMode = "normal" | "safe";

export type EngineHealth = "healthy" | "degraded";

export type LogLevel = "trace" | "debug" | "info" | "warn" | "error";

// --- Request/Response Models ---

export interface JobConfig {
  input_paths: string[];
  output_dir?: string;
  style: string;
  options: Record<string, unknown>;
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

// --- Translation Types (Sprint 5) ---

export type TranslationMode = "readable" | "traceable";
export type TranslatorType = "fake" | "literal" | "fluent";

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
