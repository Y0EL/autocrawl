<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  open: boolean
  title?: string
  body?: string
  countdown?: number
  confirmLabel?: string
  cancelLabel?: string
  tone?: 'danger' | 'accent'
}>(), {
  title: 'Konfirmasi',
  body: '',
  countdown: 3,
  confirmLabel: 'Setuju',
  cancelLabel: 'Batal',
  tone: 'danger',
})

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
  (e: 'update:open', value: boolean): void
}>()

const remaining = ref(props.countdown)
let timer: ReturnType<typeof setInterval> | null = null

function clearTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function startCountdown() {
  clearTimer()
  remaining.value = props.countdown
  timer = setInterval(() => {
    if (remaining.value > 0) {
      remaining.value -= 1
    }
    if (remaining.value <= 0) {
      clearTimer()
    }
  }, 1000)
}

watch(
  () => props.open,
  (val) => {
    if (val) {
      startCountdown()
      window.addEventListener('keydown', onKey)
    } else {
      clearTimer()
      window.removeEventListener('keydown', onKey)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  clearTimer()
  window.removeEventListener('keydown', onKey)
})

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    onCancel()
  }
}

const ready = computed(() => remaining.value <= 0)
const buttonLabel = computed(() => (ready.value ? props.confirmLabel : `Tunggu ${remaining.value}..`))

function onConfirm() {
  if (!ready.value) return
  emit('confirm')
  emit('update:open', false)
}

function onCancel() {
  emit('cancel')
  emit('update:open', false)
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-base-950/70 p-4 backdrop-blur-sm"
      @click.self="onCancel"
    >
      <div
        class="hud-panel w-full max-w-md border-base-300 bg-white shadow-hud-strong dark:border-base-700 dark:bg-base-900"
      >
        <header class="hud-panel-head">
          <div class="flex items-center gap-2">
            <span class="font-mono text-2xs uppercase tracking-ops text-base-400 dark:text-base-500">!!</span>
            <h2 class="hud-panel-title">{{ title }}</h2>
          </div>
        </header>
        <div class="hud-panel-body">
          <p class="text-sm text-base-700 dark:text-base-200" style="white-space: pre-line">{{ body }}</p>
          <div class="mt-4 flex justify-end gap-2">
            <button class="hud-btn hud-btn-ghost" type="button" @click="onCancel">
              {{ cancelLabel }}
            </button>
            <button
              :class="[
                'hud-btn',
                tone === 'danger' ? 'hud-btn-danger' : 'hud-btn-primary',
                !ready ? 'opacity-60 cursor-not-allowed' : '',
              ]"
              type="button"
              :disabled="!ready"
              @click="onConfirm"
            >
              {{ buttonLabel }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
