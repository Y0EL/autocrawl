<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { feature } from 'topojson-client'
import countriesTopo from 'world-atlas/countries-110m.json'
import landTopo from 'world-atlas/land-110m.json'
import { api } from '@/api/client'
import { resolveCountry } from '@/data/country_resolver'
import type { ExpoCountryStat } from '@/api/types'
import LivingSystemPanel from './LivingSystemPanel.vue'

/**
 * Autocrawl world map — global expo distribution heatmap.
 *
 *   - Renderer: MapLibre GL (WebGL).
 *   - Base map: 100% LOCAL `world-atlas` TopoJSON converted to GeoJSON.
 *     No tile server, no external dependency, no watermark possible.
 *   - Visualization: native MapLibre heatmap layer fed entirely by real
 *     `/stats/expo-countries` data (no synthesis). At high zoom the
 *     heatmap fades and individual country circles take over so the
 *     reader can land on a single point and click for detail.
 *   - Hit-test: invisible circle layer on top, hover → paper popup,
 *     click → /expos?country=…
 *   - LivingSystemPanel docked top-right surfaces the orchestrator's
 *     real-time pulse.
 */

const router = useRouter()

const expoCountries = useQuery({
  queryKey: ['stats', 'expo-countries'],
  queryFn: api.stats.expoCountries,
  refetchInterval: 60_000,
})

interface CountryPoint {
  iso2: string
  name: string
  lat: number
  lon: number
  expos: number
  vendors: number
}

const points = computed<CountryPoint[]>(() => {
  const rows = (expoCountries.data.value ?? []) as ExpoCountryStat[]
  const out: CountryPoint[] = []
  for (const r of rows) {
    const rec = resolveCountry(r.country)
    if (!rec) continue
    out.push({
      iso2: rec.cca2,
      name: rec.name,
      lat: rec.lat,
      lon: rec.lon,
      expos: r.expo_count ?? 0,
      vendors: r.vendor_count ?? 0,
    })
  }
  out.sort((a, b) => b.expos - a.expos)
  return out
})

const mapEl = ref<HTMLDivElement | null>(null)
let map: maplibregl.Map | null = null
let popup: maplibregl.Popup | null = null

/* ------------------------------------------------------------------ */
/* GeoJSON sources                                                      */
/* ------------------------------------------------------------------ */

const countriesGeoJson = (() => {
  const fc = feature(
    countriesTopo as unknown as Parameters<typeof feature>[0],
    (countriesTopo as unknown as { objects: Record<string, unknown> }).objects.countries as Parameters<typeof feature>[1],
  )
  return fc as GeoJSON.FeatureCollection
})()

const landGeoJson = (() => {
  const fc = feature(
    landTopo as unknown as Parameters<typeof feature>[0],
    (landTopo as unknown as { objects: Record<string, unknown> }).objects.land as Parameters<typeof feature>[1],
  )
  return ('features' in (fc as object))
    ? (fc as GeoJSON.FeatureCollection)
    : ({ type: 'FeatureCollection', features: [fc as GeoJSON.Feature] } as GeoJSON.FeatureCollection)
})()

function expoFeatureCollection(): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: points.value.map((p) => ({
      type: 'Feature',
      properties: {
        iso2: p.iso2,
        name: p.name,
        expos: p.expos,
        vendors: p.vendors,
      },
      geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
    })),
  }
}

/* ------------------------------------------------------------------ */
/* MapLibre setup                                                      */
/* ------------------------------------------------------------------ */

function refreshExpoSource() {
  if (!map) return
  const src = map.getSource('expoPoints') as maplibregl.GeoJSONSource | undefined
  if (src) src.setData(expoFeatureCollection())
}

