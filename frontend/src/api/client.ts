import axios from 'axios'
import type {
  CountryStat,
  Expo,
  IndustryStat,
  OverviewResponse,
  PaginatedResponse,
  PdfMeta,
  RunModeStat,
  RunSummary,
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
  limit?: number
  offset?: number
  sort?: string
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
  expos: (q: ExposQuery = {}) =>
    http.get<PaginatedResponse<Expo>>('/expos', { params: q }).then((r) => r.data),
  expo: (expoId: string) => http.get<Expo>(`/expos/${expoId}`).then((r) => r.data),
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
  health: () => http.get('/health').then((r) => r.data),
  triggerRun: (mode: 'dev' | 'normal' | 'aggressive' = 'normal') =>
    http.post('/runs/trigger', { mode }).then((r) => r.data),
  activeRun: () => http.get<{ active: Record<string, unknown> | null }>('/runs/active').then((r) => r.data),
}
