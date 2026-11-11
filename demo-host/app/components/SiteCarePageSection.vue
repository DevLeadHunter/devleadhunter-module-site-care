<template>
  <section class="px-6 py-12 sm:py-16" :class="{ 'bg-site-care-band': props.hasTintedBackground }">
    <div class="mx-auto flex w-full max-w-140 flex-col gap-6">
      <p class="text-site-care-violet text-xs font-medium tracking-[0.08em] uppercase">
        {{ props.eyebrow }}
      </p>
      <h2 v-if="props.heading" class="text-[28px] leading-[1.15] font-medium tracking-[-0.01em] text-balance">
        {{ props.heading }}
      </h2>
      <slot />
    </div>
  </section>
</template>

<script lang="ts" setup>
import type { SiteCarePageSectionProps } from '../types/SiteCarePageSection'

const props: SiteCarePageSectionProps = defineProps({
  eyebrow: {
    type: String,
    required: true,
  },
  heading: {
    type: String,
    default: '',
  },
  hasTintedBackground: {
    type: Boolean,
    default: false,
  },
})
</script>
