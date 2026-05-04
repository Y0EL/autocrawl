<script setup lang="ts">
/**
 * 3D world map for the overview dashboard. Powered by @antv/l7 (WebGL).
 *
 * Design intent:
 *   - One panel at the top of the overview that turns the messy ExpoORM.country
 *     strings into geographic intelligence — where the security/defense
 *     ecosystem actually clusters.
 *   - Visual encoding: cylinder height ∝ vendor count per country; pulse circle
 *     and label sit on top so the country is readable even at zoom-out.
 *   - Boundaries + filled polygons give context without dominating the data.
 *
 * The component is self-contained: it owns its Scene, fetches the TopoJSON
 * lazily, recomputes layers when the input data changes, and tears down on
 * unmount so navigating between routes doesn't leak GL contexts.
 */
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { feature } from 'topojson-client'
import type { Topology, GeometryCollection } from 'topojson-specification'
import type { FeatureCollection } from 'geojson'
import { resolveCountry } from '@/data/country_resolver'

interface CountryPoint {
  country: string
  expo_count: number
  vendor_count: number
}

const props = defineProps<{
  data: CountryPoint[]
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'pick', payload: { country: string; cca2: string }): void
}>()

const containerId = `hud-world-map-${Math.random().toString(36).slice(2, 9)}`
const containerRef = ref<HTMLElement | null>(null)

// `shallowRef` because Scene/Layer are non-reactive native objects.
const scene = shallowRef<unknown>(null)
const isReady = ref(false)
const unmatched = ref<string[]>([])

interface ResolvedPoint {
  country: string
  cca2: string
  cca3: string
  lat: number
  lon: number
  expo_count: number
  vendor_count: number
}

function resolvePoints(rows: CountryPoint[]): { resolved: ResolvedPoint[]; missed: string[] } {
  const out: ResolvedPoint[] = []
  const miss: string[] = []
  // Aggregate so multiple aliases collapse to one centroid.
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

async function initScene() {
  if (!containerRef.value) return
  // Dynamic imports keep the heavy WebGL bundle out of the initial route chunk.
  const [{ Scene, PolygonLayer, LineLayer }, { Map: L7Map }] = await Promise.all([
    import('@antv/l7'),
    import('@antv/l7-maps'),
  ])

  // Load and convert world atlas TopoJSON → GeoJSON FeatureCollection.
  const topoModule = (await import('world-atlas/countries-110m.json')) as unknown as
    | Topology
    | { default: Topology }
  const topo: Topology =
    'default' in topoModule && (topoModule as { default: Topology }).default
      ? (topoModule as { default: Topology }).default
      : (topoModule as Topology)
  const countriesFC = feature(
    topo,
    topo.objects.countries as GeometryCollection,
  ) as unknown as FeatureCollection

  const s = new Scene({
    id: containerId,
    map: new L7Map({
      center: [25, 18],
      pitch: 30,
      zoom: 1.2,
      minZoom: 0.5,
      maxZoom: 6,
    }),
  })
  s.setBgColor('#0c0e14')

  await new Promise<void>((resolve) => {
    s.once('loaded', () => resolve())
  })

  // Country fill — subdued so data layers pop.
  const polygonLayer = new PolygonLayer({})
    .source(countriesFC)
    .shape('fill')
    .color('#1a2030')
    .style({ opacity: 0.85 })

  // Country boundaries.
  const boundaryLayer = new LineLayer({ zIndex: 2 })
    .source(countriesFC)
    .shape('line')
    .color('#2c3548')
    .size(0.4)
    .style({ opacity: 0.7 })

  s.addLayer(polygonLayer)
  s.addLayer(boundaryLayer)
  layerRefs.push(polygonLayer, boundaryLayer)

  scene.value = s
  isReady.value = true
  // First paint with whatever data is currently available.
  applyDataLayers()
}

function disposeDataLayers() {
  if (!scene.value) return
  // Keep base polygon + boundary; remove only data-driven layers (rest of layerRefs).
  const s = scene.value as { removeLayer: (layer: unknown) => void }
  for (const layer of layerRefs.slice(2)) {
    try {
      s.removeLayer(layer)
    } catch {
      // ignore — layer may already be detached
    }
  }
  layerRefs = layerRefs.slice(0, 2)
}

async function applyDataLayers() {
  if (!isReady.value || !scene.value) return
  disposeDataLayers()

  const { resolved, missed } = resolvePoints(props.data ?? [])
  unmatched.value = Array.from(new Set(missed))

  if (resolved.length === 0) return

  const { PointLayer } = await import('@antv/l7')
  const s = scene.value as {
    addLayer: (layer: unknown) => void
  }

  // Normalize cylinder height by max vendor count so even small datasets look 3D.
  const maxVendor = Math.max(1, ...resolved.map((p) => p.vendor_count))
  const points = resolved.map((p) => ({
    ...p,
    cylinder_h: 60 + (p.vendor_count / maxVendor) * 240,
    pulse_size: 12 + (p.vendor_count / maxVendor) * 18,
    label: `${p.cca2} · ${p.vendor_count}`,
  }))

  const cylinder = new PointLayer({ depth: false, zIndex: 11 })
    .source(points, { parser: { type: 'json', x: 'lon', y: 'lat' } })
    .shape('cylinder')
    .size('cylinder_h', (h: number) => [3.2, 3.2, h])
    .color('vendor_count', (count: number) => {
      if (count >= 50) return '#ff5577'
      if (count >= 20) return '#ffaa33'
      if (count >= 5) return '#39ffaa'
      return '#39d8ff'
    })
    .active(true)
    .style({ opacity: 0.95, opacityLinear: { enable: true, dir: 'up' }, lightEnable: false })

  const pulse = new PointLayer({ zIndex: 10 })
    .source(points, { parser: { type: 'json', x: 'lon', y: 'lat' } })
    .shape('circle')
    .active(true)
    .animate(true)
    .size('pulse_size')
    .color('#39d8ff')

  const labels = new PointLayer({ zIndex: 12 })
    .source(points, { parser: { type: 'json', x: 'lon', y: 'lat' } })
    .shape('label', 'label')
    .size(11)
    .color('#e8eaed')
    .style({
      textAnchor: 'center',
      stroke: '#0c0e14',
      strokeWidth: 1.2,
      raisingHeight: 350000,
      textAllowOverlap: false,
      heightFixed: true,
    })

  s.addLayer(pulse)
  s.addLayer(cylinder)
  s.addLayer(labels)
  layerRefs.push(pulse, cylinder, labels)

  ;(cylinder as unknown as { on: (e: string, cb: (ev: unknown) => void) => void }).on(
    'click',
    (ev: unknown) => {
      const feat = (ev as { feature?: ResolvedPoint }).feature
      if (feat?.country) emit('pick', { country: feat.country, cca2: feat.cca2 })
    },
  )
}

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
      // ignore
    }
    scene.value = null
  }
  layerRefs = []
})
</script>

