<script setup lang="ts">
/**
 * Holographic 2.5D world map — interactive, draggable, zoomable, fullscreen.
 *
 * Architecture:
 *   - Base map: MapLibre GL (free OSS fork of Mapbox GL) via @antv/l7-maps
 *     `Mapbox` provider. main.ts aliases `window.mapboxgl = maplibregl` so L7
 *     uses MapLibre under the hood.
 *   - Tile style: CartoDB Dark Matter — free, no API key, dark space-y palette
 *     that fits the HUD aesthetic.
 *   - Data layers: WebGL via @antv/l7. Cylinders + glow halos + arc lines +
 *     extruded country polygons rendered above the basemap.
 *
 * Interactions:
 *   - Drag to pan, scroll to zoom, right-click drag to tilt+rotate (provided
 *     by MapLibre — no extra wiring).
 *   - Hover cylinder → tooltip + cylinder flashes white (active mix).
 *   - Click cylinder → side detail panel.
 *   - Right-click cylinder → context menu (filter expos/vendors, copy ISO).
 *   - Fullscreen toggle → expand container to viewport. ESC to exit.
 *   - Zoom +/- and reset-view buttons in bottom-right control cluster.
 */
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import { onClickOutside, useEventListener } from '@vueuse/core'
import { resolveCountry, flagEmoji } from '@/data/country_resolver'
import HudCountryDetailPanel from './HudCountryDetailPanel.vue'

interface CountryPoint {
  country: string
  expo_count: number
  vendor_count: number
}

const props = defineProps<{
  data: CountryPoint[]
  loading?: boolean
}>()

const router = useRouter()

const containerId = `hud-world-map-${Math.random().toString(36).slice(2, 9)}`
const containerRef = ref<HTMLElement | null>(null)
const wrapRef = ref<HTMLElement | null>(null)

const scene = shallowRef<unknown>(null)
const isReady = ref(false)
const unmatched = ref<string[]>([])

// Default camera — globe projection looks best at low zoom + slight pitch so
// the bumi-curve is obvious without occluding labels. Reset button returns here.
const DEFAULT_CAMERA = {
  center: [20, 15] as [number, number],
  pitch: 20,
  zoom: 1.1,
  rotation: 0,
}

interface ResolvedPoint {
  country: string
  cca2: string
  cca3: string
  lat: number
  lon: number
  expo_count: number
  vendor_count: number
}

interface HoverState { point: ResolvedPoint; x: number; y: number }
interface ContextState { point: ResolvedPoint; x: number; y: number }

const hoverState = ref<HoverState | null>(null)
const detailPoint = ref<ResolvedPoint | null>(null)
const contextState = ref<ContextState | null>(null)
const contextMenuRef = ref<HTMLElement | null>(null)

onClickOutside(contextMenuRef, () => {
  contextState.value = null
})

useEventListener('keydown', (e: KeyboardEvent) => {
  if (e.key === 'Escape' && contextState.value) {
    contextState.value = null
  }
})

const totalVendors = computed(() => (props.data ?? []).reduce((s, r) => s + r.vendor_count, 0))

function resolvePoints(rows: CountryPoint[]): { resolved: ResolvedPoint[]; missed: string[] } {
  const out: ResolvedPoint[] = []
  const miss: string[] = []
  const agg: Map<string, ResolvedPoint> = new Map()
  for (const r of rows) {
    const rec = resolveCountry(r.country)
    if (!rec) {
      miss.push(r.country)
      continue
    }
    const key = rec.cca2
    const existing = agg.get(key)
    if (existing) {
      existing.expo_count += r.expo_count
      existing.vendor_count += r.vendor_count
    } else {
      agg.set(key, {
        country: rec.name,
        cca2: rec.cca2,
        cca3: rec.cca3,
        lat: rec.lat,
        lon: rec.lon,
        expo_count: r.expo_count,
        vendor_count: r.vendor_count,
      })
    }
  }
  for (const v of agg.values()) out.push(v)
  out.sort((a, b) => b.vendor_count - a.vendor_count)
  return { resolved: out, missed: miss }
}

