<template>
  <div>
    <span class="block text-[13px] font-medium text-[var(--app-ink-soft)]">À proposer</span>
    <ul class="mt-1">
      <li
        v-for="offerLine in props.offerLines"
        :key="offerLine.label"
        class="flex items-baseline justify-between gap-4 border-t border-[var(--app-line)] py-3 text-[15px] text-[var(--app-ink)] first:border-t-0"
      >
        <span class="min-w-0">{{ offerLine.label }}</span>
        <span class="text-[17px] font-semibold whitespace-nowrap">{{ offerLine.price_label }}</span>
      </li>
    </ul>
    <p class="border-t border-[var(--app-line)] pt-3 text-sm text-[var(--app-ink-soft)]">
      Ensuite, s’il le souhaite : le suivi mensuel, à
      <span class="whitespace-nowrap">{{ props.monthlyLabel }}</span
      >.
    </p>
  </div>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SiteCareOfferListProps } from '../../types/SiteCareOfferList'
import type { SiteCareOfferLine } from '../../types/SiteCareSite'

const props: SiteCareOfferListProps = defineProps({
  offerLines: {
    type: Array as PropType<SiteCareOfferLine[]>,
    required: true,
  },
  monthlyLabel: {
    type: String,
    required: true,
  },
})
</script>
