<template>
  <div class="flex items-center gap-3">
    <span
      class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--app-surface-2)] text-[13px] font-semibold text-[var(--app-ink-soft)]"
      aria-hidden="true"
    >
      {{ SiteCareBusinessLabels.initialsOf(props.businessName) }}
    </span>
    <span class="min-w-0 flex-1">
      <span class="block truncate text-sm font-semibold text-[var(--app-ink)]">{{ props.businessName }}</span>
      <span class="block truncate text-sm text-[var(--app-ink-soft)]">
        {{ SiteCareBusinessLabels.placeOf(props.tradeLabel, props.city) }}
      </span>
    </span>
    <slot name="trailing" />
  </div>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SiteCareBusinessSummaryProps } from '../../types/SiteCareBusinessSummary'
import { SiteCareBusinessLabels } from '../../utils/siteCareBusinessLabels'

/** A business at the foot of a card: its initials, its name, its trade and city; `trailing` holds what sits on the right. */
const props: SiteCareBusinessSummaryProps = defineProps({
  businessName: {
    type: String,
    required: true,
  },
  tradeLabel: {
    type: String,
    required: true,
  },
  city: {
    type: String as PropType<string | null>,
    default: null,
  },
})
</script>
