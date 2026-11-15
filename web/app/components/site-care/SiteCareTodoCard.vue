<template>
  <section
    class="flex flex-wrap items-center gap-x-7 gap-y-5 rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5 @2xl:p-7"
  >
    <span
      v-if="slots.tile"
      class="hidden h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-[17px] font-semibold @lg:flex"
      :class="SITE_CARE_TONE_CLASSES[props.tileTone]"
      aria-hidden="true"
    >
      <slot name="tile" />
    </span>
    <div class="min-w-0 flex-[999_1_20rem]">
      <span class="block text-[13px] font-medium text-[var(--app-ink-soft)]">{{ props.eyebrow }}</span>
      <h2 class="mt-1 mb-2 text-xl font-semibold tracking-[-0.01em] text-[var(--app-ink)]">{{ props.title }}</h2>
      <p v-if="props.description" class="text-base leading-relaxed text-[var(--app-ink)]">{{ props.description }}</p>
      <slot />
    </div>
    <div v-if="slots.actions" class="flex flex-[1_1_14rem] flex-col gap-2.5 @2xl:max-w-64">
      <slot name="actions" />
    </div>
    <slot name="footer" />
  </section>
</template>

<script lang="ts" setup>
import type { PropType, Slots } from 'vue'
import type { SiteCareTone } from '../../types/SiteCareSite'
import type { SiteCareTodoCardProps } from '../../types/SiteCareTodoCard'
import { useSlots } from 'vue'
import { SITE_CARE_TONE_CLASSES } from '../../constants/siteCareLabels'

const props: SiteCareTodoCardProps = defineProps({
  eyebrow: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String as PropType<string | null>,
    default: null,
  },
  tileTone: {
    type: String as PropType<SiteCareTone>,
    default: 'neutral',
  },
})

const slots: Slots = useSlots()
</script>
