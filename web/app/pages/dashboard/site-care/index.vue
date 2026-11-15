<template>
  <div class="flex min-h-full flex-col gap-6">
    <SiteCarePageHeader
      title="Mes prospects"
      :description="siteList?.summary_line ?? null"
      info-text="Des entreprises qui ont déjà un site. Chaque site est regardé de l’extérieur, comme un visiteur, et relu tous les sept jours. On écrit seulement quand un point mérite une correction."
    >
      <template v-if="siteList !== null" #action>
        <SiteCareButton
          v-if="siteList.writing_queue_label !== null"
          trailing-icon="i-lucide-arrow-right"
          :is-loading="isOpeningWritingQueue"
          @click="startWritingQueue"
        >
          {{ siteList.writing_queue_label }}
        </SiteCareButton>
        <SiteCareButton v-else :to="SITE_CARE_SEARCH_PATH" leading-icon="i-lucide-search">
          Nouvelle recherche
        </SiteCareButton>
      </template>
    </SiteCarePageHeader>

    <UiLoader v-if="siteList === null && isLoadingSites" label="Chargement des prospects…" />

    <UiEmptyState
      v-else-if="siteList === null"
      title="Chargement impossible"
      description="Les prospects n’ont pas pu être chargés. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="app-btn-secondary" @click="loadSites">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <template v-else>
      <div
        v-if="searchProgressLabel"
        class="flex flex-wrap items-center gap-x-5 gap-y-3 rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] px-5 py-4"
      >
        <UIcon
          name="i-lucide-loader-circle"
          class="h-5 w-5 shrink-0 animate-spin text-[var(--app-ink-soft)]"
          aria-hidden="true"
        />
        <p class="min-w-0 flex-[999_1_16rem] text-sm text-[var(--app-ink)]" role="status">
          {{ searchProgressLabel }}
        </p>
        <SiteCareButton variant="secondary" size="small" :is-loading="isStoppingSearch" @click="stopSearch">
          Arrêter la recherche
        </SiteCareButton>
      </div>
      <p v-else-if="lastSearchNote" class="text-sm text-[var(--app-ink-soft)]">{{ lastSearchNote }}</p>

      <UiEmptyState
        v-if="siteList.counts.total === 0"
        title="Aucun prospect pour le moment"
        description="Lancez une recherche : les entreprises qui ont déjà un site arrivent ici, avec ce qu’on a vu sur leur site."
      />

      <template v-else>
        <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-1">
          <div
            ref="tabRowElement"
            class="no-scrollbar flex touch-pan-x gap-1 overflow-x-auto overflow-y-hidden overscroll-x-contain"
            :class="tabRowEdgeFadeClass"
            role="group"
            aria-label="Trier les prospects"
          >
            <button
              v-for="tab in siteTabs"
              :key="tab.key"
              type="button"
              class="flex min-h-9 flex-1 shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm whitespace-nowrap transition-colors @lg:gap-2 @lg:px-3 pointer-coarse:min-h-11"
              :class="
                tab.key === activeTab
                  ? 'bg-[var(--app-btn-bg)] font-semibold text-[var(--app-btn-text)]'
                  : 'font-medium text-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]'
              "
              :aria-pressed="tab.key === activeTab"
              @click="selectTab(tab.key)"
            >
              {{ tab.label }}
              <span
                class="min-w-6 rounded-full px-2 py-px text-center text-xs font-semibold"
                :class="
                  tab.key === activeTab
                    ? 'bg-[color-mix(in_srgb,var(--app-btn-text)_18%,transparent)] text-[var(--app-btn-text)]'
                    : 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]'
                "
              >
                {{ tab.count }}
              </span>
            </button>
          </div>
        </div>

        <div class="flex flex-wrap gap-3">
          <div class="relative min-w-0 flex-[999_1_16rem]">
            <UIcon
              name="i-lucide-search"
              class="pointer-events-none absolute top-1/2 left-4 h-4 w-4 -translate-y-1/2 text-[var(--app-ink-soft)]"
              aria-hidden="true"
            />
            <input
              v-model="searchText"
              type="search"
              placeholder="Nom, ville, adresse du site"
              aria-label="Rechercher un prospect"
              class="app-input h-10 min-h-10 rounded-full pr-4 pl-11 text-sm pointer-coarse:min-h-11"
            />
          </div>
          <div class="min-w-0 flex-[1_1_14rem] @2xl:max-w-72">
            <UiSelectField
              v-model="issueKindFilter"
              :options="ISSUE_KIND_OPTIONS"
              aria-label="Filtrer par type de souci"
              class="h-10 min-h-10 rounded-full px-4 text-sm font-medium"
            />
          </div>
        </div>

        <div
          class="grid grid-cols-1 gap-4 transition-opacity @2xl:grid-cols-2 @5xl:grid-cols-3"
          :class="{ 'opacity-60': isLoadingSites }"
          :aria-busy="isLoadingSites"
        >
          <SiteCareSitePreviewCard v-for="listedSite in sites" :key="listedSite.id" :site="listedSite" />
        </div>

        <p
          v-if="sites.length === 0 && !isLoadingSites"
          class="rounded-2xl border border-dashed border-[var(--app-line)] p-8 text-center text-[var(--app-ink-soft)]"
        >
          Aucun prospect ne correspond à ce tri.
        </p>
        <p v-else-if="sites.length > 0" class="text-sm text-[var(--app-ink-soft)]">
          {{ SITE_CARE_SITE_TAB_HINTS[activeTab] }}
        </p>

        <div v-if="hasMoreSites" class="flex flex-wrap items-center justify-between gap-3">
          <p class="text-sm text-[var(--app-ink-soft)]">
            {{ sites.length }} prospects affichés sur {{ siteList.matching_count }}
          </p>
          <SiteCareButton variant="secondary" size="small" :is-loading="isLoadingMoreSites" @click="loadMoreSites">
            Afficher plus
          </SiteCareButton>
        </div>
      </template>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { LocationQueryRaw, LocationQueryValue } from 'vue-router'
