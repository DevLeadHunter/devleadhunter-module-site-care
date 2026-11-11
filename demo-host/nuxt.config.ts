import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const currentDir: string = dirname(fileURLToPath(import.meta.url))

export default defineNuxtConfig({
  $meta: {
    name: 'devleadhunter-module-site-care',
  },

  components: [
    {
      path: join(currentDir, './app/components'),
      pathPrefix: false,
    },
  ],
})
