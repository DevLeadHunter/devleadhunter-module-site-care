<template>
  <SiteCareProspectPage
    v-if="page"
    :page="page"
    @reply-click="sendPageBeacon('site_care_page_reply_clicked')"
    @forward-click="sendPageBeacon('site_care_page_forward_clicked')"
  />
  <main
    v-else
    class="font-site-care text-site-care-ink flex min-h-dvh items-center justify-center bg-white px-6 text-center text-[17px] leading-7 antialiased"
  >
    <p v-if="isLoadingPage" class="text-site-care-ink-soft">Chargement…</p>
    <h1 v-else class="text-2xl leading-[1.15] font-medium tracking-[-0.01em] text-balance">
      Cette page n’existe plus.
    </h1>
  </main>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { SiteCarePageBeaconEvent } from '../../types/SiteCarePageBeaconEvent'
import type { SiteCarePublicPage } from '../../types/SiteCarePublicPage'
import { computed, onMounted, ref } from 'vue'
import SiteCareProspectPage from '../../components/SiteCareProspectPage.vue'
import { ApiRefusalUtils } from '~/utils/ApiRefusalUtils'
import { DemoBeaconUtils } from '~/utils/DemoBeaconUtils'

const PAGE_NOT_FOUND_STATUS: number = 404

const route: ReturnType<typeof useRoute> = useRoute()
const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

const {
  data: page,
  pending,
  error: loadError,
  refresh,
}: Awaited<ReturnType<typeof useAsyncData<SiteCarePublicPage | null>>> = await useAsyncData(
  (): string => `site-care-page-${routeSlug()}`,
  fetchPage,
)

const hasBrowserRetriedFailedLoad: Ref<boolean> = ref(false)

const isAwaitingBrowserRetry: ComputedRef<boolean> = computed(
  (): boolean => Boolean(loadError.value) && !hasBrowserRetriedFailedLoad.value,
)

const isLoadingPage: ComputedRef<boolean> = computed((): boolean => pending.value || isAwaitingBrowserRetry.value)

const pageTitle: ComputedRef<string> = computed((): string => {
  if (page.value) {
    return `${page.value.business_name} : ce que j’ai vu sur votre site`
  }

  return isLoadingPage.value ? 'Chargement…' : 'Cette page n’existe plus'
})

/**
 * The page's slug, as the address names it.
 * @returns The slug.
 */
function routeSlug(): string {
  return String(route.params.slug ?? '')
}

/**
 * The DevLeadHunter API the page reads and beacons to.
 * @returns The API base URL.
 */
function apiBase(): string {
  return String(config.public.apiBase ?? '')
}

/**
 * Read the page from the module's public endpoint.
 * @returns The page as the API wrote it, or null when the API has no page under this slug.
 * @throws The `$fetch` error of any failure other than an unknown page, for the browser to try again.
 */
async function fetchPage(): Promise<SiteCarePublicPage | null> {
  try {
    return await $fetch<SiteCarePublicPage>(
      `${apiBase()}/api/v1/site-care/public/pages/${encodeURIComponent(routeSlug())}`,
    )
  } catch (error: unknown) {
    if (ApiRefusalUtils.status(error) === PAGE_NOT_FOUND_STATUS) {
      return null
    }

    throw error
  }
}

/**
 * Load the page once more from the visitor's browser when the server could not reach the API.
 */
async function retryLoadFailedOnServer(): Promise<void> {
  if (!loadError.value) {
    return
  }

  await refresh()
  hasBrowserRetriedFailedLoad.value = true
}

/**
 * Whether the visit is the prospect's own: never the owner's tagged visit nor a preview framed by the dashboard.
 * @returns True when the visit may be reported.
 */
function isProspectVisit(): boolean {
  return !DemoBeaconUtils.isInternalVisit() && window.self === window.top
}

/**
 * Beacon one of the page's events to the API, for a prospect's visit of a page that exists.
 * @param event - The event to report.
 */
function sendPageBeacon(event: SiteCarePageBeaconEvent): void {
  if (!page.value || !isProspectVisit()) {
    return
  }

  DemoBeaconUtils.send(apiBase(), routeSlug(), event)
}

onMounted(async (): Promise<void> => {
  await retryLoadFailedOnServer()
  sendPageBeacon('site_care_page_opened')
})

useHead({
  htmlAttrs: { lang: 'fr' },
})

useSeoMeta({
  title: (): string => pageTitle.value,
  robots: 'noindex, nofollow',
})
</script>

<style src="../../assets/css/site-care-page.css"></style>
