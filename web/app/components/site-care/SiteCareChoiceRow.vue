<template>
  <button
    type="button"
    role="radio"
    :aria-checked="props.isSelected"
    class="flex w-full cursor-pointer items-center gap-4 rounded-lg border-t border-[var(--app-line)] py-[18px] text-left first:border-t-0 first:pt-0 last:pb-0 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--app-ink-soft)]"
  >
    <slot name="leading" />
    <span class="min-w-0 flex-1">
      <span class="block text-[17px] font-semibold text-[var(--app-ink)]">{{ props.title }}</span>
      <span v-if="props.description" class="mt-0.5 block text-[15px] text-[var(--app-ink-soft)]">
        {{ props.description }}
      </span>
    </span>
    <span
      class="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full border-[1.5px]"
      :class="
        props.isSelected
          ? 'border-[var(--app-btn-bg)] bg-[var(--app-btn-bg)] text-[var(--app-btn-text)]'
          : 'border-[var(--app-ink-soft)]'
      "
      aria-hidden="true"
    >
      <UIcon v-if="props.isSelected" name="i-lucide-check" class="h-3.5 w-3.5" />
    </span>
  </button>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SiteCareChoiceRowProps } from '../../types/SiteCareChoiceRow'

/** To be placed inside a `radiogroup` of the page. */
const props: SiteCareChoiceRowProps = defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String as PropType<string | null>,
    default: null,
  },
  isSelected: {
    type: Boolean,
    required: true,
  },
})
</script>
