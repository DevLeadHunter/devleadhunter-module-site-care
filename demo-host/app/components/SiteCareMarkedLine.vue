<template>
  <li class="flex items-start gap-3">
    <svg
      class="mt-0.5 size-5 flex-none"
      :class="props.mark === 'check' ? 'text-site-care-violet' : 'text-site-care-ink-soft'"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <template v-if="props.mark === 'check'">
        <path d="M21.801 10A10 10 0 1 1 17 3.335" />
        <path d="m9 11 3 3L22 4" />
      </template>
      <template v-else>
        <circle cx="12" cy="12" r="10" />
        <path d="M12 8v4M12 16h.01" />
      </template>
    </svg>
    <p class="text-site-care-ink-muted text-[15px] leading-6">
      {{ props.text }}
    </p>
  </li>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SiteCareLineMark, SiteCareMarkedLineProps } from '../types/SiteCareMarkedLine'

const props: SiteCareMarkedLineProps = defineProps({
  text: {
    type: String,
    required: true,
  },
  mark: {
    type: String as PropType<SiteCareLineMark>,
    default: 'check',
  },
})
</script>