function popupHtml(p: CountryPoint): string {
  const escape = (s: string) => s.replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] ?? c
  ))
  return `
    <div class="autocrawl-paper-popup">
      <div class="popup-name">${escape(p.name)}</div>
      <div class="popup-stats">
        <div>
          <span class="popup-num">${p.expos.toLocaleString()}</span>
          <span class="popup-label">Ekspo</span>
        </div>
        <div>
          <span class="popup-num">${p.vendors.toLocaleString()}</span>
          <span class="popup-label">Vendor</span>
        </div>
      </div>
    </div>`
}

onMounted(() => {
  if (!mapEl.value) return

  map = new maplibregl.Map({
    container: mapEl.value,
    style: {
      version: 8,
      sources: {
        land:       { type: 'geojson', data: landGeoJson },
        countries:  { type: 'geojson', data: countriesGeoJson },
        expoPoints: { type: 'geojson', data: expoFeatureCollection() },
      },
      layers: [
        {
          id: 'background',
          type: 'background',
          paint: { 'background-color': '#F4EFE6' },
        },
        {
          id: 'land-fill',
          type: 'fill',
          source: 'land',
          paint: {
            'fill-color': '#ECE5D8',
            'fill-opacity': 0.95,
          },
        },
        {
          id: 'country-borders',
          type: 'line',
          source: 'countries',
          paint: {
            'line-color': '#141210',
            'line-width': 0.4,
            'line-opacity': 0.32,
          },
        },

        /* ---------- Heatmap layer — driven by real expo counts ---------- */
        {
          id: 'expo-heatmap',
          type: 'heatmap',
          source: 'expoPoints',
          maxzoom: 5,
          paint: {
            /* Per-feature weight: log-ish curve so a country with 1 expo
             * is still visible while 1000 doesn't dominate the planet. */
            'heatmap-weight': [
              'interpolate', ['linear'], ['get', 'expos'],
              0,    0,
              1,    0.35,
              10,   0.65,
              100,  0.95,
              1000, 1.25,
            ],
            'heatmap-intensity': [
              'interpolate', ['linear'], ['zoom'],
              0, 0.9,
              5, 2.4,
            ],
            /* Color ramp: transparent → faint ink-teal → ink-teal hot →
             * vermilion. The first stop MUST be fully transparent for
             * the heatmap algorithm to work correctly. */
            'heatmap-color': [
              'interpolate', ['linear'], ['heatmap-density'],
              0,    'rgba(255, 255, 255, 0)',
              0.10, 'rgba(16, 48, 46, 0.18)',
              0.30, 'rgba(16, 48, 46, 0.50)',
              0.55, 'rgba(82, 36, 28, 0.68)',
              0.80, 'rgba(181, 50, 26, 0.82)',
              1.00, 'rgba(181, 50, 26, 0.94)',
            ],
            'heatmap-radius': [
              'interpolate', ['linear'], ['zoom'],
              0, 16,
              3, 30,
              5, 56,
            ],
            'heatmap-opacity': [
              'interpolate', ['linear'], ['zoom'],
              0, 0.95,
              4, 0.9,
              5, 0.5,
            ],
          },
        },

        /* ---------- Country circles (fade in at high zoom) ---------- */
        {
          id: 'expo-circles',
          type: 'circle',
          source: 'expoPoints',
          minzoom: 3.5,
          paint: {
            'circle-radius': [
              'interpolate', ['linear'], ['get', 'expos'],
              0,    3,
              10,   6,
              100,  10,
              1000, 18,
            ],
            'circle-color': [
              'interpolate', ['linear'], ['get', 'expos'],
              0,   '#10302E',
              50,  '#52241C',
              500, '#B5321A',
            ],
            'circle-opacity': [
              'interpolate', ['linear'], ['zoom'],
              3.5, 0,
              5,   0.92,
            ],
            'circle-stroke-color': '#F4EFE6',
            'circle-stroke-width': 1.4,
          },
        },

        /* ---------- Invisible hit-test layer for hover/click ---------- */
        {
          id: 'expo-hit',
          type: 'circle',
          source: 'expoPoints',
          paint: {
            'circle-radius': [
              'interpolate', ['linear'], ['get', 'expos'],
              0, 14,
              10, 18,
              100, 26,
              1000, 38,
            ],
            'circle-color': '#000000',
            'circle-opacity': 0.001,
          },
        },
      ],
    },
    center: [12, 22],
    zoom: 1.4,
    minZoom: 0.5,
    maxZoom: 6,
    pitch: 0,
    bearing: 0,
    attributionControl: false,
    dragRotate: false,
    pitchWithRotate: false,
    touchPitch: false,
  })

  map.addControl(new maplibregl.NavigationControl({
    showZoom: true,
    showCompass: false,
    visualizePitch: false,
  }), 'bottom-right')

  popup = new maplibregl.Popup({
    closeButton: false,
    closeOnClick: false,
    className: 'autocrawl-popup',
    offset: 14,
  })

  map.on('mouseenter', 'expo-hit', (e) => {
    if (!map || !e.features?.[0]) return
    map.getCanvas().style.cursor = 'pointer'
    const props = e.features[0].properties as { name: string; expos: number; vendors: number; iso2: string }
    const point: CountryPoint = {
      iso2: props.iso2, name: props.name,
      expos: Number(props.expos), vendors: Number(props.vendors),
      lat: 0, lon: 0,
    }
    const coords = (e.features[0].geometry as GeoJSON.Point).coordinates as [number, number]
    popup?.setLngLat(coords).setHTML(popupHtml(point)).addTo(map)
  })
  map.on('mouseleave', 'expo-hit', () => {
    if (!map) return
    map.getCanvas().style.cursor = ''
    popup?.remove()
  })
  map.on('click', 'expo-hit', (e) => {
    const country = (e.features?.[0]?.properties as { name?: string } | undefined)?.name
    if (country) router.push({ path: '/expos', query: { country } })
  })
})

