<template>
  <span
    class="inline-flex items-center rounded-md border border-[var(--app-line)] px-2 py-0.5 font-[family-name:var(--app-font-mono)] text-xs whitespace-nowrap text-[var(--app-ink)]"
  >
    {{ props.technology }}
  </span>
</template>

<script lang="ts" setup>
import type { SiteCareTechnologyChipProps } from '../../types/SiteCareTechnologyChip'

/** Chip naming the technology an issue is about (« PHP 7.4 », « WordPress 6.5 »), shown next to the issue tag. */
const props: SiteCareTechnologyChipProps = defineProps({
  technology: {
    type: String,
    required: true,
  },
})
</script>