import type { UseToastReturn } from '~/types/Composables'
import type { SelectFieldOption } from '~/types/SelectField'
import type { UseSiteCareWritingQueueReturn } from '../../../composables/useSiteCareWritingQueue'
import type { SiteCareSearch } from '../../../types/SiteCareSearch'
import type {
  SiteCareIssueKind,
  SiteCareIssueKindFilter,
  SiteCareSiteListItem,
  SiteCareSiteListQuery,
  SiteCareSiteListResponse,
  SiteCareSiteTab,
  SiteCareSiteTabCount,
  SiteCareSiteTabLabel,
} from '../../../types/SiteCareSite'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useSelectedTabReveal } from '~/composables/useSelectedTabReveal'
import { useTabRowEdgeFade } from '~/composables/useTabRowEdgeFade'
import { useToast } from '~/composables/useToast'
import { parseApiDate } from '~/utils/date'
import { useSiteCareWritingQueue } from '../../../composables/useSiteCareWritingQueue'
import {
  SITE_CARE_ISSUE_KIND_FILTERS,
  SITE_CARE_SITE_TAB_HINTS,
  SITE_CARE_SITE_TABS,
} from '../../../constants/siteCareLabels'
import {
  SITE_CARE_SEARCH_PATH,
  SITE_CARE_SITE_LIST_MAXIMUM_LIMIT,
  SITE_CARE_SITES_PATH,
  SITE_CARE_WRITING_QUEUE_QUERY,
} from '../../../constants/siteCareModule'
import { SiteCareService } from '../../../services/siteCareService'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Mes prospects · DevLeadHunter' })

const route: ReturnType<typeof useRoute> = useRoute()
const router: ReturnType<typeof useRouter> = useRouter()
const toast: UseToastReturn = useToast()
const { loadQueue }: UseSiteCareWritingQueueReturn = useSiteCareWritingQueue()

const ALL_KINDS_VALUE: string = 'all'

const DEFAULT_TAB: SiteCareSiteTab = 'to_write'

const SITE_PAGE_SIZE: number = 100

const SEARCH_TEXT_DEBOUNCE_MS: number = 300

const SEARCH_PROGRESS_REFRESH_INTERVAL_MS: number = 5000

const LAST_SEARCH_NOTE_LIFETIME_MS: number = 24 * 60 * 60 * 1000

