<script setup lang="ts" generic="T extends object">
import { ref, computed } from 'vue'

interface Column<T> {
  key: keyof T | string
  label: string
  width?: string
  align?: 'left' | 'right' | 'center'
}

const props = withDefaults(
  defineProps<{
    items: T[]
    columns: Column<T>[]
    rowKey: keyof T
    loading?: boolean
    emptyLabel?: string
    pageSize?: number
  }>(),
  { loading: false, emptyLabel: 'Belum ada data', pageSize: 20 },
)

const page = ref(1)

const totalPages = computed(() => Math.max(1, Math.ceil(props.items.length / props.pageSize)))
const paged = computed(() => {
  const start = (page.value - 1) * props.pageSize
  return props.items.slice(start, start + props.pageSize)
})

function go(p: number) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
}
</script>

<template>
  <div class="card overflow-hidden">
    <div class="overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead class="sticky top-0 z-10 border-b border-zinc-200 bg-zinc-50 backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/80">
          <tr>
            <th
              v-for="col in columns"
              :key="String(col.key)"
              class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400"
              :class="{
                'text-right': col.align === 'right',
                'text-center': col.align === 'center',
              }"
              :style="col.width ? { width: col.width } : {}"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-zinc-100 dark:divide-zinc-800">
          <tr v-if="loading">
            <td :colspan="columns.length" class="px-4 py-12 text-center">
              <i class="fa-solid fa-circle-notch fa-spin text-zinc-400"></i>
              <span class="ml-2 text-zinc-500 dark:text-zinc-400">Memuat data</span>
            </td>
          </tr>
          <tr v-else-if="!items.length">
            <td :colspan="columns.length" class="px-4 py-16 text-center">
              <div class="flex flex-col items-center gap-2 text-zinc-500 dark:text-zinc-400">
                <i class="fa-regular fa-folder-open text-2xl"></i>
                <span>{{ emptyLabel }}</span>
              </div>
            </td>
          </tr>
          <tr
            v-else
            v-for="row in paged"
            :key="String(row[rowKey])"
            class="transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/40"
          >
            <td
              v-for="col in columns"
              :key="String(col.key)"
              class="px-4 py-3 align-middle text-zinc-700 dark:text-zinc-200"
              :class="{
                'text-right': col.align === 'right',
                'text-center': col.align === 'center',
              }"
            >
              <slot :name="`cell-${String(col.key)}`" :row="row" :value="row[col.key as keyof T]">
                {{ row[col.key as keyof T] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="!loading && items.length"
      class="flex items-center justify-between border-t border-zinc-200 bg-zinc-50 px-4 py-3 text-xs text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900/60 dark:text-zinc-400"
    >
      <span>
        Menampilkan {{ (page - 1) * pageSize + 1 }} sampai
        {{ Math.min(page * pageSize, items.length) }} dari {{ items.length }} data
      </span>
      <div class="flex items-center gap-1">
        <button
          class="btn-ghost h-7 w-7 rounded-md p-0"
          :disabled="page <= 1"
          @click="go(page - 1)"
        >
          <i class="fa-solid fa-chevron-left text-xs"></i>
        </button>
        <span class="px-2 tabular-nums">{{ page }} / {{ totalPages }}</span>
        <button
          class="btn-ghost h-7 w-7 rounded-md p-0"
          :disabled="page >= totalPages"
          @click="go(page + 1)"
        >
          <i class="fa-solid fa-chevron-right text-xs"></i>
        </button>
      </div>
    </div>
  </div>
</template>
