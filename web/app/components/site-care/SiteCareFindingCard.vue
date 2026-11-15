<template>
  <SiteCareCard title="Ce qu’on a vu sur son site" title-id="site-care-finding-title">
    <p v-if="props.site.unread_text" class="text-base leading-relaxed text-[var(--app-ink)]">
      {{ props.site.unread_text }}
    </p>

    <div v-if="props.site.fixes.length > 0" class="flex flex-col gap-3">
      <h3 class="text-[15px] font-semibold text-[var(--app-ink)]">À corriger</h3>
      <ul class="divide-y divide-[var(--app-line)]">
        <li v-for="point in props.site.fixes" :key="point.key" class="flex flex-col gap-2 py-4 first:pt-0 last:pb-0">
          <div class="flex flex-wrap items-center gap-2">
            <SiteCareIssueTag :kind="point.kind" :label="point.kind_label" :tone="point.tone" />
            <SiteCareTechnologyChip v-if="point.tech" :technology="point.tech" />
          </div>
          <p class="text-base leading-relaxed font-medium text-[var(--app-ink)]">{{ point.fact }}</p>
        </li>
      </ul>
    </div>

    <div v-if="props.site.watches.length > 0" class="flex flex-col gap-3">
      <h3 class="text-[15px] font-semibold text-[var(--app-ink)]">À surveiller</h3>
      <ul class="divide-y divide-[var(--app-line)]">
        <li v-for="point in props.site.watches" :key="point.key" class="flex flex-col gap-2 py-4 first:pt-0 last:pb-0">
          <div class="flex flex-wrap items-center gap-2">
            <SiteCareIssueTag :kind="point.kind" :label="point.kind_label" :tone="point.tone" />
            <SiteCareTechnologyChip v-if="point.tech" :technology="point.tech" />
          </div>
          <p class="text-base leading-relaxed text-[var(--app-ink)]">{{ point.fact }}</p>
        </li>
      </ul>
    </div>

    <div v-if="props.site.good_points.length > 0" class="flex flex-col gap-3">
      <h3 class="text-[15px] font-semibold text-[var(--app-ink)]">Ce qui va bien</h3>
      <ul class="grid gap-x-6 gap-y-2.5 @2xl:grid-cols-2">
        <li
          v-for="goodPoint in props.site.good_points"
          :key="goodPoint"
          class="flex items-start gap-3 text-[15px] text-[var(--app-ink)]"
        >
          <span
            class="mt-px flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--app-green-soft)] text-[var(--app-green)]"
            aria-hidden="true"
          >
            <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
          </span>
          {{ goodPoint }}
        </li>
      </ul>
      <p v-if="props.site.hidden_line" class="text-sm text-[var(--app-ink-soft)]">{{ props.site.hidden_line }}</p>
    </div>

    <div class="flex flex-col gap-1">
      <h3 class="text-[15px] font-semibold text-[var(--app-ink)]">Le voir vous-même</h3>
      <div class="flex flex-col">
        <button
          type="button"
          class="group flex min-h-16 w-full cursor-pointer items-center gap-3.5 py-3 text-left"
          @click="openWebsite"
        >
          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--app-blue-soft)] text-[var(--app-blue)]"
            aria-hidden="true"
          >
            <UIcon name="i-lucide-globe" class="h-[18px] w-[18px]" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block text-[13px] font-medium text-[var(--app-ink-soft)]">Son site</span>
            <span class="block font-semibold break-all text-[var(--app-ink)] group-hover:underline">
              {{ props.site.domain }}
            </span>
          </span>
          <UIcon
            name="i-lucide-external-link"
            class="h-[18px] w-[18px] shrink-0 text-[var(--app-ink-soft)]"
            aria-label="Lien externe"
          />
        </button>
        <button
          v-if="props.site.page_url"
          type="button"
          class="group flex min-h-16 w-full cursor-pointer items-center gap-3.5 border-t border-[var(--app-line)] py-3 text-left"
          @click="openPreparedPage"
        >
          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--app-violet-soft)] text-[var(--app-violet)]"
            aria-hidden="true"
          >
            <UIcon name="i-lucide-file-text" class="h-[18px] w-[18px]" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block text-[13px] font-medium text-[var(--app-ink-soft)]">Facultative</span>
            <span class="block font-semibold text-[var(--app-ink)] group-hover:underline">
              La page préparée pour lui
            </span>
          </span>
          <UIcon
            name="i-lucide-external-link"
            class="h-[18px] w-[18px] shrink-0 text-[var(--app-ink-soft)]"
            aria-label="Lien externe"
          />
        </button>
        <button
          v-if="props.site.tab !== 'review'"
          type="button"
          class="group flex min-h-16 w-full cursor-pointer items-center gap-3.5 border-t border-[var(--app-line)] py-3 text-left disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="props.isActionPending"
          @click="emit('recheck')"
        >
          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]"
            aria-hidden="true"
          >
            <UIcon
              :name="props.isRechecking ? 'i-lucide-loader-circle' : 'i-lucide-refresh-cw'"
              class="h-[18px] w-[18px]"
              :class="{ 'animate-spin': props.isRechecking }"
            />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block text-[13px] font-medium text-[var(--app-ink-soft)]">{{ checkedLabel }}</span>
            <span class="block font-semibold text-[var(--app-ink)] group-hover:underline">Recontrôler le site</span>
          </span>
        </button>
      </div>
    </div>
  </SiteCareCard>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { UseOpenExternalUrlReturn } from '~/types/Composables'
import type { SiteCareFindingCardEmits, SiteCareFindingCardProps } from '../../types/SiteCareFindingCard'
import type { SiteCareSiteDetail } from '../../types/SiteCareSite'
import { computed } from 'vue'
import { useOpenExternalUrl } from '~/composables/useOpenExternalUrl'
import { formatShortMonthDayTime } from '~/utils/date'

const props: SiteCareFindingCardProps = defineProps({
  site: {
    type: Object as PropType<SiteCareSiteDetail>,
    required: true,
  },
  isRechecking: {
    type: Boolean,
    default: false,
  },
  isActionPending: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<SiteCareFindingCardEmits> = defineEmits<SiteCareFindingCardEmits>()

const { openExternalUrl }: UseOpenExternalUrlReturn = useOpenExternalUrl()

const checkedLabel: ComputedRef<string> = computed(
  (): string => `Contrôlé le ${formatShortMonthDayTime(props.site.checked_at)}`,
)

/**
 * Open the prospect's own website in a new tab.
 * @returns A promise resolved once the website is opened.
 */
async function openWebsite(): Promise<void> {
  await openExternalUrl(props.site.website)
}

/**
 * Open the page prepared for the prospect in a new tab, marked as an internal visit so it is not counted as his.
 * @returns A promise resolved once the page is opened.
 */
async function openPreparedPage(): Promise<void> {
  const pageUrl: string | null = props.site.page_url
  if (pageUrl !== null) {
    await openExternalUrl(`${pageUrl}${pageUrl.includes('?') ? '&' : '?'}internal=1`)
  }
}
</script>
