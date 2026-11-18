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
      <SiteCareBusinessSummary
        class="border-t border-[var(--app-line)] pt-3"
        :business-name="props.site.business_name"
        :trade-label="props.site.trade_label"
        :city="props.site.city"
      >
        <template #trailing>
          <span v-if="isOfferShown" class="shrink-0 text-right">
            <span class="block text-base leading-tight font-semibold text-[var(--app-ink)]">
              {{ props.site.price_label }}
            </span>
            <span class="block text-xs font-medium text-[var(--app-ink-soft)]">à proposer</span>
          </span>
          <SiteCareStateBadge v-else :label="props.site.state.label" :tone="props.site.state.tone" />
        </template>
      </SiteCareBusinessSummary>
    </div>
  </SiteCareLinkCard>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { SiteCareSiteListItem } from '../../types/SiteCareSite'
import type { SiteCareSitePreviewCardProps } from '../../types/SiteCareSitePreviewCard'
import { computed } from 'vue'
import { SITE_CARE_SITES_PATH } from '../../constants/siteCareModule'

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
