import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import IndustryBadge from '@/components/IndustryBadge.vue'

describe('IndustryBadge', () => {
  it('renders defense palette', () => {
    const wrapper = mount(IndustryBadge, { props: { tag: 'defense' } })
    expect(wrapper.html()).toContain('rose')
    expect(wrapper.text()).toBe('defense')
  })

  it('renders cybersecurity palette', () => {
    const wrapper = mount(IndustryBadge, { props: { tag: 'cybersecurity' } })
    expect(wrapper.html()).toContain('violet')
  })

  it('falls back to neutral for unknown tag', () => {
    const wrapper = mount(IndustryBadge, { props: { tag: 'unknown_industry' } })
    expect(wrapper.html()).toContain('zinc')
    expect(wrapper.text()).toBe('unknown_industry')
  })
})