let layerRefs: unknown[] = []
const HUB_COUNT = 3

async function initScene() {
  if (!containerRef.value) return
  const [{ Scene, PointLayer, LineLayer }, { Mapbox }] = await Promise.all([
    import('@antv/l7'),
    import('@antv/l7-maps'),
  ])

  // CartoDB Dark Matter — free, no key, dark space-y palette. Provides the
  // basemap (countries, oceans, labels) underneath our data layers.
  // CartoDB requires attribution but L7 logo hide rule doesn't kill it; we
  // keep MapLibre's small attribution control instead (compliant + small).
  const s = new Scene({
    id: containerId,
    logoVisible: false,
    map: new Mapbox({
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: DEFAULT_CAMERA.center,
      pitch: DEFAULT_CAMERA.pitch,
      zoom: DEFAULT_CAMERA.zoom,
      rotation: DEFAULT_CAMERA.rotation,
      minZoom: 0.5,
      maxZoom: 12,
      attributionControl: true,
    } as unknown as ConstructorParameters<typeof Mapbox>[0]),
  } as unknown as ConstructorParameters<typeof Scene>[0])

  await new Promise<void>((resolve) => {
    s.once('loaded', () => resolve())
  })

  try {
    ;(s as unknown as { setLogoVisible?: (v: boolean) => void }).setLogoVisible?.(false)
  } catch {
    /* ignore */
  }

  // Reach into the underlying MapLibre instance to: switch to GLOBE projection
  // (MapLibre 5+ — this is what makes "real 2.5D" feel — the map curves at low
  // zoom and flattens to mercator as you zoom in), enable infinite horizontal
  // wrap so panning never reveals the projection edge, and recolor every admin
  // boundary line to HUD cyan to match the rest of the panel.
  const ml = ((s as unknown as { map?: { map?: unknown } }).map?.map
    ?? (s as unknown as { map?: unknown }).map) as
    | {
        setProjection?: (p: { type: string }) => void
        setRenderWorldCopies?: (v: boolean) => void
        getStyle?: () => { layers?: { id: string; type: string }[] }
        setPaintProperty?: (id: string, prop: string, value: unknown) => void
        on?: (ev: string, cb: () => void) => void
      }
    | undefined

  if (ml) {
    try {
      ml.setProjection?.({ type: 'globe' })
    } catch {
      /* older maplibre — fall back to mercator with wrap */
    }
    try {
      ml.setRenderWorldCopies?.(true)
    } catch {
      /* ignore */
    }

    const recolorBoundaries = () => {
      try {
        const layers = ml.getStyle?.()?.layers ?? []
        for (const layer of layers) {
          // CartoDB Dark Matter ships layers like "admin_country", "admin_state",
          // plus "boundary_*" + "country_label" — we only want line layers that
          // depict admin/political boundaries, not labels or fills.
          if (
            typeof layer.id !== 'string'
            || layer.type !== 'line'
            || !/boundary|admin|border/i.test(layer.id)
          ) {
            continue
          }
          ml.setPaintProperty?.(layer.id, 'line-color', '#22d3ee')
          ml.setPaintProperty?.(layer.id, 'line-opacity', 0.55)
          ml.setPaintProperty?.(layer.id, 'line-width', 0.6)
        }
      } catch {
        /* style not ready yet — styledata event will retry */
      }
    }
    recolorBoundaries()
    // Style streams in over time; re-apply on each chunk so newly added layers
    // also get the cyan treatment.
    ml.on?.('styledata', recolorBoundaries)
  }

  // No country polygon overlay — CartoDB basemap already paints countries
  // and boundaries with proper labels at every zoom level. Drawing our own
  // would just dim the basemap detail.

  scene.value = s
  isReady.value = true
  applyDataLayers(PointLayer, LineLayer)
}

