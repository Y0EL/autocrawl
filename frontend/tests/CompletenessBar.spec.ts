import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import CompletenessBar from '@/components/CompletenessBar.vue'

describe('CompletenessBar', () => {
  it('renders 0% when score is 0', () => {
    const wrapper = mount(CompletenessBar, { props: { score: 0, showLabel: true } })
    expect(wrapper.text()).toContain('0%')
  })

  it('renders 100% when score is 1', () => {
    const wrapper = mount(CompletenessBar, { props: { score: 1, showLabel: true } })
    expect(wrapper.text()).toContain('100%')
  })

  it('clamps over 1', () => {
    const wrapper = mount(CompletenessBar, { props: { score: 1.5, showLabel: true } })
    expect(wrapper.text()).toContain('100%')
  })

  it('clamps below 0', () => {
    const wrapper = mount(CompletenessBar, { props: { score: -0.2, showLabel: true } })
    expect(wrapper.text()).toContain('0%')
  })

  it('uses emerald colour for high score', () => {
    const wrapper = mount(CompletenessBar, { props: { score: 0.85 } })
    expect(wrapper.html()).toContain('bg-emerald-500')
  })

  it('uses rose colour for very low score', () => {
    const wrapper = mount(CompletenessBar, { props: { score: 0.1 } })
    expect(wrapper.html()).toContain('bg-rose-500')
  })

  it('hides label when showLabel is false', () => {
    const wrapper = mount(CompletenessBar, { props: { score: 0.5, showLabel: false } })
    expect(wrapper.text()).not.toContain('50%')
  })
})
