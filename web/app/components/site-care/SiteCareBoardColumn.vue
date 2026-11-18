<template>
  <section
    class="flex flex-col gap-3 rounded-2xl p-4"
    :class="SITE_CARE_TONE_CLASSES[props.tone]"
    :aria-labelledby="titleId"
  >
    <div class="px-1">
      <div class="flex items-baseline justify-between gap-2 font-semibold">
        <h2 :id="titleId" class="text-[15px]">{{ props.title }}</h2>
        <span class="text-sm">{{ props.cardCount }}</span>
      </div>
      <p class="mt-0.5 text-[13px]">{{ props.description }}</p>
    </div>
    <slot />
    <p v-if="props.cardCount === 0" class="px-1 py-3 text-sm">{{ props.emptyText }}</p>
  </section>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SiteCareBoardColumnProps } from '../../types/SiteCareBoardColumn'
import type { SiteCareTone } from '../../types/SiteCareSite'
import { useId } from 'vue'
import { SITE_CARE_TONE_CLASSES } from '../../constants/siteCareLabels'

/** A tinted column of a board: its heading, how many cards it holds, one line that says what they are. */
const props: SiteCareBoardColumnProps = defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    required: true,
  },
  cardCount: {
    type: Number,
    required: true,
  },
  tone: {
    type: String as PropType<SiteCareTone>,
    required: true,
  },
  emptyText: {
    type: String,
    required: true,
  },
})

const titleId: string = useId()
</script>