function disposeDataLayers() {
  if (!scene.value) return
  const s = scene.value as { removeLayer: (layer: unknown) => void }
  for (const layer of layerRefs) {
    try {
      s.removeLayer(layer)
    } catch {
      /* layer already detached */
    }
  }
  layerRefs = []
}

// L7's chained-builder API has loose TS types upstream; keeping this branch
// in pragmatic any-cast land is more readable than the 6-layer self-reference
// gymnastics needed to make Pyright happy.
/* eslint-disable @typescript-eslint/no-explicit-any */
async function applyDataLayers(
  PointLayer?: any,
  LineLayer?: any,
) {
  if (!isReady.value || !scene.value) return
  if (!PointLayer || !LineLayer) {
    const mod: any = await import('@antv/l7')
    PointLayer = mod.PointLayer
    LineLayer = mod.LineLayer
  }

  disposeDataLayers()

  const { resolved, missed } = resolvePoints(props.data ?? [])
  unmatched.value = Array.from(new Set(missed))

  if (resolved.length === 0) return

  const s: any = scene.value

  const maxVendor = Math.max(1, ...resolved.map((p) => p.vendor_count))
  const hubSet = new Set(resolved.slice(0, HUB_COUNT).map((p) => p.cca2))
  const points = resolved.map((p) => {
    const isHub = hubSet.has(p.cca2)
    const baseHeight = 80000 + (p.vendor_count / maxVendor) * 360000
    const cylHeight = isHub ? baseHeight * 1.4 : baseHeight
    return {
      ...p,
      cylinder_h: cylHeight,
      pulse_size: 14 + (p.vendor_count / maxVendor) * 22,
      label: `${p.cca2} · ${p.vendor_count}`,
      color_value: isHub ? 100 : p.vendor_count,
      is_hub: isHub,
    }
  })

  function tierColor(count: number): string {
    if (count >= 100) return '#ff5577'
    if (count >= 50) return '#ff8a3d'
    if (count >= 20) return '#ffaa33'
    if (count >= 5) return '#39ffaa'
    return '#39d8ff'
  }

  const haloOuter = new PointLayer({ zIndex: 9, depth: false })
    .source(points, { parser: { type: 'json', x: 'lon', y: 'lat' } })
    .shape('circle')
    .size('pulse_size', (v: number) => v * 2.6)
    .color('#39d8ff')
    .style({ opacity: 0.18 })

  const haloInner = new PointLayer({ zIndex: 9.5, depth: false })
    .source(points, { parser: { type: 'json', x: 'lon', y: 'lat' } })
    .shape('circle')
    .size('pulse_size', (v: number) => v * 1.5)
    .color('#39d8ff')
    .style({ opacity: 0.32 })

  const pulse = new PointLayer({ zIndex: 10 })
    .source(points, { parser: { type: 'json', x: 'lon', y: 'lat' } })
    .shape('circle')
    .active(true)
    .animate(true)
    .size('pulse_size')
    .color('color_value', (v: number) => tierColor(v))
    .style({ opacity: 0.7 })

  const cylinder: any = new PointLayer({ depth: false, zIndex: 11 })
    .source(points, { parser: { type: 'json', x: 'lon', y: 'lat' } })
    .shape('cylinder')
    .size('cylinder_h', (h: number) => [3.8, 3.8, h])
    .color('color_value', (v: number) => tierColor(v))
    .active({ color: '#ffffff', mix: 0.6 })
    .style({
      opacity: 0.95,
      opacityLinear: { enable: true, dir: 'up' },
      lightEnable: false,
    })

  cylinder.on('mousemove', (ev: any) => {
    if (ev.feature) {
      hoverState.value = { point: ev.feature, x: ev.x ?? 0, y: ev.y ?? 0 }
      if (containerRef.value) containerRef.value.style.cursor = 'pointer'
    }
  })
  cylinder.on('unmousemove', () => {
    hoverState.value = null
    if (containerRef.value) containerRef.value.style.cursor = ''
  })
  cylinder.on('mouseout', () => {
    hoverState.value = null
    if (containerRef.value) containerRef.value.style.cursor = ''
  })
  cylinder.on('click', (ev: any) => {
    if (ev.feature) {
      detailPoint.value = ev.feature
      contextState.value = null
    }
  })
  cylinder.on('contextmenu', (ev: any) => {
    ev.originEvent?.preventDefault()
    if (ev.feature) {
      contextState.value = { point: ev.feature, x: ev.x ?? 0, y: ev.y ?? 0 }
    }
  })

  const arcSrc = resolved
    .slice(0, HUB_COUNT)
    .flatMap((h) =>
      resolved.slice(HUB_COUNT).map((t) => ({
        x: h.lon,
        y: h.lat,
        x1: t.lon,
        y1: t.lat,
      })),
    )

  let arcLayer: any = null
  if (arcSrc.length > 0) {
    arcLayer = new LineLayer({ blend: 'normal', zIndex: 8 })
      .source(arcSrc, {
        parser: { type: 'json', x: 'x', y: 'y', x1: 'x1', y1: 'y1' },
      })
      .size(1.6)
      .shape('arc3d')
      .color('rgb(57, 216, 255)')
      .animate({ interval: 0.18, trailLength: 0.5, duration: 1.2 })
      .style({
        sourceColor: 'rgb(57, 216, 255)',
        targetColor: 'rgb(255, 85, 119)',
        thetaOffset: 1.1,
        opacity: 0.85,
      })
  }

  const labels = new PointLayer({ zIndex: 12 })
    .source(points, { parser: { type: 'json', x: 'lon', y: 'lat' } })
    .shape('label', 'label')
    .size(11)
    .color('#e8eaed')
    .style({
      textAnchor: 'center',
      stroke: '#06080d',
      strokeWidth: 1.4,
      raisingHeight: 420000,
      textAllowOverlap: false,
      heightFixed: true,
    })

  s.addLayer(haloOuter)
  s.addLayer(haloInner)
  s.addLayer(pulse)
  s.addLayer(cylinder)
  if (arcLayer) s.addLayer(arcLayer)
  s.addLayer(labels)

  layerRefs.push(haloOuter, haloInner, pulse, cylinder)
  if (arcLayer) layerRefs.push(arcLayer)
  layerRefs.push(labels)
}
/* eslint-enable @typescript-eslint/no-explicit-any */