<template>
  <section
    class="relative flex h-[420px] w-full flex-col overflow-hidden border border-base-200 bg-[#0c0e14] dark:border-base-700"
  >
    <header
      class="absolute left-0 right-0 top-0 z-10 flex items-center justify-between border-b border-base-700/40 bg-[#0c0e14]/80 px-3 py-2 backdrop-blur-sm"
    >
      <div class="flex items-center gap-2">
        <span class="font-mono text-2xs uppercase tracking-ops text-base-500">MAP-01</span>
        <h2 class="font-mono text-2xs font-medium uppercase tracking-ops text-base-200">
          Distribusi Geografis Ekspo
        </h2>
      </div>
      <div class="flex items-center gap-2">
        <span class="font-mono text-2xs text-base-400">
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

    <div :id="containerId" ref="containerRef" class="absolute inset-0" />

    <footer
      v-if="!loading && (data?.length ?? 0) === 0"
      class="absolute inset-0 z-20 flex items-center justify-center"
    >
      <div
        class="border border-base-700/40 bg-[#0c0e14]/80 px-4 py-3 font-mono text-2xs uppercase tracking-ops text-base-400 backdrop-blur-sm"
      >
        Belum ada ekspo terindeks dengan field country.
      </div>
    </footer>

    <footer
      class="absolute bottom-0 left-0 right-0 z-10 flex items-center justify-between border-t border-base-700/40 bg-[#0c0e14]/80 px-3 py-1.5 backdrop-blur-sm"
    >
      <div class="flex items-center gap-3 font-mono text-2xs text-base-400">
        <span class="flex items-center gap-1">
          <span class="inline-block h-2 w-2 rounded-full bg-[#39d8ff]" />
          1-4 vendor
        </span>
        <span class="flex items-center gap-1">
          <span class="inline-block h-2 w-2 rounded-full bg-[#39ffaa]" />
          5-19
        </span>
        <span class="flex items-center gap-1">
          <span class="inline-block h-2 w-2 rounded-full bg-[#ffaa33]" />
          20-49
        </span>
        <span class="flex items-center gap-1">
          <span class="inline-block h-2 w-2 rounded-full bg-[#ff5577]" />
          50+
        </span>
      </div>
      <span class="font-mono text-2xs text-base-500">
        TINGGI BAR ∝ JUMLAH VENDOR
      </span>
    </footer>
  </section>
</template>
