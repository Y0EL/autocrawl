<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Vendor } from '@/api/types'

defineProps<{
  vendors: Vendor[]
}>()

const sourceLabel = (v: Vendor): { label: string; cls: string; icon: string } => {
  const types = new Set((v.source_trail ?? []).map((s) => s.type))
  if (types.has('pdf')) {
    return {
      label: 'PDF',
      cls: 'bg-rose-500/10 text-rose-400 ring-1 ring-rose-500/30',
      icon: 'fa-solid fa-file-pdf',
    }
  }
  if (types.has('aggregator')) {
    return {
      label: 'AGG',
      cls: 'bg-sky-500/10 text-sky-400 ring-1 ring-sky-500/30',
      icon: 'fa-solid fa-globe',
    }
  }
  return {
    label: 'SRC',
    cls: 'bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/30',
    icon: 'fa-solid fa-magnifying-glass',
  }
}

const relativeTime = (iso: string): string => {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'baru saja'
  if (mins < 60) return `${mins}m lalu`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}j lalu`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}h lalu`
  const months = Math.floor(days / 30)
  return `${months}bln lalu`
}
</script>

<template>
  <div class="card flex h-full flex-col border-zinc-800 bg-zinc-900/50">
    <div class="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
      <h3 class="text-sm font-semibold text-zinc-100">
        <i class="fa-solid fa-rss mr-1.5 text-zinc-500"></i>
        Activity
      </h3>
      <span class="text-xs text-zinc-500">Vendor terbaru</span>
    </div>
    <div class="flex-1 divide-y divide-zinc-800/70 overflow-y-auto">
      <RouterLink
        v-for="v in vendors"
        :key="v.domain"
        :to="`/vendors/${v.domain}`"
        class="block px-4 py-3 transition-colors hover:bg-zinc-800/40"
      >
        <div class="flex items-start gap-3">
          <span
            v-if="!v.logo_url"
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-sm font-semibold text-zinc-300"
          >
            {{ v.company_name.charAt(0) }}
          </span>
          <img
            v-else
            :src="v.logo_url"
            :alt="v.company_name"
            class="h-9 w-9 shrink-0 rounded-full bg-zinc-800 object-contain p-1"
            referrerpolicy="no-referrer"
          />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <span class="truncate text-sm font-medium text-zinc-100">{{ v.company_name }}</span>
              <span class="text-xs text-zinc-500">@{{ v.domain }}</span>
            </div>
            <p
              v-if="v.tagline || v.description"
              class="mt-0.5 line-clamp-2 text-xs text-zinc-400"
            >
              {{ v.tagline || (v.description ?? '').slice(0, 120) }}
            </p>
            <div class="mt-1 flex items-center gap-2 text-xs text-zinc-500">
              <span :class="['inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium', sourceLabel(v).cls]">
                <i :class="[sourceLabel(v).icon, 'text-[9px]']"></i>
                {{ sourceLabel(v).label }}
              </span>
              <span v-if="v.address?.country">
                <i class="fa-solid fa-location-dot text-[9px]"></i>
                {{ v.address.country }}
              </span>
              <span class="ml-auto">{{ relativeTime(v.last_enriched_at) }}</span>
            </div>
          </div>
        </div>
      </RouterLink>
      <div v-if="!vendors.length" class="p-6 text-center text-sm text-zinc-500">
        Belum ada vendor terkoleksi.
      </div>
    </div>
  </div>
</template>
