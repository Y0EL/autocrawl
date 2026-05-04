export type ProvenanceType = 'aggregator' | 'pdf' | 'search' | 'manual'

export interface SourceProvenance {
  type: ProvenanceType
  url?: string | null
  pdf_filename?: string | null
  pdf_sha256?: string | null
  page?: number | null
  position?: number | null
  extraction_method?: string | null
  confidence?: number | null
  context_snippet?: string | null
  discovered_at: string
}

export interface ContactPoint {
  type: 'email' | 'phone' | 'fax' | 'form' | 'other'
  value: string
  label?: string | null
  verified?: boolean | null
  verification_score?: number | null
  verification_signals?: Record<string, unknown> | null
}

export interface Address {
  street?: string | null
  city?: string | null
  region?: string | null
  country?: string | null
  postal_code?: string | null
  raw?: string | null
}

export interface SocialLinks {
  linkedin?: string | null
  twitter?: string | null
  facebook?: string | null
  youtube?: string | null
  instagram?: string | null
  github?: string | null
  other?: string[]
}

export interface FundingInfo {
  total_raised_usd?: number | null
  last_round?: string | null
  last_round_at?: string | null
  investors?: string[]
}

export type VendorStatus =
  | 'enriched'
  | 'unresolved'
  | 'enrich_failed'
  | 'scope_rejected'
  | 'validation_rejected'

export interface Vendor {
  vendor_id: string
  status: VendorStatus
  domain: string | null
  company_name: string
  canonical_url: string | null
  description?: string | null
  tagline?: string | null
  products: string[]
  industries: string[]
  expos_seen: string[]
  address?: Address | null
  contacts: ContactPoint[]
  socials: SocialLinks
  funding: FundingInfo
  employee_count?: number | null
  founded_year?: number | null
  domain_age_days?: number | null
  registrar?: string | null
  registrar_country?: string | null
  first_seen_wayback?: string | null
  logo_url?: string | null
  tech_stack: string[]
  confidence_score: number
  enrichment_gap: string[]
  source_trail: SourceProvenance[]
  source_tags: string[]
  first_enriched_at: string
  last_enriched_at: string
  language_code?: 'en' | 'id'
  description_original?: string | null
  tagline_original?: string | null
  products_original?: string[]
  industries_original?: string[]
  translation_method?: string | null
  translated_at?: string | null
}

export interface Expo {
  expo_id: string
  name: string
  source: string
  aggregator_url?: string | null
  official_url?: string | null
  location?: string | null
  country?: string | null
  start_date?: string | null
  end_date?: string | null
  topics: string[]
  discovered_at: string
  discovery_query?: string | null
  pdf_brochure_urls: string[]
  vendor_domains: string[]
}

export interface PdfMeta {
  filename: string
  source_url: string
  expo_id: string
  sha256: string
  size_bytes: number
  downloaded_at: string
  page_count: number
  vendors_found: number
}

export interface RunSummary {
  run_id: string
  started_at: string
  finished_at?: string | null
  mode: 'dev' | 'normal' | 'aggressive'
  expos_discovered: number
  exhibitors_extracted: number
  vendors_resolved: number
  vendors_enriched: number
  vendors_dedup_skipped: number
  failures: number
  firecrawl_credits_used?: number
  openai_tokens_used?: number
  notes?: string | null
  exhibitors_resolve_failed?: number
  exhibitors_enrich_failed?: number
  exhibitors_validation_rejected?: number
  exhibitors_scope_rejected?: number
}

export interface ExhibitorRefRow {
  ref_id: string
  expo_id: string | null
  name: string
  raw_url: string | null
  short_description: string | null
  booth: string | null
  status: string
  failure_category: string | null
  failure_reason: string | null
  resolved_domain: string | null
  resolve_attempts: number
  last_attempted_at: string | null
  run_id: string | null
  created_at: string
  updated_at: string
}

export interface RefsStats {
  total: number
  by_status: Record<string, number>
  by_failure_category: Record<string, number>
}

