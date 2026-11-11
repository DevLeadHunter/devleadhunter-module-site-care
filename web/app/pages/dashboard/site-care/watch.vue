<template>
  <div class="flex min-h-full max-w-4xl flex-col gap-8">
    <UiPageHeader
      eyebrow="Entretien de sites"
      :has-eyebrow-mark="false"
      title="Veille"
      description="Ce qui vient de changer sur les sites de vos prospects, et les dates qui approchent. Chaque ligne est une raison d’écrire aujourd’hui."
    />

    <UiLoader v-if="isLoadingWatch" label="Chargement de la veille…" />

    <UiEmptyState
      v-else-if="hasWatchLoadFailed"
      title="Chargement impossible"
      description="La veille n’a pas pu être chargée. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="btn-secondary" @click="loadWatch">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <p v-else-if="watchSections.length === 0" class="app-card p-6 text-sm text-[var(--app-ink-soft)]">
      Rien de nouveau sur les sites de vos prospects.
    </p>

    <template v-else>
      <section v-for="watchSection in watchSections" :key="watchSection.heading">
        <h2 class="app-label mb-3">{{ watchSection.heading }}</h2>
        <div class="app-card divide-y divide-[var(--app-line)]">
          <article v-for="event in watchSection.events" :key="event.key" class="flex items-start gap-4 p-5 @2xl:p-6">
            <span
              class="app-badge h-10 w-10 shrink-0 justify-center p-0"
              :class="SITE_CARE_TONE_BADGE_CLASSES[event.tone]"
            >
              <UIcon :name="eventIcon(event)" class="h-[18px] w-[18px]" aria-hidden="true" />
            </span>
            <div class="min-w-0">
              <h3 class="text-base font-semibold text-[var(--app-ink)]">{{ event.title }}</h3>
              <p class="mt-1.5 text-[15px] leading-relaxed text-[var(--app-ink-soft)]">{{ event.detail }}</p>
              <p class="mt-2 font-[family-name:var(--app-font-mono)] text-xs text-[var(--app-ink-soft)]">
                {{ event.when_label }}
              </p>
              <NuxtLink :to="eventDestination(event)" class="btn-secondary mt-4 inline-flex">
                {{ event.action_label }}
              </NuxtLink>
            </div>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import type { SiteCareWatchEvent, SiteCareWatchResponse } from '../../../types/SiteCareWatch'
import type { SiteCareWatchSection } from '../../../types/SiteCareWatchPage'
import { computed, onMounted, ref } from 'vue'
import { SITE_CARE_ISSUE_KIND_ICONS, SITE_CARE_TONE_BADGE_CLASSES } from '../../../constants/siteCareLabels'
import { SITE_CARE_SECTION_PATH } from '../../../constants/siteCareModule'
import { SiteCareService } from '../../../services/siteCareService'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Veille · DevLeadHunter' })

const UNKNOWN_EVENT_ICON: string = 'i-lucide-bell'

const watchFeed: Ref<SiteCareWatchResponse | null> = ref(null)
const isLoadingWatch: Ref<boolean> = ref(true)
const hasWatchLoadFailed: Ref<boolean> = ref(false)

const watchSections: ComputedRef<SiteCareWatchSection[]> = computed((): SiteCareWatchSection[] => {
  if (watchFeed.value === null) {
    return []
  }
  const sections: SiteCareWatchSection[] = [
    { heading: 'Aujourd’hui', events: watchFeed.value.today },
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
 * Where the button of an event leads: « Mes prospects », on the sheet of its site or on its tab and type of issue.
 * @param event - The event.
 * @returns The route of the list, the target in its query.
 */
function eventDestination(event: SiteCareWatchEvent): RouteLocationRaw {
  if (event.target.site_id !== null) {
    return {
      path: SITE_CARE_SECTION_PATH,
      query: { site: String(event.target.site_id) },
    }
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
