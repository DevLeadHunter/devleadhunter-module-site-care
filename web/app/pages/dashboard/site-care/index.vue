<template>
  <div class="flex min-h-full flex-col gap-6">
    <UiPageHeader
      eyebrow="Entretien de sites"
      :has-eyebrow-mark="false"
      title="Mes prospects"
      description="Des entreprises qui ont déjà un site. Chaque site est regardé de l’extérieur, comme un visiteur. On écrit seulement quand un point mérite une correction."
    >
      <template #primary-action>
        <NuxtLink :to="SITE_CARE_SEARCH_PATH" class="btn-primary">
          <UIcon name="i-lucide-plus" class="h-4 w-4" />
          Nouvelle recherche
        </NuxtLink>
      </template>
    </UiPageHeader>

    <UiLoader v-if="siteList === null && isLoadingSites" label="Chargement des prospects…" />

    <UiEmptyState
      v-else-if="siteList === null"
      title="Chargement impossible"
      description="Les prospects n’ont pas pu être chargés. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="btn-secondary" @click="loadSites">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <template v-else>
      <section class="grid grid-cols-2 gap-4 @3xl:grid-cols-4" aria-label="Chiffres du module">
        <UiStatCard label="Total prospects" :value="siteList.counts.total" icon="i-lucide-users" />
        <UiStatCard label="Avec email" :value="siteList.counts.with_email" icon="i-lucide-mail" />
        <UiStatCard label="Un point à corriger" :value="siteList.counts.to_fix" icon="i-lucide-triangle-alert" />
        <UiStatCard label="Écrits" :value="siteList.counts.written" icon="i-lucide-send" />
      </section>

      <p v-if="searchProgressLabel" class="flex items-center gap-2 text-sm text-[var(--app-ink-soft)]" role="status">
        <UIcon name="i-lucide-loader-circle" class="h-4 w-4 shrink-0 animate-spin" />
        {{ searchProgressLabel }}
      </p>
      <p v-else-if="lastSearchNote" class="text-sm text-[var(--app-ink-soft)]">{{ lastSearchNote }}</p>

      <UiEmptyState
        v-if="siteList.counts.total === 0"
        title="Aucun prospect pour le moment"
        description="Lancez une recherche : les entreprises qui ont déjà un site arrivent ici."
      >
        <template #action>
          <NuxtLink :to="SITE_CARE_SEARCH_PATH" class="btn-primary">
            <UIcon name="i-lucide-plus" class="h-4 w-4" />
            Nouvelle recherche
          </NuxtLink>
        </template>
      </UiEmptyState>

      <section v-else class="flex flex-col gap-4">
        <div class="flex flex-wrap gap-3">
          <div class="relative min-w-0 flex-[999_1_16rem]">
            <UIcon
              name="i-lucide-search"
              class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
            />
            <input
              v-model="searchText"
              type="search"
              placeholder="Nom, ville, adresse du site"
              aria-label="Rechercher un prospect"
              class="app-input pl-9"
            />
          </div>
          <div class="min-w-0 flex-[1_1_12.5rem]">
            <UiSelectField v-model="tradeFilter" :options="tradeOptions" aria-label="Filtrer par métier" />
          </div>
          <div class="min-w-0 flex-[1_1_12.5rem]">
            <UiSelectField
              v-model="issueKindFilter"
              :options="ISSUE_KIND_OPTIONS"
              aria-label="Filtrer par type de souci"
            />
          </div>
        </div>

        <div class="border-b border-[var(--app-line)]">
          <UiFilterTabs :model-value="activeTab" :tabs="siteTabs" @update:model-value="selectTab" />
        </div>

        <div
          class="app-card overflow-hidden transition-opacity"
          :class="{ 'opacity-60': isLoadingSites }"
          :aria-busy="isLoadingSites"
        >
          <div
            class="hidden gap-4 bg-[var(--app-surface-2)] px-5 py-3 @2xl:grid @2xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1.9fr)_minmax(0,1fr)_7.25rem] @2xl:items-center"
          >
            <span class="app-label">Entreprise</span>
            <span class="app-label">Ce qu’on a vu sur son site</span>
            <span class="app-label">Email</span>
            <span class="app-label text-right">État</span>
          </div>

          <ul>
            <li
              v-for="listedSite in sites"
              :key="listedSite.id"
              class="grid gap-2.5 border-t border-[var(--app-line)] p-5 first:border-t-0 @2xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1.9fr)_minmax(0,1fr)_7.25rem] @2xl:items-center @2xl:gap-4 @2xl:first:border-t"
            >
              <button
                type="button"
                class="block w-full min-w-0 rounded text-left focus-visible:ring-2 focus-visible:ring-[var(--app-ink-soft)] focus-visible:outline-none"
                @click="openSiteSheet(listedSite.id)"
              >
                <span class="block text-[15px] font-semibold text-[var(--app-ink)]">{{
                  listedSite.business_name
                }}</span>
                <span class="mt-0.5 block text-[13px] text-[var(--app-ink-soft)]">
                  {{ listedSite.trade_label }} · {{ listedSite.city }}
                </span>
                <span
                  class="block font-[family-name:var(--app-font-mono)] text-xs break-words text-[var(--app-ink-soft)]"
                >
                  {{ listedSite.domain }}
                </span>
              </button>

              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-1.5">
                  <SiteCareIssueTag
                    :kind="listedSite.lead.kind"
                    :label="listedSite.lead.kind_label"
                    :tone="listedSite.lead.tone"
                  />
                  <SiteCareTechnologyChip v-if="listedSite.lead.tech" :technology="listedSite.lead.tech" />
                </div>
                <p class="mt-1.5 text-[15px] leading-snug text-[var(--app-ink)]">{{ listedSite.lead.sentence }}</p>
                <p v-if="listedSite.also" class="mt-0.5 text-[13px] text-[var(--app-ink-soft)]">
                  {{ listedSite.also }}
                </p>
              </div>

              <p
                class="min-w-0 font-[family-name:var(--app-font-mono)] text-[13px] break-words text-[var(--app-ink-soft)]"
              >
                {{ listedSite.email ?? 'Pas d’email connu' }}
              </p>

              <div class="@2xl:justify-self-end @2xl:text-right">
                <span class="app-badge whitespace-nowrap" :class="SITE_CARE_TONE_BADGE_CLASSES[listedSite.state.tone]">
                  {{ listedSite.state.label }}
                </span>
              </div>
            </li>
          </ul>

          <p v-if="sites.length === 0" class="px-5 py-4 text-[13px] text-[var(--app-ink-soft)]">
            Aucun prospect ne correspond à ce tri.
          </p>

          <div
            v-if="hasMoreSites"
            class="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--app-line)] px-5 py-4"
          >
            <p class="text-[13px] text-[var(--app-ink-soft)]">
              {{ sites.length }} prospects affichés sur
              {{ siteList.matching_count }}
            </p>
            <button
              type="button"
              class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="isLoadingMoreSites"
              @click="loadMoreSites"
            >
              <UIcon v-if="isLoadingMoreSites" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
              Afficher plus
            </button>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { LocationQueryValue } from 'vue-router'