export interface OverviewResponse {
  vendors_total: number
  expos_total: number
  pdfs_total: number
  phase_2_threshold: number
  phase_2_progress_ratio: number
  latest_run: RunSummary | null
  industry_breakdown: { tag: string; count: number }[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface IndustryStat {
  tag: string
  count: number
}

export interface CountryStat {
  country: string
  count: number
}

export interface ExpoCountryStat {
  country: string
  expo_count: number
  vendor_count: number
}

export interface SourceTypeStat {
  type: string
  count: number
}

export interface TimelinePoint {
  date: string
  vendors_added: number
}

export interface RunModeStat {
  mode: string
  count: number
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  db: 'ok' | 'down'
  version: string
  uptime_seconds?: number
  error?: string
}

export interface SettingsResponse {
  llm_provider: string
  llm_base_url: string | null
  openai_model_heavy: string
  openai_model_light: string
  translation_enabled: boolean
  translation_provider: string
  target_language: string
  phase_2_vendor_threshold: number
  max_vendors_per_run: number
  max_expos_per_run: number
  run_interval_minutes: number
  pdf_discovery_enabled: boolean
  ocr_enabled: boolean
  mode: string
  log_level: string
}

export interface OrchestratorNode {
  id: string
  label: string
  code: string
  description: string
  x: number
  y: number
  active: number
  started: number
  completed: number
  failed: number
  last_event_at: number | null
}

export interface OrchestratorEdge {
  id: string
  source: string
  target: string
}

export interface OrchestratorState {
  nodes: OrchestratorNode[]
  edges: OrchestratorEdge[]
  last_event_id: string
  events_observed: number
}

export interface CrawlEvent {
  id: string
  ts: number
  node: string
  event: 'started' | 'completed' | 'failed' | string
  run_id: string
  payload: Record<string, unknown>
}

export interface OrchestratorEventsResponse {
  events: CrawlEvent[]
  next_since: string
}

export interface OrchestratorActiveRun {
  started_at: string
  mode: string
  status: string
  duration_seconds?: number
}

export interface OrchestratorStageState {
  node: string
  code: string
  label: string
  active: number
  completed_today: number
  failed_today: number
  in_flight_label: string | null
  last_event_at: number | null
}

export interface OrchestratorCurrent {
  active_run: OrchestratorActiveRun | null
  stages: OrchestratorStageState[]
}

export interface OrchestratorThroughput {
  window_seconds: number
  effective_window_seconds: number
  fallback_used: boolean
  last_event_at: number | null
  now: number
  events_total: number
  events_per_minute: number
  vendors_per_minute: number
  errors_per_minute: number
  active_workers_total: number
  by_node: Record<string, number>
}

export interface ErrorGroupSample {
  ref_id: string
  name: string
  expo_id: string | null
  failure_reason: string
  resolve_attempts: number
}

export interface ErrorGroup {
  category: string
  title: string
  count: number
  cause: string
  remedy: string
  samples: ErrorGroupSample[]
}

export interface ErrorSummaryResponse {
  groups: ErrorGroup[]
  total: number
}

export type ScopeRuleKind =
  | 'blacklist_domain'
  | 'whitelist_domain'
  | 'scope_keyword_include'
  | 'scope_keyword_exclude'
  | 'seed_topic'
  | 'anchor_expo'

export type ScopeRuleSource = 'yaml_default' | 'user' | 'ai_suggested'

export interface ScopeRule {
  id: string
  kind: ScopeRuleKind
  value: string
  source: ScopeRuleSource
  enabled: boolean
  notes: string | null
  extra: Record<string, unknown>
  created_at: string | null
  updated_at: string | null
}

export interface ScopeRulesResponse {
  items: ScopeRule[]
  total: number
  valid_kinds: ScopeRuleKind[]
}

export interface ScopePromptResponse {
  key: string
  content: string
  is_custom: boolean
  updated_at: string | null
}

export interface ScopeSuggestion {
  value: string
  reason: string
  confidence: number
}

export interface ScopeSuggestResponse {
  kind: ScopeRuleKind
  hint: string
  suggestions: ScopeSuggestion[]
}