watch(
  () => props.data,
  () => {
    void applyDataLayers()
  },
  { deep: true },
)

onMounted(() => {
  void initScene()
})

onBeforeUnmount(() => {
  if (scene.value) {
    try {
      ;(scene.value as { destroy: () => void }).destroy()
    } catch {
      /* ignore */
    }
    scene.value = null
  }
  layerRefs = []
})

// Camera controls
function zoomIn() {
  if (!scene.value) return
  try {
    const s = scene.value as { getZoom: () => number; setZoomAndCenter: (z: number, c: [number, number]) => void; getCenter: () => { lng: number; lat: number } }
    const z = s.getZoom()
    const c = s.getCenter()
    s.setZoomAndCenter(Math.min(z + 1, 12), [c.lng, c.lat])
  } catch {
    /* ignore */
  }
}
function zoomOut() {
  if (!scene.value) return
  try {
    const s = scene.value as { getZoom: () => number; setZoomAndCenter: (z: number, c: [number, number]) => void; getCenter: () => { lng: number; lat: number } }
    const z = s.getZoom()
    const c = s.getCenter()
    s.setZoomAndCenter(Math.max(z - 1, 0.5), [c.lng, c.lat])
  } catch {
    /* ignore */
  }
}
function resetView() {
  if (!scene.value) return
  try {
    const s = scene.value as {
      setZoomAndCenter: (z: number, c: [number, number]) => void
      setPitch: (p: number) => void
      setRotation: (r: number) => void
    }
    s.setPitch(DEFAULT_CAMERA.pitch)
    s.setRotation(DEFAULT_CAMERA.rotation)
    s.setZoomAndCenter(DEFAULT_CAMERA.zoom, DEFAULT_CAMERA.center)
  } catch {
    /* ignore */
  }
}

