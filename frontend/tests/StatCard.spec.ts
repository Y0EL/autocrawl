import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import StatCard from '@/components/StatCard.vue'

describe('StatCard', () => {
  it('renders label and value', () => {
    const wrapper = mount(StatCard, { props: { label: 'Vendor Total', value: 42 } })
    expect(wrapper.text()).toContain('Vendor Total')
    expect(wrapper.text()).toContain('42')
  })

  it('renders hint when provided', () => {
    const wrapper = mount(StatCard, {
      props: { label: 'X', value: 1, hint: 'Target 100' },
    })
    expect(wrapper.text()).toContain('Target 100')
  })

  it('shows up arrow on up trend', () => {
    const wrapper = mount(StatCard, {
      props: { label: 'X', value: 1, trend: 'up' },
    })
    expect(wrapper.html()).toContain('fa-arrow-trend-up')
  })

  it('shows down arrow on down trend', () => {
    const wrapper = mount(StatCard, {
      props: { label: 'X', value: 1, trend: 'down' },
    })
    expect(wrapper.html()).toContain('fa-arrow-trend-down')
  })

  it('renders icon when provided', () => {
    const wrapper = mount(StatCard, {
      props: { label: 'X', value: 1, icon: 'fa-solid fa-building' },
    })
    expect(wrapper.html()).toContain('fa-solid fa-building')
  })
})
