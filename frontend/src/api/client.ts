import axios from 'axios'
import type {
  CountryStat,
  ErrorSummaryResponse,
  ExhibitorRefRow,
  Expo,
  HealthResponse,
  IndustryStat,
  OrchestratorCurrent,
  OrchestratorEventsResponse,
  OrchestratorState,
  OrchestratorThroughput,
  OverviewResponse,
  PaginatedResponse,
  PdfMeta,
  RefsStats,
  RunModeStat,
  RunSummary,
  ScopePromptResponse,
  ScopeRule,
  ScopeRuleKind,
  ScopeRulesResponse,
  ScopeSuggestResponse,
  SettingsResponse,
  SourceTypeStat,
  TimelinePoint,
  Vendor,
} from './types'

const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

export interface VendorsQuery {
  industry?: string
  country?: string
  search?: string
  status?: string
  limit?: number
  offset?: number
  sort?: string
}

export interface RefsQuery {
  status?: string
  failure_category?: string
  expo_id?: string
  limit?: number
  offset?: number
}

export interface ExposQuery {
  country?: string
  search?: string
  limit?: number
  offset?: number
}

export const api = {
  overview: () => http.get<OverviewResponse>('/overview').then((r) => r.data),
  vendors: (q: VendorsQuery = {}) =>
    http.get<PaginatedResponse<Vendor>>('/vendors', { params: q }).then((r) => r.data),
  vendor: (domain: string) => http.get<Vendor>(`/vendors/${domain}`).then((r) => r.data),
  deepenVendor: (vendorId: string) =>
    http.post<{ status: string; vendor_id: string; domain: string | null; current_status: string; current_score: number }>(
      `/vendors/${vendorId}/deepen`,
    ).then((r) => r.data),
  expos: (q: ExposQuery = {}) =>
    http.get<PaginatedResponse<Expo>>('/expos', { params: q }).then((r) => r.data),
  expo: (expoId: string) => http.get<Expo>(`/expos/${expoId}`).then((r) => r.data),
  deepenExpo: (expoId: string) =>
    http.post<{ status: string; expo_id: string; name: string | null }>(
      `/expos/${expoId}/deepen`,
    ).then((r) => r.data),
  pdfs: (expoId?: string) =>
    http
      .get<PaginatedResponse<PdfMeta>>('/pdfs', { params: expoId ? { expo_id: expoId } : {} })
      .then((r) => r.data),
  runs: (limit = 20) =>
    http.get<PaginatedResponse<RunSummary>>('/runs', { params: { limit } }).then((r) => r.data),
  stats: {
    industries: () => http.get<IndustryStat[]>('/stats/industries').then((r) => r.data),
    countries: (limit = 10) =>
      http.get<CountryStat[]>('/stats/countries', { params: { limit } }).then((r) => r.data),
    sourceTypes: () => http.get<SourceTypeStat[]>('/stats/source-types').then((r) => r.data),
    timeline: (days = 30) =>
      http.get<TimelinePoint[]>('/stats/timeline', { params: { days } }).then((r) => r.data),
    runsMode: (days = 30) =>
      http.get<RunModeStat[]>('/stats/runs-mode', { params: { days } }).then((r) => r.data),
  },
  health: () => http.get<HealthResponse>('/health').then((r) => r.data),
  settings: () => http.get<SettingsResponse>('/settings').then((r) => r.data),
  orchestrator: {
    state: () => http.get<OrchestratorState>('/orchestrator/state').then((r) => r.data),
    events: (since = '0', limit = 50) =>
      http
        .get<OrchestratorEventsResponse>('/orchestrator/events', { params: { since, limit } })
        .then((r) => r.data),
    current: () =>
      http.get<OrchestratorCurrent>('/orchestrator/current').then((r) => r.data),
    throughput: (windowSeconds = 60) =>
      http
        .get<OrchestratorThroughput>('/orchestrator/throughput', {
          params: { window_seconds: windowSeconds },
        })
        .then((r) => r.data),
    errorSummary: (samplesPerGroup = 5) =>
      http
        .get<ErrorSummaryResponse>('/orchestrator/error-summary', {
          params: { samples_per_group: samplesPerGroup },
        })
        .then((r) => r.data),
  },
  exhibitorRefs: {
    stats: () => http.get<RefsStats>('/exhibitor-refs/stats').then((r) => r.data),
    list: (q: RefsQuery = {}) =>
      http
        .get<PaginatedResponse<ExhibitorRefRow>>('/exhibitor-refs', { params: q })
        .then((r) => r.data),
    retry: (refId: string) =>
      http.post(`/exhibitor-refs/${refId}/retry-resolve`).then((r) => r.data),
  },
  triggerRun: (mode: 'dev' | 'normal' | 'aggressive' = 'normal') =>
    http.post('/runs/trigger', { mode }).then((r) => r.data),
  activeRun: () =>
    http
      .get<{ active: Record<string, unknown> | null }>('/runs/active')
      .then((r) => r.data),
  config: {
    listScopeRules: (params: { kind?: ScopeRuleKind; source?: string; enabled?: boolean } = {}) =>
      http
        .get<ScopeRulesResponse>('/config/scope', { params })
        .then((r) => r.data),
    createScopeRule: (body: {
      kind: ScopeRuleKind
      value: string
      source?: 'user' | 'ai_suggested'
      enabled?: boolean
      notes?: string | null
      extra?: Record<string, unknown> | null
    }) =>
      http
        .post<ScopeRule>('/config/scope', body)
        .then((r) => r.data),
    updateScopeRule: (id: string, body: { enabled?: boolean; notes?: string | null }) =>
      http.patch<ScopeRule>(`/config/scope/${id}`, body).then((r) => r.data),
    deleteScopeRule: (id: string) =>
      http.delete<void>(`/config/scope/${id}`).then((r) => r.data),
    getScopePrompt: () =>
      http.get<ScopePromptResponse>('/config/scope/prompt').then((r) => r.data),
    setScopePrompt: (content: string) =>
      http.put<ScopePromptResponse>('/config/scope/prompt', { content }).then((r) => r.data),
    resetScopePrompt: () =>
      http.delete<void>('/config/scope/prompt').then((r) => r.data),
    suggestScopeRules: (body: {
      kind: ScopeRuleKind
      hint: string
      max_suggestions?: number
    }) =>
      http
        .post<ScopeSuggestResponse>('/config/scope/suggest', body)
        .then((r) => r.data),
  },
}
