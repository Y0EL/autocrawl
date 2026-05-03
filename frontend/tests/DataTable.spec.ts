import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import DataTable from '@/components/DataTable.vue'

interface Row {
  id: number
  name: string
  qty: number
}

const items: Row[] = [
  { id: 1, name: 'Alpha', qty: 10 },
  { id: 2, name: 'Bravo', qty: 5 },
  { id: 3, name: 'Charlie', qty: 8 },
]

const columns = [
  { key: 'name', label: 'Nama' },
  { key: 'qty', label: 'Jumlah', align: 'right' as const },
]

describe('DataTable', () => {
  it('renders header labels', () => {
    const wrapper = mount(DataTable<Row>, {
      props: { items, columns, rowKey: 'id' },
    })
    expect(wrapper.text()).toContain('Nama')
    expect(wrapper.text()).toContain('Jumlah')
  })

  it('renders all rows', () => {
    const wrapper = mount(DataTable<Row>, {
      props: { items, columns, rowKey: 'id' },
    })
    expect(wrapper.text()).toContain('Alpha')
    expect(wrapper.text()).toContain('Bravo')
    expect(wrapper.text()).toContain('Charlie')
  })

  it('shows loading state', () => {
    const wrapper = mount(DataTable<Row>, {
      props: { items: [], columns, rowKey: 'id', loading: true },
    })
    expect(wrapper.text()).toContain('Memuat data')
  })

  it('shows empty state', () => {
    const wrapper = mount(DataTable<Row>, {
      props: { items: [], columns, rowKey: 'id', emptyLabel: 'Tidak ada data' },
    })
    expect(wrapper.text()).toContain('Tidak ada data')
  })

  it('paginates correctly', () => {
    const big: Row[] = Array.from({ length: 25 }, (_, i) => ({
      id: i,
      name: `Item ${i}`,
      qty: i,
    }))
    const wrapper = mount(DataTable<Row>, {
      props: { items: big, columns, rowKey: 'id', pageSize: 10 },
    })
    expect(wrapper.text()).toContain('1 / 3')
  })
})
