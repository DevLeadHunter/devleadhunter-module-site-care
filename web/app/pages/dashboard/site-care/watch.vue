<template>
  <div class="flex min-h-full max-w-4xl flex-col gap-8">
    <SiteCarePageHeader
      title="Veille"
      description="Ce qui a changé sur les sites de vos prospects, et les dates qui approchent. Chaque ligne est une raison d’écrire."
      info-text="Le site de chaque prospect est relu tous les sept jours. Quand quelque chose change, ou qu’une date approche, une ligne apparaît ici."
    />

    <UiLoader v-if="isLoadingWatch" label="Chargement de la veille…" />

    <UiEmptyState
      v-else-if="hasWatchLoadFailed"
      title="Chargement impossible"
      description="La veille n’a pas pu être chargée. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="app-btn-secondary" @click="loadWatch">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <SiteCareCard v-else-if="priorityEvent === null && watchSections.length === 0">
      <p class="text-base text-[var(--app-ink-soft)]">Rien de nouveau sur les sites de vos prospects.</p>
    </SiteCareCard>

    <template v-else>
      <SiteCareTodoCard
        v-if="priorityEvent !== null"
        :eyebrow="`À faire · ${priorityEvent.when_label}`"
        :title="priorityEvent.title"
        :description="priorityEvent.detail"
        :tile-tone="priorityEvent.tone"
        aria-label="À faire en premier"
      >
        <template #tile>
          <UIcon :name="eventIcon(priorityEvent)" class="h-6 w-6" />
        </template>
        <template #actions>
          <SiteCareButton :to="eventDestination(priorityEvent)" class="w-full" trailing-icon="i-lucide-arrow-right">
            {{ priorityEvent.action_label }}
          </SiteCareButton>
        </template>
      </SiteCareTodoCard>

      <SiteCareCard v-for="watchSection in watchSections" :key="watchSection.heading" :title="watchSection.heading">
        <div class="flex flex-col">
          <NuxtLink
            v-for="event in watchSection.events"
            :key="event.key"
            :to="eventDestination(event)"
            class="group flex items-start gap-4 border-t border-[var(--app-line)] py-[18px] first:border-t-0 first:pt-0 last:pb-0"
          >
            <span
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
              :class="SITE_CARE_TONE_CLASSES[event.tone]"
              aria-hidden="true"
            >
              <UIcon :name="eventIcon(event)" class="h-[18px] w-[18px]" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="block text-[17px] leading-snug font-semibold text-[var(--app-ink)] group-hover:underline">
                {{ event.title }}
              </span>
              <span class="mt-1 block text-[15px] leading-normal text-[var(--app-ink-soft)]">{{ event.detail }}</span>
              <span class="mt-1.5 block text-[13px] font-medium text-[var(--app-ink-soft)]">
                {{ event.when_label }} · {{ event.action_label }}
              </span>
            </span>
            <UIcon
              name="i-lucide-chevron-right"
              class="mt-2.5 h-[18px] w-[18px] shrink-0 text-[var(--app-ink-soft)]"
              aria-hidden="true"
            />
          </NuxtLink>
        </div>
      </SiteCareCard>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import type { SiteCareWatchEvent, SiteCareWatchResponse } from '../../../types/SiteCareWatch'
import type { SiteCareWatchSection } from '../../../types/SiteCareWatchPage'
import { computed, onMounted, ref } from 'vue'
import { SITE_CARE_ISSUE_KIND_ICONS, SITE_CARE_TONE_CLASSES } from '../../../constants/siteCareLabels'
import { SITE_CARE_SECTION_PATH, SITE_CARE_SITES_PATH } from '../../../constants/siteCareModule'
import { SiteCareService } from '../../../services/siteCareService'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Veille · DevLeadHunter' })

const UNKNOWN_EVENT_ICON: string = 'i-lucide-bell'

const watchFeed: Ref<SiteCareWatchResponse | null> = ref(null)
const isLoadingWatch: Ref<boolean> = ref(true)
const hasWatchLoadFailed: Ref<boolean> = ref(false)

const priorityEvent: ComputedRef<SiteCareWatchEvent | null> = computed(
  (): SiteCareWatchEvent | null =>
    watchFeed.value?.today.find((event: SiteCareWatchEvent): boolean => event.tone === 'red') ?? null,
)

const watchSections: ComputedRef<SiteCareWatchSection[]> = computed((): SiteCareWatchSection[] => {
  if (watchFeed.value === null) {
    return []
  }
  const sections: SiteCareWatchSection[] = [
    {
      heading: 'Aujourd’hui',
      events: watchFeed.value.today.filter(
        (event: SiteCareWatchEvent): boolean => event.key !== priorityEvent.value?.key,
      ),
    },
    { heading: 'Dates qui approchent', events: watchFeed.value.deadlines },
  ]
  return sections.filter((watchSection: SiteCareWatchSection): boolean => watchSection.events.length > 0)
})

/**
 * The icon of an event, by its kind.
 * @param event - The event.
 * @returns The icon of its kind, or a neutral one for a kind the API added since.
 */
function eventIcon(event: SiteCareWatchEvent): string {
  return SITE_CARE_ISSUE_KIND_ICONS[event.kind] ?? UNKNOWN_EVENT_ICON
}

/**
 * Where an event leads: the page of its site, else « Mes prospects » on its tab and its type of issue.
 * @param event - The event.
 * @returns The route to open.
 */
function eventDestination(event: SiteCareWatchEvent): RouteLocationRaw {
  if (event.target.site_id !== null) {
    return `${SITE_CARE_SITES_PATH}/${event.target.site_id}`
  }
  const query: Record<string, string> = {}
  if (event.target.tab !== null) {
    query.tab = event.target.tab
  }
  if (event.target.kind !== null) {
    query.kind = event.target.kind
  }
  return { path: SITE_CARE_SECTION_PATH, query }
}

/**
 * Read the watch.
 * @returns A promise resolved once the events are shown, or the failure is.
 */
async function loadWatch(): Promise<void> {
  isLoadingWatch.value = true
  hasWatchLoadFailed.value = false
  try {
    watchFeed.value = await SiteCareService.getWatch()
  } catch {
    hasWatchLoadFailed.value = true
  } finally {
    isLoadingWatch.value = false
  }
}

onMounted(async (): Promise<void> => {
  await loadWatch()
})
</script>
