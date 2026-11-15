<template>
  <span
    class="inline-flex items-center rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-2.5 py-0.5 text-[13px] font-medium whitespace-nowrap text-[var(--app-ink)]"
  >
    {{ props.technology }}
  </span>
</template>

<script lang="ts" setup>
import type { SiteCareTechnologyChipProps } from '../../types/SiteCareTechnologyChip'

const props: SiteCareTechnologyChipProps = defineProps({
  technology: {
    type: String,
    required: true,
  },
})
</script>
