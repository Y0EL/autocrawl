<script setup lang="ts">
import AtlasMap from '@/components/atlas/AtlasMap.vue'
import AiInsightsCard from '@/components/atlas/AiInsightsCard.vue'
import TopIndustriesCard from '@/components/atlas/TopIndustriesCard.vue'
import LiveExhibitorFeed from '@/components/atlas/LiveExhibitorFeed.vue'
import IndustryDonut from '@/components/atlas/IndustryDonut.vue'
import QuickActionsList from '@/components/atlas/QuickActionsList.vue'
</script>

<template>
  <div class="atlas-canvas px-6 pt-4 pb-10">
    <!-- Row 1: hero map + right column (insights + industries) -->
    <div class="grid grid-cols-12 gap-4">
      <!-- Hero map: 8 cols × ~540px -->
      <section class="col-span-12 lg:col-span-8 card relative" style="height: 540px;">
        <AtlasMap />
      </section>

      <!-- Right column: insights stacked above industries -->
      <aside class="col-span-12 lg:col-span-4 flex flex-col gap-4">
        <AiInsightsCard />
        <TopIndustriesCard />
      </aside>
    </div>

    <!-- Row 2: live feed + donut + quick actions -->
    <div class="mt-4 grid grid-cols-12 gap-4">
      <section class="col-span-12 lg:col-span-6">
        <LiveExhibitorFeed />
      </section>
      <section class="col-span-12 md:col-span-6 lg:col-span-3">
        <IndustryDonut />
      </section>
      <section class="col-span-12 md:col-span-6 lg:col-span-3">
        <QuickActionsList />
      </section>
    </div>
  </div>
</template>
