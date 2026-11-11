import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

/** Site care layer of the dashboard: `~/` is the core here, so module files import each other relatively. */
const layerDirectory: string = dirname(fileURLToPath(import.meta.url))

// No import of `defineNuxtConfig`: Nuxt provides it while it loads a layer, which has no node_modules of its own.
export default defineNuxtConfig({
  $meta: {
    name: 'site-care',
  },

  // Absolute paths: in a layer, `~/components` is the host app's folder, never this one. Same prefixes as the core.
  components: [
    {
      path: join(layerDirectory, 'app/components/ui'),
      prefix: 'Ui',
    },
    {
      path: join(layerDirectory, 'app/components'),
      pathPrefix: false,
      ignore: ['**/ui/**'],
    },
  ],
})
