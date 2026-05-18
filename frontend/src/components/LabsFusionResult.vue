<script setup lang="ts">
import { ref } from 'vue'
import { toast } from 'vue-sonner'
import { api } from '@/api/client'
import type { Fusion, FusionEmailDraft, FusionListItem } from '@/api/types'
import TagBadge from '@/components/TagBadge.vue'

const props = defineProps<{
  fusion: Fusion | FusionListItem
  compact?: boolean
}>()

const emit = defineEmits<{
  (e: 'open-detail', fusionId: string): void
}>()

const expanded = ref<Set<number>>(new Set())

function toggleExpand(id: number) {
  if (expanded.value.has(id)) expanded.value.delete(id)
  else expanded.value.add(id)
  expanded.value = new Set(expanded.value)
}

async function copyDraft(draft: FusionEmailDraft) {
  const text = `Subject: ${draft.subject}\n\n${draft.body}`
  try {
    await navigator.clipboard.writeText(text)
    toast.success('Draft tersalin')
    try {
      await api.labs.markCopied(props.fusion.fusion_id, draft.id)
    } catch { /* analytics non-fatal */ }
  } catch {
    toast.error('Gagal salin ke clipboard')
  }
}
</script>

<template>
  <div
    v-if="compact"
    class="card overflow-hidden cursor-pointer transition-all hover:border-amber/40 hover:-translate-y-px"
    @click="emit('open-detail', fusion.fusion_id)"
  >
    <div class="card-body flex gap-3">
      <div class="h-20 w-32 shrink-0 overflow-hidden rounded-[4px] border border-rule-strong bg-surface-2">
        <img v-if="fusion.image_url" :src="fusion.image_url" alt="" class="h-full w-full object-cover">
      </div>
      <div class="min-w-0 flex-1">
        <p class="truncate text-[13px] font-semibold text-ink">{{ fusion.name }}</p>
        <p v-if="fusion.tagline" class="truncate text-[11.5px] text-ink-2 italic mt-0.5">{{ fusion.tagline }}</p>
        <p class="mt-1.5 num-display text-[10.5px] text-ink-mute">
          {{ ('source_vendor_count' in fusion ? fusion.source_vendor_count : (fusion as Fusion).source_vendor_ids?.length) ?? 0 }} vendor source
        </p>
      </div>
    </div>
  </div>

  <div v-else-if="'description' in fusion" class="space-y-4">
    <!-- Hero panel -->
    <div class="card-2 rounded-[6px] p-4 space-y-3">
      <div v-if="fusion.image_url" class="overflow-hidden rounded-[4px] border border-rule-strong">
        <img :src="fusion.image_url" alt="" class="w-full">
      </div>
      <h2 class="text-[24px] font-bold text-ink tracking-[-0.02em]">{{ fusion.name }}</h2>
      <p v-if="fusion.tagline" class="text-[15px] text-amber italic leading-snug">"{{ fusion.tagline }}"</p>
      <p v-if="fusion.description" class="text-[13.5px] text-ink-2 leading-relaxed" style="white-space: pre-line">{{ fusion.description }}</p>

      <div v-if="fusion.industries.length" class="flex flex-wrap items-center gap-1.5">
        <TagBadge
          v-for="ind in fusion.industries"
          :key="ind"
          :raw="ind"
          size="sm"
        />
      </div>

      <!-- Pull-quote treatment: amber tint + full hairline border + leading mark.
           No side-stripe (Impeccable ban: border-left greater than 1px as colored
           accent on callouts is forbidden). -->
      <div v-if="fusion.rationale" class="px-3 py-2 bg-amber/5 border border-amber/25 rounded-[4px]">
        <p class="text-[12px] italic text-ink-2 leading-relaxed" style="white-space: pre-line">{{ fusion.rationale }}</p>
      </div>
    </div>

    <!-- Source vendors -->
    <div v-if="fusion.source_vendors?.length" class="space-y-2">
      <div class="flex items-center justify-between mb-2">
        <span class="label">Source Vendors</span>
        <span class="label label-mute">{{ fusion.source_vendors.length }}</span>
      </div>
      <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div
          v-for="v in fusion.source_vendors"
          :key="v.vendor_id"
          class="flex items-center gap-3 p-2.5 rounded-[6px] border border-rule bg-surface-2/50"
        >
          <div class="h-8 w-8 shrink-0 rounded-[3px] border border-rule-strong bg-surface flex items-center justify-center">
            <img v-if="v.logo_url" :src="v.logo_url" :alt="v.company_name" class="h-6 w-6 object-contain" referrerpolicy="no-referrer">
            <span v-else class="text-[12px] font-bold text-amber">{{ v.company_name.charAt(0).toUpperCase() }}</span>
          </div>
          <div class="min-w-0">
            <p class="truncate text-[13px] text-ink">{{ v.company_name }}</p>
            <p class="truncate num-display text-[10.5px] text-ink-mute">{{ v.domain }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Email drafts -->
    <div v-if="fusion.drafts?.length" class="space-y-2">
      <div class="flex items-center justify-between mb-2">
        <span class="label">Email Drafts</span>
        <span class="label label-mute">{{ fusion.drafts.length }}</span>
      </div>
      <div class="space-y-2">
        <div
          v-for="d in fusion.drafts"
          :key="d.id"
          class="rounded-[6px] border border-rule overflow-hidden"
        >
          <button
            class="flex w-full items-center justify-between gap-3 bg-surface-2 px-3 py-2.5 text-left transition-colors hover:bg-surface-3"
            type="button"
            @click="toggleExpand(d.id)"
          >
            <div class="min-w-0">
              <p class="truncate text-[13px] text-ink">{{ d.vendor_name || d.vendor_id }}</p>
              <p class="truncate num-display text-[11px] text-ink-mute">{{ d.to_email }} · {{ d.subject }}</p>
            </div>
            <FaIcon :icon="['fas', expanded.has(d.id) ? 'minus' : 'plus']" class="text-[10px] text-ink-mute shrink-0" />
          </button>
          <div v-if="expanded.has(d.id)" class="border-t border-rule p-3.5 space-y-3 bg-surface">
            <div>
              <span class="label">Subject</span>
              <p class="text-[14px] text-ink mt-1">{{ d.subject }}</p>
            </div>
            <div>
              <span class="label">Body</span>
              <pre class="mt-1 whitespace-pre-wrap break-words text-[13px] text-ink-2 leading-relaxed">{{ d.body }}</pre>
            </div>
            <div class="flex justify-between items-center pt-2 rule-t">
              <p v-if="d.copied_at" class="num-display text-[10.5px] text-ink-mute">
                <FaIcon :icon="['fas', 'check']" class="text-ok mr-1 text-[9px]" />
                Pernah disalin: {{ d.copied_at }}
              </p>
              <span v-else></span>
              <button class="btn btn-amber h-8" type="button" @click="copyDraft(d)">
                <FaIcon :icon="['fas', 'copy']" class="text-[10px]" />
                Salin
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
