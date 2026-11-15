<template>
  <SiteCareLinkCard :to="`${SITE_CARE_SITES_PATH}/${props.site.id}`">
    <div class="mb-2.5 flex flex-wrap items-center gap-2">
      <SiteCareIssueTag :kind="props.site.lead.kind" :label="props.site.lead.kind_label" :tone="props.site.lead.tone" />
      <SiteCareTechnologyChip v-if="props.site.lead.tech" :technology="props.site.lead.tech" />
    </div>
    <h2 class="text-base leading-snug font-semibold tracking-[-0.01em] text-[var(--app-ink)]">
      {{ props.site.lead.sentence }}
    </h2>
    <p v-if="props.site.also" class="mt-1.5 text-sm text-[var(--app-ink-soft)]">{{ props.site.also }}</p>

    <div class="mt-auto pt-3">
      <div class="flex items-center gap-3 border-t border-[var(--app-line)] pt-3">
        <span
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--app-surface-2)] text-[13px] font-semibold text-[var(--app-ink-soft)]"
          aria-hidden="true"
        >
          {{ SiteCareBusinessLabels.initialsOf(props.site.business_name) }}
        </span>
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-semibold text-[var(--app-ink)]">{{ props.site.business_name }}</span>
          <span class="block truncate text-sm text-[var(--app-ink-soft)]">
            {{ SiteCareBusinessLabels.placeOf(props.site.trade_label, props.site.city) }}
          </span>
        </span>
        <span v-if="isOfferShown" class="shrink-0 text-right">
          <span class="block text-base leading-tight font-semibold text-[var(--app-ink)]">
            {{ props.site.price_label }}
          </span>
          <span class="block text-xs font-medium text-[var(--app-ink-soft)]">à proposer</span>
        </span>
        <span
          v-else
          class="inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap"
          :class="SITE_CARE_TONE_CLASSES[props.site.state.tone]"
        >
          {{ props.site.state.label }}
        </span>
      </div>
    </div>
  </SiteCareLinkCard>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { SiteCareSiteListItem } from '../../types/SiteCareSite'
import type { SiteCareSitePreviewCardProps } from '../../types/SiteCareSitePreviewCard'
import { computed } from 'vue'
import { SITE_CARE_TONE_CLASSES } from '../../constants/siteCareLabels'
import { SITE_CARE_SITES_PATH } from '../../constants/siteCareModule'
import { SiteCareBusinessLabels } from '../../utils/siteCareBusinessLabels'

/** A site of « Mes prospects » as its card: the issue that leads, the business, then the price to offer or its state. */
const props: SiteCareSitePreviewCardProps = defineProps({
  site: {
    type: Object as PropType<SiteCareSiteListItem>,
    required: true,
  },
})

const isOfferShown: ComputedRef<boolean> = computed(
  (): boolean => props.site.state.key === 'to_write' && props.site.price_label !== null,
)
</script>