const ISSUE_KIND_OPTIONS: SelectFieldOption[] = [
  { value: ALL_KINDS_VALUE, label: 'Tous les soucis' },
  ...SITE_CARE_ISSUE_KIND_FILTERS.map(
    (filter: SiteCareIssueKindFilter): SelectFieldOption => ({ value: filter.kind, label: filter.label }),
  ),
]

const siteList: Ref<SiteCareSiteListResponse | null> = ref(null)
const sites: Ref<SiteCareSiteListItem[]> = ref([])
const isLoadingSites: Ref<boolean> = ref(true)
const isLoadingMoreSites: Ref<boolean> = ref(false)
const activeTab: Ref<SiteCareSiteTab> = ref(parseSiteTab(firstQueryValue(route.query.tab)) ?? DEFAULT_TAB)
const issueKindFilter: Ref<string> = ref(parseIssueKind(firstQueryValue(route.query.kind)) ?? ALL_KINDS_VALUE)
const searchText: Ref<string> = ref('')
const appliedSearchText: Ref<string> = ref('')
const currentSearch: Ref<SiteCareSearch | null> = ref(null)
const isStoppingSearch: Ref<boolean> = ref(false)
const isOpeningWritingQueue: Ref<boolean> = ref(false)
const tabRowElement: Ref<HTMLElement | null> = useSelectedTabReveal(
  (): string => activeTab.value,
  '[aria-pressed="true"]',
)
const tabRowEdgeFadeClass: ComputedRef<string> = useTabRowEdgeFade(tabRowElement)

let latestSiteRequestNumber: number = 0
let searchTextTimer: ReturnType<typeof setTimeout> | null = null
let searchProgressTimer: ReturnType<typeof setTimeout> | null = null
let hasLeftPage: boolean = false

const siteTabs: ComputedRef<SiteCareSiteTabCount[]> = computed((): SiteCareSiteTabCount[] =>
  SITE_CARE_SITE_TABS.map(
    (tab: SiteCareSiteTabLabel): SiteCareSiteTabCount => ({
      key: tab.key,
      label: tab.label,
      count: siteList.value?.tab_counts[tab.key] ?? 0,
    }),
  ),
)

const hasMoreSites: ComputedRef<boolean> = computed(
  (): boolean => siteList.value !== null && siteList.value.matching_count > sites.value.length,
)

const isSearchRunning: ComputedRef<boolean> = computed(
  (): boolean => currentSearch.value?.status === 'pending' || currentSearch.value?.status === 'running',
)

const searchProgressLabel: ComputedRef<string | null> = computed((): string | null => {
  const search: SiteCareSearch | null = currentSearch.value
  if (search === null || !isSearchRunning.value) {
    return null
  }
  return `Recherche en cours · ${search.zone_label} · ${search.progress_label}`
})

const lastSearchNote: ComputedRef<string | null> = computed((): string | null => {
  const search: SiteCareSearch | null = currentSearch.value
  if (search === null || isSearchRunning.value || search.note === null) {
    return null
  }
  const endedAt: number = parseApiDate(search.completed_at ?? search.created_at).getTime()
  return Date.now() - endedAt < LAST_SEARCH_NOTE_LIFETIME_MS ? search.note : null
})

/**
 * Read one value of the address query, whatever its shape.
 * @param value - The raw query value.
 * @returns Its first value, or null when the address does not carry it.
 */
function firstQueryValue(value: LocationQueryValue | LocationQueryValue[] | undefined): string | null {
  const firstValue: LocationQueryValue | undefined = Array.isArray(value) ? value[0] : value
  return firstValue ?? null
}

/**
 * Read a tab of the list from a raw value; `all` is accepted, the watch's links open it.
 * @param value - The value to read.
 * @returns The tab, or null when the value names none.
 */
function parseSiteTab(value: string | null): SiteCareSiteTab | null {
  if (value === 'all') {
    return 'all'
  }
  return SITE_CARE_SITE_TABS.find((tab: SiteCareSiteTabLabel): boolean => tab.key === value)?.key ?? null
}

/**
 * Read a type of issue from a raw value.
 * @param value - The value to read.
 * @returns The type of issue, or null when the value names none (« all » included).
 */
function parseIssueKind(value: string | null): SiteCareIssueKind | null {
  return (
    SITE_CARE_ISSUE_KIND_FILTERS.find((filter: SiteCareIssueKindFilter): boolean => filter.kind === value)?.kind ?? null
  )
}