// Context-menu actions
function ctxFilterExpos() {
  if (!contextState.value) return
  router.push({ path: '/expos', query: { country: contextState.value.point.country } })
  contextState.value = null
}
function ctxFilterVendors() {
  if (!contextState.value) return
  router.push({ path: '/vendors', query: { country: contextState.value.point.country } })
  contextState.value = null
}
async function ctxCopyIso() {
  if (!contextState.value) return
  try {
    await navigator.clipboard.writeText(contextState.value.point.cca2)
  } catch {
    /* ignore */
  }
  contextState.value = null
}
</script>

<template>
  <section
    ref="wrapRef"
    class="relative flex h-[460px] w-full flex-col overflow-hidden border border-cyan-400/20 bg-[#06080d] shadow-[inset_0_0_60px_rgba(57,216,255,0.05)]"
  >
    <header
      class="pointer-events-none absolute left-0 right-0 top-0 z-20 flex items-center justify-between border-b border-cyan-400/20 bg-[#06080d]/85 px-3 py-2 backdrop-blur"
    >
      <div class="flex items-center gap-2">
        <span class="font-mono text-2xs uppercase tracking-ops text-cyan-400/70">MAP-01</span>
        <h2 class="font-mono text-2xs font-medium uppercase tracking-ops text-cyan-200">
          DISTRIBUSI GEOGRAFIS · TACTICAL VIEW
        </h2>
      </div>
      <div class="flex items-center gap-3">
        <span class="flex items-center gap-1.5 font-mono text-2xs uppercase tracking-ops text-emerald-400">
          <span class="relative flex h-1.5 w-1.5">
            <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span class="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-400" />
          </span>
          LIVE 5s
        </span>
        <span class="font-mono text-2xs text-cyan-400/60">
          {{ (data ?? []).length }} negara · {{ unmatched.length }} unmatched
        </span>
        <span
          v-if="loading"
          class="font-mono text-2xs uppercase tracking-ops text-warn-400"
        >
          MEMUAT
        </span>
      </div>
    </header>

    <!-- Map canvas. Cursor hints to user that pan is available. -->
    <div
      :id="containerId"
      ref="containerRef"
      class="absolute inset-0 cursor-grab active:cursor-grabbing"
    />

    <!-- Soft vignette for HUD feel; pointer-events-none so it doesn't eat drag. -->
    <div class="hud-map-vignette pointer-events-none absolute inset-0 z-[6]" />

    <!-- Camera controls cluster (bottom-right). pointer-events-auto on inner buttons. -->
    <div class="absolute bottom-9 right-2 z-30 flex flex-col gap-1">
      <button
        class="hud-map-btn"
        type="button"
        title="Perbesar"
        @click="zoomIn"
      >
        <FaIcon :icon="['fas', 'plus']" class="text-2xs" />
      </button>
      <button
        class="hud-map-btn"
        type="button"
        title="Perkecil"
        @click="zoomOut"
      >
        <FaIcon :icon="['fas', 'minus']" class="text-2xs" />
      </button>
      <button
        class="hud-map-btn"
        type="button"
        title="Reset tampilan"
        @click="resetView"
      >
        <FaIcon :icon="['fas', 'rotate']" class="text-2xs" />
      </button>
    </div>

    <!-- Hover tooltip -->
    <div
      v-if="hoverState"
      :style="{ left: `${hoverState.x + 14}px`, top: `${hoverState.y + 14}px` }"
      class="pointer-events-none absolute z-30 max-w-[260px] border border-cyan-400/40 bg-[#06080d]/95 px-2.5 py-2 shadow-[0_0_16px_rgba(57,216,255,0.25)] backdrop-blur"
    >
      <div class="flex items-center gap-2 font-mono text-xs text-cyan-200">
        <span class="text-base">{{ flagEmoji(hoverState.point.cca2) }}</span>
        <span class="font-semibold">{{ hoverState.point.country }}</span>
      </div>
      <div class="mt-1 grid grid-cols-2 gap-2 font-mono text-2xs text-base-300">
        <div>VENDOR <span class="hud-mono-num text-cyan-300">{{ hoverState.point.vendor_count }}</span></div>
        <div>EKSPO <span class="hud-mono-num text-cyan-300">{{ hoverState.point.expo_count }}</span></div>
      </div>
      <div class="mt-1 font-mono text-[10px] uppercase tracking-ops text-cyan-400/50">
        Klik kiri = detail · Klik kanan = aksi
      </div>
    </div>

    <!-- Context menu -->
    <div
      v-if="contextState"
      ref="contextMenuRef"
      :style="{ left: `${contextState.x}px`, top: `${contextState.y}px` }"
      class="absolute z-40 min-w-[200px] border border-cyan-400/40 bg-[#06080d]/95 py-1 shadow-[0_4px_24px_rgba(0,0,0,0.6)] backdrop-blur"
    >
      <div class="border-b border-cyan-400/20 px-3 py-1 font-mono text-2xs uppercase tracking-ops text-cyan-400/70">
        {{ flagEmoji(contextState.point.cca2) }} {{ contextState.point.country }}
      </div>
      <button class="hud-context-item" type="button" @click="ctxFilterExpos">
        <FaIcon :icon="['fas', 'flag-checkered']" class="mr-2 text-2xs" />
        Filter Ekspo di sini
      </button>
      <button class="hud-context-item" type="button" @click="ctxFilterVendors">
        <FaIcon :icon="['fas', 'building']" class="mr-2 text-2xs" />
        Filter Vendor di sini
      </button>
      <button class="hud-context-item" type="button" @click="ctxCopyIso">
        <FaIcon :icon="['fas', 'copy']" class="mr-2 text-2xs" />
        Copy ISO ({{ contextState.point.cca2 }})
      </button>
    </div>

    <!-- Detail side panel -->
    <HudCountryDetailPanel
      :visible="!!detailPoint"
      :country="detailPoint?.country ?? ''"
      :cca2="detailPoint?.cca2 ?? ''"
      :total-vendors="totalVendors"
      @close="detailPoint = null"
    />

    <!-- Empty state -->
    <div
      v-if="!loading && (data?.length ?? 0) === 0"
      class="pointer-events-none absolute inset-0 z-20 flex items-center justify-center"
    >
      <div class="border border-cyan-400/30 bg-[#06080d]/90 px-4 py-3 font-mono text-2xs uppercase tracking-ops text-cyan-300/80 backdrop-blur">
        Belum ada ekspo terindeks dengan field country.
      </div>
    </div>

    <!-- Footer legend -->
    <footer
      class="pointer-events-none absolute bottom-0 left-0 right-0 z-20 flex items-center justify-between border-t border-cyan-400/20 bg-[#06080d]/85 px-3 py-1.5 backdrop-blur"
    >
      <div class="flex items-center gap-3 font-mono text-2xs text-base-400">
        <span class="flex items-center gap-1">
          <span class="inline-block h-2 w-2 rounded-full bg-[#39d8ff]" /> 1-4
        </span>
        <span class="flex items-center gap-1">
          <span class="inline-block h-2 w-2 rounded-full bg-[#39ffaa]" /> 5-19
        </span>
        <span class="flex items-center gap-1">
          <span class="inline-block h-2 w-2 rounded-full bg-[#ffaa33]" /> 20-49
        </span>
        <span class="flex items-center gap-1">
          <span class="inline-block h-2 w-2 rounded-full bg-[#ff8a3d]" /> 50-99
        </span>
        <span class="flex items-center gap-1">
          <span class="inline-block h-2 w-2 rounded-full bg-[#ff5577]" /> HUB
        </span>
      </div>
      <span class="font-mono text-2xs text-cyan-400/50">
        DRAG · SCROLL · RIGHT-DRAG ROTATE
      </span>
    </footer>
  </section>
</template>