watch(points, () => {
  refreshExpoSource()
})

onBeforeUnmount(() => {
  popup?.remove()
  popup = null
  map?.remove()
  map = null
})

const isLoading = computed(() => expoCountries.isPending.value)
const totalCountries = computed(() => points.value.length)
const totalExpos = computed(() =>
  points.value.reduce((s, p) => s + p.expos, 0),
)
const totalVendors = computed(() =>
  points.value.reduce((s, p) => s + p.vendors, 0),
)
</script>

<template>
  <div class="autocrawl-map relative w-full h-full select-none overflow-hidden">
    <div ref="mapEl" class="absolute inset-0 w-full h-full" />

    <div class="absolute left-5 top-4 z-[400] flex flex-col pointer-events-none bg-paper/85 backdrop-blur-sm pl-1 pr-3 py-1">
      <span class="label">Peta · Sebaran Ekspo</span>
      <span class="display text-[1.5rem] leading-tight mt-0.5">Heatmap Global</span>
    </div>

    <!-- Living System Panel — real-time orchestrator pulse -->
    <div class="absolute right-5 top-4 z-[400] pointer-events-auto">
      <LivingSystemPanel />
    </div>

    <!-- Heatmap legend -->
    <div class="absolute left-5 bottom-4 z-[400] flex flex-col gap-1.5 bg-paper/85 backdrop-blur-sm px-3 py-2 rule pointer-events-none">
      <div class="flex items-baseline gap-3">
        <div class="flex items-baseline gap-1.5">
          <span class="num-display text-[1rem]">{{ totalExpos.toLocaleString() }}</span>
          <span class="label">Ekspo</span>
        </div>
        <div class="flex items-baseline gap-1.5">
          <span class="num-display text-[1rem]">{{ totalCountries }}</span>
          <span class="label">Negara</span>
        </div>
        <div class="flex items-baseline gap-1.5">
          <span class="num-display text-[1rem]">{{ totalVendors.toLocaleString() }}</span>
          <span class="label">Vendor</span>
        </div>
      </div>
      <!-- Color scale -->
      <div class="flex items-center gap-2 mt-1">
        <span class="label-mono text-[0.625rem]">Densitas</span>
        <div class="legend-bar h-[6px] w-32" />
        <span class="label-mono text-[0.625rem]">Tinggi</span>
      </div>
    </div>

    <div
      v-if="isLoading"
      class="absolute inset-0 flex items-center justify-center pointer-events-none z-[500]"
    >
      <span class="label bg-paper px-3 py-1 rule">Memuat peta…</span>
    </div>
  </div>