/**
 * Read a site identifier from a raw value.
 * @param value - The value to read.
 * @returns The identifier, or null when the value is not one.
 */
function parseSiteId(value: string | null): number | null {
  const siteId: number = Number(value)
  return value !== null && Number.isInteger(siteId) && siteId > 0 ? siteId : null
}

/**
 * The query of the list for the tab and filters on screen.
 * @param limit - How many rows to ask.
 * @param offset - How many rows to skip.
 * @returns The query to send.
 */
function siteListQuery(limit: number, offset: number): SiteCareSiteListQuery {
  return {
    tab: activeTab.value,
    trade: null,
    kind: parseIssueKind(issueKindFilter.value),
    q: appliedSearchText.value === '' ? null : appliedSearchText.value,
    limit,
    offset,
  }
}

/**
 * Show an answer of the API: its counts and its rows replace the ones on screen.
 * @param response - The answer to show.
 */
function showSiteList(response: SiteCareSiteListResponse): void {
  siteList.value = response
  sites.value = response.sites
}

/**
 * Load the first rows of the tab and filters on screen.
 * @returns A promise resolved once the rows are shown, or the failure is.
 */
async function loadSites(): Promise<void> {
  latestSiteRequestNumber += 1
  const requestNumber: number = latestSiteRequestNumber
  isLoadingSites.value = true
  try {
    const response: SiteCareSiteListResponse = await SiteCareService.listSites(siteListQuery(SITE_PAGE_SIZE, 0))
    if (requestNumber === latestSiteRequestNumber) {
      showSiteList(response)
    }
  } catch {
    if (requestNumber === latestSiteRequestNumber && siteList.value !== null) {
      toast.error('Les prospects n’ont pas pu être chargés.')
    }
  } finally {
    if (requestNumber === latestSiteRequestNumber) {
      isLoadingSites.value = false
    }
  }
}

/**
 * Read again the rows on screen and the counts, without a loader, while a search brings new prospects.
 * @returns A promise resolved once the list is up to date; a failure leaves the list as it is.
 */
async function refreshSites(): Promise<void> {
  if (siteList.value === null || isLoadingSites.value || isLoadingMoreSites.value) {
    return
  }
  latestSiteRequestNumber += 1
  const requestNumber: number = latestSiteRequestNumber
  const shownSiteCount: number = Math.min(
    Math.max(sites.value.length, SITE_PAGE_SIZE),
    SITE_CARE_SITE_LIST_MAXIMUM_LIMIT,
  )
  try {
    const response: SiteCareSiteListResponse = await SiteCareService.listSites(siteListQuery(shownSiteCount, 0))
    if (requestNumber === latestSiteRequestNumber) {
      showSiteList(response)
    }
  } catch {
    // The list on screen stays: the next refresh reads it again.
  }
}

/**
 * Add the next rows under the ones on screen.
 * @returns A promise resolved once the rows are added, or the failure is shown.
 */
async function loadMoreSites(): Promise<void> {
  if (isLoadingSites.value || isLoadingMoreSites.value) {
    return
  }
  latestSiteRequestNumber += 1
  const requestNumber: number = latestSiteRequestNumber
  isLoadingMoreSites.value = true
  try {
    const response: SiteCareSiteListResponse = await SiteCareService.listSites(
      siteListQuery(SITE_PAGE_SIZE, sites.value.length),
    )
    if (requestNumber !== latestSiteRequestNumber) {
      return
    }
    const shownSiteIds: Set<number> = new Set(
      sites.value.map((shownSite: SiteCareSiteListItem): number => shownSite.id),
    )
    siteList.value = response
    sites.value = [
      ...sites.value,
      ...response.sites.filter((addedSite: SiteCareSiteListItem): boolean => !shownSiteIds.has(addedSite.id)),
    ]
  } catch {
    toast.error('Les prospects suivants n’ont pas pu être chargés.')
  } finally {
    isLoadingMoreSites.value = false
  }
}

/**
 * Switch the list to another tab.
 * @param tab - The tab clicked.
 */
function selectTab(tab: SiteCareSiteTab): void {
  activeTab.value = tab
}

