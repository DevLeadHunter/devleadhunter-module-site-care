<template>
  <section
    class="flex flex-col gap-5 rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-6 @2xl:p-7"
    :aria-labelledby="props.titleId ?? undefined"
  >
    <div v-if="props.title" class="flex items-center gap-0.5 border-b border-[var(--app-line)] pb-4">
      <h2 :id="props.titleId ?? undefined" class="text-lg font-semibold tracking-[-0.01em] text-[var(--app-ink)]">
        {{ props.title }}
      </h2>
      <slot name="info" />
    </div>
    <slot />
  </section>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SiteCareCardProps } from '../../types/SiteCareCard'

const props: SiteCareCardProps = defineProps({
  title: {
    type: String as PropType<string | null>,
    default: null,
  },
  titleId: {
    type: String as PropType<string | null>,
    default: null,
  },
})
</script>