</template>

<style>
.autocrawl-map .maplibregl-canvas { outline: none; }
.autocrawl-map .maplibregl-ctrl-attrib,
.autocrawl-map .maplibregl-ctrl-bottom-left .maplibregl-ctrl-attrib,
.autocrawl-map .maplibregl-ctrl-logo { display: none !important; }

.autocrawl-map .legend-bar {
  background: linear-gradient(
    to right,
    rgba(16, 48, 46, 0.18) 0%,
    rgba(16, 48, 46, 0.50) 30%,
    rgba(82, 36, 28, 0.68) 55%,
    rgba(181, 50, 26, 0.82) 80%,
    rgba(181, 50, 26, 0.94) 100%
  );
  border: 1px solid rgba(20, 18, 16, 0.18);
}

/* Navigation control (zoom +/−) — paper themed. */
.autocrawl-map .maplibregl-ctrl-group {
  background: rgb(244 239 230) !important;
  border: 1px solid rgba(20, 18, 16, 0.28) !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  margin: 16px !important;
}
.autocrawl-map .maplibregl-ctrl-group button {
  width: 28px !important;
  height: 28px !important;
  background-color: rgb(244 239 230) !important;
  border-radius: 0 !important;
  border: 0 !important;
  border-bottom: 1px solid rgba(20, 18, 16, 0.18) !important;
}
.autocrawl-map .maplibregl-ctrl-group button:last-child { border-bottom: 0 !important; }
.autocrawl-map .maplibregl-ctrl-group button:hover {
  background-color: rgb(236 229 216) !important;
}
.autocrawl-map .maplibregl-ctrl-group button .maplibregl-ctrl-icon {
  filter: invert(8%) sepia(8%) saturate(414%) hue-rotate(2deg) brightness(95%);
}

/* Popup — paper, hairline, editorial type */
.autocrawl-map .autocrawl-popup .maplibregl-popup-content {
  background: rgb(244 239 230) !important;
  color: rgb(20 18 16) !important;
  border: 1px solid rgba(20, 18, 16, 0.28) !important;
  border-radius: 0 !important;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10) !important;
  padding: 12px 14px !important;
  min-width: 180px !important;
}
.autocrawl-map .autocrawl-popup .maplibregl-popup-tip { display: none !important; }

.autocrawl-map .autocrawl-paper-popup .popup-name {
  font-family: 'Newsreader Variable', Newsreader, Georgia, serif;
  font-weight: 500;
  font-size: 17px;
  letter-spacing: -0.012em;
  line-height: 1.05;
  color: rgb(20 18 16);
  font-variation-settings: 'opsz' 36;
}
.autocrawl-map .autocrawl-paper-popup .popup-stats {
  display: flex;
  gap: 18px;
  margin-top: 8px;
  align-items: baseline;
}
.autocrawl-map .autocrawl-paper-popup .popup-num {
  font-family: 'Newsreader Variable', Newsreader, Georgia, serif;
  font-feature-settings: 'tnum', 'lnum';
  font-variant-numeric: tabular-nums lining-nums;
  font-size: 22px;
  font-weight: 500;
  letter-spacing: -0.01em;
  color: rgb(20 18 16);
  margin-right: 4px;
  font-variation-settings: 'opsz' 60;
}
.autocrawl-map .autocrawl-paper-popup .popup-label {
  font-family: 'Newsreader Variable', Newsreader, Georgia, serif;
  font-variant-caps: all-small-caps;
  font-feature-settings: 'smcp', 'c2sc';
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: rgb(122 113 103);
}
</style>
