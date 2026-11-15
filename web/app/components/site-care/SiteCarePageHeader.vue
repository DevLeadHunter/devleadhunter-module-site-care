<template>
  <header class="flex flex-wrap items-center justify-between gap-5">
    <div class="min-w-0 flex-[999_1_24rem]">
      <div class="flex items-center gap-1">
        <h1 :class="titleClasses">{{ props.title }}</h1>
        <SiteCareInfoTip v-if="props.infoText" accessible-label="À propos de cette page" :info-text="props.infoText" />
      </div>
      <p v-if="props.description" class="mt-1.5 text-[var(--app-ink-soft)]" :class="descriptionClasses">
        {{ props.description }}
      </p>
    </div>
    <div v-if="slots.action" class="flex flex-wrap gap-3">
      <slot name="action" />
    </div>
  </header>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Slots } from 'vue'
import type { SiteCarePageHeaderProps } from '../../types/SiteCarePageHeader'
import { computed, useSlots } from 'vue'

/** `hasLargeTitle` keeps the large title of the step pages (a site, a new search), whose buttons stay large too. */
const props: SiteCarePageHeaderProps = defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String as PropType<string | null>,
    default: null,
  },
  infoText: {
    type: String as PropType<string | null>,
    default: null,
  },
  hasLargeTitle: {
    type: Boolean,
    default: false,
  },
})

const slots: Slots = useSlots()

const titleClasses: ComputedRef<string> = computed((): string =>
  props.hasLargeTitle
    ? 'text-2xl leading-tight font-semibold tracking-[-0.02em] text-[var(--app-ink)] @xl:text-[1.75rem]'
    : 'app-page-title',
)

const descriptionClasses: ComputedRef<string> = computed((): string =>
  props.hasLargeTitle ? 'max-w-[60ch] text-base' : 'max-w-2xl text-sm',
)
</script>
