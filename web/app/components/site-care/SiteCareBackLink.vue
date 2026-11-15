<template>
  <NuxtLink
    :to="props.to"
    class="inline-flex min-h-11 items-center gap-2 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] pr-[18px] pl-3 text-[15px] font-medium text-[var(--app-ink)] transition-colors hover:border-[var(--app-ink-soft)]"
  >
    <UIcon name="i-lucide-chevron-left" class="h-4 w-4" aria-hidden="true" />
    <slot />
  </NuxtLink>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import type { SiteCareBackLinkProps } from '../../types/SiteCareBackLink'

const props: SiteCareBackLinkProps = defineProps({
  to: {
    type: [String, Object] as PropType<RouteLocationRaw>,
    required: true,
  },
})
</script>
