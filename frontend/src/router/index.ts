import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'atlas',
      component: () => import('@/views/AtlasPage.vue'),
    },
    {
      path: '/vendors',
      name: 'vendors',
      component: () => import('@/views/VendorsListPage.vue'),
    },
    {
      path: '/vendors/:domain',
      name: 'vendor-detail',
      component: () => import('@/views/VendorDetailPage.vue'),
      props: true,
    },
    {
      path: '/expos',
      name: 'expos',
      component: () => import('@/views/ExposListPage.vue'),
    },
    {
      path: '/expos/:expoId',
      name: 'expo-detail',
      component: () => import('@/views/ExpoDetailPage.vue'),
      props: true,
    },
    {
      path: '/pdfs',
      name: 'pdfs',
      component: () => import('@/views/PdfsListPage.vue'),
    },
    {
      path: '/runs',
      name: 'runs',
      component: () => import('@/views/RunsListPage.vue'),
    },
    {
      path: '/diagnostik',
      name: 'diagnostik',
      component: () => import('@/views/DiagnosticsPage.vue'),
    },
    {
      path: '/orkestrator',
      name: 'orkestrator',
      component: () => import('@/views/OrchestratorProgressPage.vue'),
    },
    {
      path: '/konfigurasi',
      name: 'konfigurasi',
      component: () => import('@/views/ConfigurationPage.vue'),
    },
    {
      path: '/labs',
      name: 'labs',
      component: () => import('@/views/LabsPage.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundPage.vue'),
    },
  ],
})

export default router
