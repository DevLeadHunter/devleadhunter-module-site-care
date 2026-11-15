<template>
  <NuxtLink
    :to="props.to"
    class="flex flex-col rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5 transition-colors hover:border-[var(--app-ink)] focus-visible:border-[var(--app-ink)] focus-visible:outline-none"
  >
    <slot />
  </NuxtLink>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import type { SiteCareLinkCardProps } from '../../types/SiteCareLinkCard'

const props: SiteCareLinkCardProps = defineProps({
  to: {
    type: [String, Object] as PropType<RouteLocationRaw>,
    required: true,
  },
})
</script>
