<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { RouterLink } from 'vue-router'

interface NavItem {
  to: string
  label: string
  icon: string
}

const items: NavItem[] = [
  { to: '/', label: 'Ringkasan', icon: 'fa-solid fa-gauge-high' },
  { to: '/vendors', label: 'Vendor', icon: 'fa-solid fa-building' },
  { to: '/expos', label: 'Expo', icon: 'fa-solid fa-flag-checkered' },
  { to: '/pdfs', label: 'Brosur PDF', icon: 'fa-solid fa-file-pdf' },
  { to: '/runs', label: 'Riwayat Run', icon: 'fa-solid fa-clock-rotate-left' },
]

const collapsed = useStorage('autocrawl-sidebar-collapsed', false)
</script>

<template>
  <aside
    :class="[
      'flex h-full shrink-0 flex-col border-r border-zinc-200 bg-white transition-[width] duration-200 dark:border-zinc-800 dark:bg-zinc-950',
      collapsed ? 'w-16' : 'w-56',
    ]"
  >
    <div
      class="flex h-14 items-center gap-3 border-b border-zinc-200 px-3 dark:border-zinc-800"
      :class="collapsed ? 'justify-center' : ''"
    >
      <div
        class="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-accent-500 to-accent-700 text-white shadow-sm"
      >
        <i class="fa-solid fa-spider text-sm"></i>
      </div>
      <div v-if="!collapsed" class="flex flex-col leading-tight">
        <span class="text-sm font-bold tracking-tight">AUTOCRAWL</span>
        <span class="font-mono text-[10px] text-zinc-500 dark:text-zinc-400">CONSOLE v0.1</span>
      </div>
    </div>

    <nav class="flex flex-1 flex-col gap-0.5 p-2">
      <RouterLink v-for="item in items" :key="item.to" :to="item.to" v-slot="{ isActive }">
        <span
          :class="[
            'group flex items-center gap-3 rounded-md text-sm font-medium transition-colors',
            collapsed ? 'h-10 w-10 justify-center' : 'h-9 px-3',
            isActive
              ? 'bg-accent-50 text-accent-700 dark:bg-accent-500/10 dark:text-accent-300'
              : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800/60 dark:hover:text-zinc-100',
          ]"
          :title="collapsed ? item.label : undefined"
        >
          <i :class="[item.icon, 'w-4 text-center text-sm']"></i>
          <span v-if="!collapsed">{{ item.label }}</span>
        </span>
      </RouterLink>
    </nav>

    <button
      class="m-2 flex h-9 items-center justify-center gap-2 rounded-md text-xs text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800/60 dark:hover:text-zinc-100"
      :title="collapsed ? 'Expand' : 'Collapse'"
      @click="collapsed = !collapsed"
    >
      <i :class="collapsed ? 'fa-solid fa-angles-right' : 'fa-solid fa-angles-left'"></i>
      <span v-if="!collapsed">Collapse</span>
    </button>
  </aside>
</template>
