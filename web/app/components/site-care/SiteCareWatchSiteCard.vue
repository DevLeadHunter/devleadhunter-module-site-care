<template>
  <SiteCareLinkCard :to="`${SITE_CARE_SITES_PATH}/${props.siteChange.site_id}`" is-compact>
    <div class="flex flex-wrap items-center justify-between gap-2">
      <span class="flex flex-wrap items-center gap-2">
        <SiteCareIssueTag
          :kind="props.siteChange.kind"
          :label="props.siteChange.kind_label"
          :tone="props.siteChange.tone"
        />
        <SiteCareTechnologyChip v-if="props.siteChange.tech" :technology="props.siteChange.tech" />
      </span>
      <span class="text-xs text-[var(--app-ink-soft)]">{{ props.siteChange.seen_label }}</span>
    </div>
    <h3 class="mt-2.5 text-sm leading-snug font-semibold text-[var(--app-ink)]">{{ props.siteChange.sentence }}</h3>
    <SiteCareBusinessSummary
      class="mt-3 border-t border-[var(--app-line)] pt-3"
      :business-name="props.siteChange.business_name"
      :trade-label="props.siteChange.trade_label"
      :city="props.siteChange.city"
    >
      <template #trailing>
        <SiteCareStateBadge :label="props.siteChange.state.label" :tone="props.siteChange.state.tone" />
      </template>
    </SiteCareBusinessSummary>
  </SiteCareLinkCard>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SiteCareWatchSiteChange } from '../../types/SiteCareWatch'
import type { SiteCareWatchSiteCardProps } from '../../types/SiteCareWatchSiteCard'
import { SITE_CARE_SITES_PATH } from '../../constants/siteCareModule'

/** One site of the watch: what changed on it, when it was seen and where the owner stands with it; opens its page. */
const props: SiteCareWatchSiteCardProps = defineProps({
  siteChange: {
    type: Object as PropType<SiteCareWatchSiteChange>,
    required: true,
  },
})
</script>
