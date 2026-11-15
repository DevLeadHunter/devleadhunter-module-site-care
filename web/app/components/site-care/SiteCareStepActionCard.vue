<template>
  <aside
    class="flex w-full min-w-0 flex-col gap-6 rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-6 @4xl:sticky @4xl:top-6"
    :aria-label="props.title"
  >
    <div>
      <div v-if="props.stepCount > 0" class="flex gap-1.5" aria-hidden="true">
        <span
          v-for="stepNumber in props.stepCount"
          :key="stepNumber"
          class="h-[5px] flex-1 rounded-full"
          :class="stepNumber <= props.reachedStepCount ? 'bg-[var(--app-ink)]' : 'bg-[var(--app-surface-2)]'"
        ></span>
      </div>
      <p class="text-[17px] font-semibold text-[var(--app-ink)]" :class="{ 'mt-2.5': props.stepCount > 0 }">
        {{ props.title }}
      </p>
    </div>
    <slot />
  </aside>
</template>

<script lang="ts" setup>
import type { SiteCareStepActionCardProps } from '../../types/SiteCareStepActionCard'

const props: SiteCareStepActionCardProps = defineProps({
  title: {
    type: String,
    required: true,
  },
  stepCount: {
    type: Number,
    default: 0,
  },
  reachedStepCount: {
    type: Number,
    default: 0,
  },
})
</script>
