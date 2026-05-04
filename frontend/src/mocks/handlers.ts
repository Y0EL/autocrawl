import { http, HttpResponse, delay } from 'msw'
import type { OverviewResponse, PaginatedResponse } from '@/api/types'
import { vendors } from './data/vendors'
import { expos } from './data/expos'
import { pdfs } from './data/pdfs'
import { runs } from './data/runs'

const SIM_LATENCY_MS = 120

function paginate<T>(items: T[], limit: number, offset: number): PaginatedResponse<T> {
  return {
    items: items.slice(offset, offset + limit),
    total: items.length,
    limit,
    offset,
  }
}

function buildOverview(): OverviewResponse {
  const industryCounts: Record<string, number> = {}
  for (const v of vendors) {
    for (const tag of v.industries) {
      industryCounts[tag] = (industryCounts[tag] ?? 0) + 1
    }
  }
  const breakdown = Object.entries(industryCounts)
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count)

  const phase2Threshold = 100
  const enriched = vendors.length
  return {
    vendors_total: enriched,
    expos_total: expos.length,
    pdfs_total: pdfs.length,
    phase_2_threshold: phase2Threshold,
    phase_2_progress_ratio: enriched / phase2Threshold,
    latest_run: runs[0] ?? null,
    industry_breakdown: breakdown,
  }
}

export const handlers = [
  http.get('/api/overview', async () => {
    await delay(SIM_LATENCY_MS)
    return HttpResponse.json(buildOverview())
  }),

  http.get('/api/vendors', async ({ request }) => {
    await delay(SIM_LATENCY_MS)
    const url = new URL(request.url)
    const search = (url.searchParams.get('search') ?? '').toLowerCase()
    const industry = url.searchParams.get('industry') ?? ''
    const country = url.searchParams.get('country') ?? ''
    const limit = Number(url.searchParams.get('limit') ?? 20)
    const offset = Number(url.searchParams.get('offset') ?? 0)

    let filtered = vendors
    if (search) {
      filtered = filtered.filter(
        (v) =>
          (v.domain ?? '').toLowerCase().includes(search) ||
          v.company_name.toLowerCase().includes(search),
      )
    }
    if (industry) {
      filtered = filtered.filter((v) => v.industries.includes(industry))
    }
    if (country) {
      filtered = filtered.filter((v) => v.address?.country === country)
    }
    return HttpResponse.json(paginate(filtered, limit, offset))
  }),

  http.get('/api/vendors/:domain', async ({ params }) => {
    await delay(SIM_LATENCY_MS)
    const found = vendors.find((v) => v.domain === params.domain)
    if (!found) return HttpResponse.json({ message: 'Not found' }, { status: 404 })
    return HttpResponse.json(found)
  }),

  http.get('/api/expos', async ({ request }) => {
    await delay(SIM_LATENCY_MS)
    const url = new URL(request.url)
    const search = (url.searchParams.get('search') ?? '').toLowerCase()
    const country = url.searchParams.get('country') ?? ''
    const limit = Number(url.searchParams.get('limit') ?? 20)
    const offset = Number(url.searchParams.get('offset') ?? 0)

    let filtered = expos
    if (search) {
      filtered = filtered.filter((e) => e.name.toLowerCase().includes(search))
    }
    if (country) {
      filtered = filtered.filter((e) => e.country === country)
    }
    return HttpResponse.json(paginate(filtered, limit, offset))
  }),

  http.get('/api/expos/:expoId', async ({ params }) => {
    await delay(SIM_LATENCY_MS)
    const found = expos.find((e) => e.expo_id === params.expoId)
    if (!found) return HttpResponse.json({ message: 'Not found' }, { status: 404 })
    return HttpResponse.json(found)
  }),

  http.get('/api/pdfs', async ({ request }) => {
    await delay(SIM_LATENCY_MS)
    const url = new URL(request.url)
    const expoId = url.searchParams.get('expo_id')
    let filtered = pdfs
    if (expoId) filtered = filtered.filter((p) => p.expo_id === expoId)
    return HttpResponse.json(paginate(filtered, 100, 0))
  }),

  http.get('/api/runs', async ({ request }) => {
    await delay(SIM_LATENCY_MS)
    const limit = Number(new URL(request.url).searchParams.get('limit') ?? 20)
    return HttpResponse.json(paginate(runs, limit, 0))
  }),
]