import type { UseToastReturn } from '~/types/Composables'
import type { SelectFieldOption } from '~/types/SelectField'
import type { UiFilterTab } from '~/types/UiFilterTabs'
import type { UseSiteCareSiteChangesReturn } from '../../../composables/useSiteCareSiteChanges'
import type { SiteCareSearch } from '../../../types/SiteCareSearch'
import type {
  SiteCareIssueKind,
  SiteCareIssueKindFilter,
  SiteCareSiteListItem,
  SiteCareSiteListQuery,
  SiteCareSiteListResponse,
  SiteCareSiteTab,
  SiteCareSiteTabLabel,
  SiteCareTradeFilter,
} from '../../../types/SiteCareSite'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useToast } from '~/composables/useToast'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { parseApiDate } from '~/utils/date'
import { useSiteCareSiteChanges } from '../../../composables/useSiteCareSiteChanges'
import {
  SITE_CARE_ISSUE_KIND_FILTERS,
  SITE_CARE_SITE_TABS,
  SITE_CARE_TONE_BADGE_CLASSES,
} from '../../../constants/siteCareLabels'
import { SITE_CARE_SEARCH_PATH } from '../../../constants/siteCareModule'
import { SiteCareService } from '../../../services/siteCareService'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Mes prospects · DevLeadHunter' })

const route: ReturnType<typeof useRoute> = useRoute()
const toast: UseToastReturn = useToast()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
const { siteChangeCount }: UseSiteCareSiteChangesReturn = useSiteCareSiteChanges()

/** Value of a filter that keeps everything. */
const ALL_FILTER_VALUE: string = 'all'

/** Rows asked per call, and the most the API gives in one call. */
const SITE_PAGE_SIZE: number = 100
const SITE_LIST_MAXIMUM_LIMIT: number = 500

const SEARCH_TEXT_DEBOUNCE_MS: number = 300

/** While a search runs, its progress and the list are read again at this pace. */
const SEARCH_PROGRESS_REFRESH_INTERVAL_MS: number = 5000

