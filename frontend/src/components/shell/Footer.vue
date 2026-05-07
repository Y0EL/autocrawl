<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { api } from '@/api/client'

const now = ref(new Date())
let tick = 0
onMounted(() => { tick = window.setInterval(() => (now.value = new Date()), 1000) })
onBeforeUnmount(() => { if (tick) window.clearInterval(tick) })

const health = useQuery({
  queryKey: ['health'],
  queryFn: api.health,
  refetchInterval: 10000,
})

const tone = computed<'ok' | 'warn' | 'crit'>(() => {
  const h = health.data.value
  if (!h) return 'warn'
  if (h.status === 'ok' && h.db === 'ok') return 'ok'
  if (h.db === 'down') return 'crit'
  return 'warn'
})

const stamp = computed(() => {
  const d = now.value
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${hh}:${mm}:${ss}`
})
</script>

<template>
  <footer class="rule-t bg-paper flex h-7 shrink-0 items-center justify-between px-5">
    <span class="label-mono">Build 0.3 · Autocrawl · Edisi paper</span>
    <div class="flex items-center gap-4">
      <span class="font-mono text-[0.625rem] tracking-[0.14em] text-ink-mute tabular-nums">{{ stamp }}</span>
      <span class="flex items-center gap-1.5">
        <span class="dot" :class="`dot-${tone}`"></span>
        <span class="label-mono">gsp.engineerteam</span>
      </span>
    </div>
  </footer>
</template>
