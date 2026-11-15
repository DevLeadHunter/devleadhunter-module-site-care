<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full py-1 pr-3 pl-2.5 text-[13px] font-medium whitespace-nowrap"
    :class="SITE_CARE_TONE_CLASSES[props.tone]"
  >
    <UIcon :name="SITE_CARE_ISSUE_KIND_ICONS[props.kind]" class="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
    {{ props.label }}
  </span>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SiteCareIssueTagProps } from '../../types/SiteCareIssueTag'
import type { SiteCareLeadKind, SiteCareTone } from '../../types/SiteCareSite'
import { SITE_CARE_ISSUE_KIND_ICONS, SITE_CARE_TONE_CLASSES } from '../../constants/siteCareLabels'

const props: SiteCareIssueTagProps = defineProps({
  kind: {
    type: String as PropType<SiteCareLeadKind>,
    required: true,
  },
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
