<template>
  <span
    ref="anchorElement"
    class="group relative inline-flex"
    @mouseenter="keepTooltipOnScreen"
    @focusin="keepTooltipOnScreen"
  >
    <button
      type="button"
      class="-my-3 inline-flex h-11 w-11 shrink-0 cursor-help items-center justify-center rounded-full text-[#5b8fe0] transition-colors hover:text-[#3f76cf] focus-visible:text-[#3f76cf] focus-visible:outline-none dark:text-[#8fb4ff]"
      :aria-label="props.accessibleLabel"
      :aria-describedby="tooltipId"
    >
      <UIcon name="i-lucide-info" class="h-[22px] w-[22px]" aria-hidden="true" />
    </button>
    <span
      :id="tooltipId"
      ref="tooltipElement"
      role="tooltip"
      class="pointer-events-none absolute top-full z-30 mt-1 hidden w-80 max-w-[calc(100vw-2rem)] rounded-xl bg-[var(--app-ink)] px-3.5 py-3 text-sm leading-normal font-normal tracking-normal text-[var(--app-bg)] normal-case group-focus-within:block group-hover:block"
      :style="{ left: `${tooltipLeftOffset}px` }"
    >
      {{ props.infoText }}
    </span>
  </span>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import type { SiteCareInfoTipProps } from '../../types/SiteCareInfoTip'
import { ref, useId } from 'vue'

const props: SiteCareInfoTipProps = defineProps({
  accessibleLabel: {
    type: String,
    required: true,
  },
  infoText: {
    type: String,
    required: true,
  },
})

const tooltipId: string = useId()

const SCREEN_EDGE_MARGIN: number = 16

const anchorElement: Ref<HTMLElement | null> = ref(null)
const tooltipElement: Ref<HTMLElement | null> = ref(null)
const tooltipLeftOffset: Ref<number> = ref(0)

/** Slide the tooltip to the left when it would cross the right edge of the screen, as under an « i » on a phone. */
function keepTooltipOnScreen(): void {
  if (anchorElement.value === null || tooltipElement.value === null) {
    return
  }

  const anchorLeft: number = anchorElement.value.getBoundingClientRect().left
  const roomOnTheRight: number = document.documentElement.clientWidth - SCREEN_EDGE_MARGIN - anchorLeft
  const widthBeyondTheScreen: number = tooltipElement.value.offsetWidth - roomOnTheRight
  tooltipLeftOffset.value = -Math.max(0, Math.min(widthBeyondTheScreen, anchorLeft - SCREEN_EDGE_MARGIN))
}
</script>
