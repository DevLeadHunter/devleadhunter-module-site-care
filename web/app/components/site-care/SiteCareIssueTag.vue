<template>
  <span
    class="app-badge gap-1.5 py-[3px] pr-2.5 pl-2 text-[13px] font-semibold whitespace-nowrap"
    :class="
      props.kind === 'hack' ? 'bg-[var(--app-red)] text-[var(--app-surface)]' : SITE_CARE_TONE_BADGE_CLASSES[props.tone]
    "
  >
    <UIcon :name="SITE_CARE_ISSUE_KIND_ICONS[props.kind]" class="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
    {{ props.label }}
  </span>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { SiteCareIssueTagProps } from '../../types/SiteCareIssueTag'
import type { SiteCareLeadKind, SiteCareTone } from '../../types/SiteCareSite'
import { SITE_CARE_ISSUE_KIND_ICONS, SITE_CARE_TONE_BADGE_CLASSES } from '../../constants/siteCareLabels'

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
