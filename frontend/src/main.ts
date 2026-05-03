import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { VueQueryPlugin } from '@tanstack/vue-query'
import router from '@/router'
import App from '@/App.vue'
import '@/styles/main.css'

async function bootstrap() {
  if (import.meta.env.DEV && import.meta.env.VITE_USE_MOCKS === 'true') {
    const { startMocks } = await import('@/mocks/start')
    await startMocks()
  }

  const app = createApp(App)
  app.use(createPinia())
  app.use(router)
  app.use(VueQueryPlugin)
  app.mount('#app')
}

bootstrap()