/** Keep the tab and the type of issue in the address, so coming back from a site lands on the same list. */
function writeFiltersInAddress(): void {
  const query: LocationQueryRaw = {}
  if (activeTab.value !== DEFAULT_TAB) {
    query.tab = activeTab.value
  }
  const issueKind: SiteCareIssueKind | null = parseIssueKind(issueKindFilter.value)
  if (issueKind !== null) {
    query.kind = issueKind
  }
  router.replace({ query })
}

/**
 * Start « Traiter les sites »: queue the sites of « À écrire » in their order, then open the first.
 * @returns A promise resolved once the first site's page is opened, or the failure is shown.
 */
async function startWritingQueue(): Promise<void> {
  isOpeningWritingQueue.value = true
  try {
    const queuedSiteIds: number[] = await loadQueue()
    const firstSiteId: number | undefined = queuedSiteIds[0]
    if (firstSiteId === undefined) {
      toast.info('Plus aucun site n’attend de message.')
      await loadSites()
      return
    }
    await navigateTo({ path: `${SITE_CARE_SITES_PATH}/${firstSiteId}`, query: SITE_CARE_WRITING_QUEUE_QUERY })
  } catch {
    toast.error('Les sites à écrire n’ont pas pu être chargés.')
  } finally {
    isOpeningWritingQueue.value = false
  }
}

/**
 * Read the search under way, else the last one.
 * @returns A promise resolved once read; a failure keeps the last known state.
 */
async function refreshSearchProgress(): Promise<void> {
  try {
    currentSearch.value = await SiteCareService.getCurrentSearch()
  } catch {
    // The progress line keeps its last figures: the next refresh reads them again.
  }
}

/**
 * Stop the search under way: what it already brought stays in the list, which is read again.
 * @returns A promise resolved once the search is stopped, or the failure is shown; a failure leaves it running.
 */
async function stopSearch(): Promise<void> {
  isStoppingSearch.value = true
  try {
    currentSearch.value = await SiteCareService.stopCurrentSearch()
    stopSearchProgressRefresh()
    await refreshSites()
  } catch {
    toast.error('La recherche n’a pas pu être arrêtée.')
  } finally {
    isStoppingSearch.value = false
  }
}

/** Stop reading the search progress. */
function stopSearchProgressRefresh(): void {
  if (searchProgressTimer !== null) {
    clearTimeout(searchProgressTimer)
    searchProgressTimer = null
  }
}

/** Read the search progress and the list again in a few seconds, and so on until the search ends. */
function scheduleSearchProgressRefresh(): void {
  stopSearchProgressRefresh()
  searchProgressTimer = setTimeout(async (): Promise<void> => {
    await Promise.all([refreshSearchProgress(), refreshSites()])
    if (hasLeftPage) {
      return
    }
    if (isSearchRunning.value) {
      scheduleSearchProgressRefresh()
      return
    }
    // The search just ended: its last prospects may have arrived after the list was read.
    await refreshSites()
  }, SEARCH_PROGRESS_REFRESH_INTERVAL_MS)
}

watch(
  (): string => searchText.value,
  (typedText: string): void => {
    if (searchTextTimer !== null) {
      clearTimeout(searchTextTimer)
    }
    searchTextTimer = setTimeout((): void => {
      appliedSearchText.value = typedText.trim()
    }, SEARCH_TEXT_DEBOUNCE_MS)
  },
)

watch(
  (): string => [activeTab.value, issueKindFilter.value, appliedSearchText.value].join('\n'),
  (): void => {
    writeFiltersInAddress()
    loadSites()
  },
)

onMounted(async (): Promise<void> => {
  const siteIdOfOldSheetLink: number | null = parseSiteId(firstQueryValue(route.query.site))
  if (siteIdOfOldSheetLink !== null) {
    await navigateTo(`${SITE_CARE_SITES_PATH}/${siteIdOfOldSheetLink}`, { replace: true })
    return
  }
  await Promise.all([loadSites(), refreshSearchProgress()])
  if (!hasLeftPage && isSearchRunning.value) {
    scheduleSearchProgressRefresh()
  }
})

onBeforeUnmount((): void => {
  hasLeftPage = true
  stopSearchProgressRefresh()
  if (searchTextTimer !== null) {
    clearTimeout(searchTextTimer)
  }
})
</script>
