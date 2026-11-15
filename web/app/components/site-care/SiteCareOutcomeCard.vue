<template>
  <section
    class="flex flex-col items-start gap-4 rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-6 @2xl:p-7"
  >
    <span
      v-if="props.hasCheckMark"
      class="flex h-14 w-14 items-center justify-center rounded-full bg-[var(--app-green-soft)] text-[var(--app-green)]"
      aria-hidden="true"
    >
      <UIcon name="i-lucide-check" class="h-6 w-6" />
    </span>
    <h2 class="text-[22px] font-semibold tracking-[-0.01em] text-[var(--app-ink)]">{{ props.title }}</h2>
    <p class="text-base leading-relaxed text-[var(--app-ink)]">{{ props.description }}</p>
  </section>
</template>

<script lang="ts" setup>
import type { SiteCareOutcomeCardProps } from '../../types/SiteCareOutcomeCard'

const props: SiteCareOutcomeCardProps = defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    required: true,
  },
  hasCheckMark: {
    type: Boolean,
    default: true,
  },
})
</script>
