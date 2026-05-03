import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ProvenanceTimeline from '@/components/ProvenanceTimeline.vue'
import type { SourceProvenance } from '@/api/types'

const sampleEntries: SourceProvenance[] = [
  {
    type: 'pdf',
    url: 'https://expo.com/list.pdf',
    pdf_filename: 'list.pdf',
    pdf_sha256: 'abc123def4567890',
    page: 7,
    position: 3,
    extraction_method: 'surya_ocr',
    confidence: 0.92,
    context_snippet: 'Hall B Stand 24',
    discovered_at: '2026-05-04T10:30:00Z',
  },
  {
    type: 'search',
    url: 'https://duckduckgo.com/?q=test',
    extraction_method: 'name_resolver_llm_tiebreak',
    discovered_at: '2026-05-04T10:31:15Z',
  },
]

describe('ProvenanceTimeline', () => {
  it('renders one item per entry', () => {
    const wrapper = mount(ProvenanceTimeline, { props: { entries: sampleEntries } })
    expect(wrapper.findAll('li')).toHaveLength(2)
  })

  it('shows pdf page and position badges', () => {
    const wrapper = mount(ProvenanceTimeline, { props: { entries: sampleEntries } })
    expect(wrapper.text()).toContain('Halaman 7')
    expect(wrapper.text()).toContain('Posisi 3')
  })

  it('shows confidence percentage', () => {
    const wrapper = mount(ProvenanceTimeline, { props: { entries: sampleEntries } })
    expect(wrapper.text()).toContain('92%')
  })

  it('shows extraction method', () => {
    const wrapper = mount(ProvenanceTimeline, { props: { entries: sampleEntries } })
    expect(wrapper.text()).toContain('surya_ocr')
    expect(wrapper.text()).toContain('name_resolver_llm_tiebreak')
  })

  it('shows pdf filename', () => {
    const wrapper = mount(ProvenanceTimeline, { props: { entries: sampleEntries } })
    expect(wrapper.text()).toContain('list.pdf')
  })

  it('renders empty when no entries', () => {
    const wrapper = mount(ProvenanceTimeline, { props: { entries: [] } })
    expect(wrapper.findAll('li')).toHaveLength(0)
  })
})
