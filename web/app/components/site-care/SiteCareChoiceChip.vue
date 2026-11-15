<template>
  <button
    type="button"
    class="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border px-4 text-[15px] transition-colors focus-visible:ring-2 focus-visible:ring-[var(--app-ink-soft)] focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
    :class="
      props.isSelected
        ? 'border-[var(--app-ink)] bg-[var(--app-ink)] font-semibold text-[var(--app-bg)]'
        : 'border-[var(--app-line)] bg-[var(--app-bg)] text-[var(--app-ink)] hover:border-[var(--app-ink-soft)]'
    "
    :aria-pressed="props.isSelected"
    :disabled="props.isDisabled"
  >
    <UIcon v-if="props.isSelected" name="i-lucide-check" class="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
    <slot />
  </button>
</template>

<script lang="ts" setup>
import type { SiteCareChoiceChipProps } from '../../types/SiteCareChoiceChip'

const props: SiteCareChoiceChipProps = defineProps({
  isSelected: {
    type: Boolean,
    required: true,
  },
  isDisabled: {
    type: Boolean,
    default: false,
  },
})
</script>
