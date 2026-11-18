<template>
  <span
    class="inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap"
    :class="SITE_CARE_TONE_CLASSES[props.tone]"
  >
    {{ props.label }}
  </span>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SiteCareTone } from '../../types/SiteCareSite'
import type { SiteCareStateBadgeProps } from '../../types/SiteCareStateBadge'
import { SITE_CARE_TONE_CLASSES } from '../../constants/siteCareLabels'

/** Where the owner stands with a site (« À écrire », « Sans email », « Écrit le 9 nov. »), in the colour the API picked. */
const props: SiteCareStateBadgeProps = defineProps({
  label: {
    type: String,
    required: true,
  },
  tone: {
    type: String as PropType<SiteCareTone>,
    required: true,
  },
})
</script>