/** How long the note of the last search (not enough businesses, failure) stays above the list. */
const LAST_SEARCH_NOTE_LIFETIME_MS: number = 24 * 60 * 60 * 1000

const ISSUE_KIND_OPTIONS: SelectFieldOption[] = [
  { value: ALL_FILTER_VALUE, label: 'Tous les soucis' },
  ...SITE_CARE_ISSUE_KIND_FILTERS.map(
    (filter: SiteCareIssueKindFilter): SelectFieldOption => ({ value: filter.kind, label: filter.label }),
  ),
]

/** The latest answer of the API: its counts cover every site, its rows only the first window. */
const siteList: Ref<SiteCareSiteListResponse | null> = ref(null)
/** The rows on screen: the first window, plus the ones « Afficher plus » added. */
const sites: Ref<SiteCareSiteListItem[]> = ref([])
const isLoadingSites: Ref<boolean> = ref(true)
const isLoadingMoreSites: Ref<boolean> = ref(false)
const activeTab: Ref<SiteCareSiteTab> = ref(parseSiteTab(firstQueryValue(route.query.tab)) ?? 'to_write')
const tradeFilter: Ref<string> = ref(ALL_FILTER_VALUE)
const issueKindFilter: Ref<string> = ref(parseIssueKind(firstQueryValue(route.query.kind)) ?? ALL_FILTER_VALUE)
const searchText: Ref<string> = ref('')
/** The text the list is filtered on: `searchText` once the typing paused. */
const appliedSearchText: Ref<string> = ref('')
const currentSearch: Ref<SiteCareSearch | null> = ref(null)

/** Number of the latest list request: an answer that is not the latest one is dropped. */
let latestSiteRequestNumber: number = 0
let searchTextTimer: ReturnType<typeof setTimeout> | null = null
let searchProgressTimer: ReturnType<typeof setTimeout> | null = null
let hasLeftPage: boolean = false

const siteTabs: ComputedRef<UiFilterTab[]> = computed((): UiFilterTab[] =>
  SITE_CARE_SITE_TABS.map(
    (tab: SiteCareSiteTabLabel): UiFilterTab => ({
      key: tab.key,
      label: tab.label,
      count: siteList.value?.tab_counts[tab.key],
    }),
  ),
)

const tradeOptions: ComputedRef<SelectFieldOption[]> = computed((): SelectFieldOption[] => [
  { value: ALL_FILTER_VALUE, label: 'Tous les métiers' },
  ...(siteList.value?.trades ?? []).map(
    (trade: SiteCareTradeFilter): SelectFieldOption => ({ value: trade.key, label: trade.label }),
  ),
])

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
  const checkedSitesWording: string = search.checked_count > 1 ? 'sites regardés' : 'site regardé'
  return `Recherche en cours : ${search.checked_count} ${checkedSitesWording} sur ${search.requested_count}`
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
 * Read a tab of the list from a raw value.
 * @param value - The value to read.
 * @returns The tab, or null when the value names none.
 */
function parseSiteTab(value: string | null): SiteCareSiteTab | null {
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
    trade: tradeFilter.value === ALL_FILTER_VALUE ? null : tradeFilter.value,
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
 * Read again the rows on screen and the counts, without a loader: after an action of the sheet, or while a search
 * brings new prospects.
 * @returns A promise resolved once the list is up to date; a failure leaves the list as it is.
 */
async function refreshSites(): Promise<void> {
  if (siteList.value === null || isLoadingSites.value || isLoadingMoreSites.value) {
    return
  }
  latestSiteRequestNumber += 1
  const requestNumber: number = latestSiteRequestNumber
  const shownSiteCount: number = Math.min(Math.max(sites.value.length, SITE_PAGE_SIZE), SITE_LIST_MAXIMUM_LIMIT)
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
 * @param tabKey - The key of the tab clicked.
 */
function selectTab(tabKey: string): void {
  const tab: SiteCareSiteTab | null = parseSiteTab(tabKey)
  if (tab !== null) {
    activeTab.value = tab
  }
}

/**
 * Open the sheet of a prospect in the drawer stack.
 * @param siteId - The site to open.
 */
function openSiteSheet(siteId: number): void {
  drawerStack.push({ kind: 'site-care-site', siteId })
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
  (): string => [activeTab.value, tradeFilter.value, issueKindFilter.value, appliedSearchText.value].join('\n'),
  (): void => {
    loadSites()
  },
)

watch(
  (): number => siteChangeCount.value,
  (): void => {
    refreshSites()
  },
)

onMounted(async (): Promise<void> => {
  const requestedSiteId: number | null = parseSiteId(firstQueryValue(route.query.site))
  if (requestedSiteId !== null) {
    openSiteSheet(requestedSiteId)
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
