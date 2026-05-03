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

export interface Vendor {
  domain: string
  company_name: string
  canonical_url: string
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
