<template>
  <SiteCareLinkCard :to="concernedSitesDestination" is-compact>
    <div class="flex flex-wrap items-center justify-between gap-2">
      <SiteCareIssueTag :kind="props.watchDate.kind" :label="props.watchDate.kind_label" :tone="props.watchDate.tone" />
      <span class="text-xs font-semibold text-[var(--app-ink)]">{{ props.watchDate.countdown_label }}</span>
    </div>
    <h3 class="mt-2.5 text-sm leading-snug font-semibold text-[var(--app-ink)]">{{ props.watchDate.title }}</h3>
    <p class="mt-1 text-sm text-[var(--app-ink-soft)]">{{ props.watchDate.detail }}</p>
    <p class="mt-2 text-sm font-medium text-[var(--app-ink)]">{{ props.watchDate.sites_label }}</p>
    <div
      class="mt-3 flex items-center justify-between gap-3 border-t border-[var(--app-line)] pt-3 text-sm font-medium text-[var(--app-ink)]"
    >
      {{ props.watchDate.action_label }}
      <UIcon name="i-lucide-arrow-right" class="h-4 w-4 shrink-0 text-[var(--app-ink-soft)]" aria-hidden="true" />
    </div>
  </SiteCareLinkCard>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import type { SiteCareWatchDate } from '../../types/SiteCareWatch'
import type { SiteCareWatchDateCardProps } from '../../types/SiteCareWatchDateCard'
import { computed } from 'vue'
import {
  SITE_CARE_SECTION_PATH,
  SITE_CARE_SITES_PATH,
  SITE_CARE_WATCH_DATE_QUERY_NAME,
} from '../../constants/siteCareModule'

/** One date after which some sites will have a problem; opens its only site, else « Mes prospects » on its sites. */
const props: SiteCareWatchDateCardProps = defineProps({
  watchDate: {
    type: Object as PropType<SiteCareWatchDate>,
    required: true,
  },
})

const concernedSitesDestination: ComputedRef<RouteLocationRaw> = computed((): RouteLocationRaw => {
  if (props.watchDate.site_id !== null) {
    return `${SITE_CARE_SITES_PATH}/${props.watchDate.site_id}`
  }
  return { path: SITE_CARE_SECTION_PATH, query: { tab: 'all', [SITE_CARE_WATCH_DATE_QUERY_NAME]: props.watchDate.key } }
})
</script>
