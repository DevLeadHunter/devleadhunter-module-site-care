<template>
  <NuxtLink
    :to="props.to"
    class="flex flex-col border border-[var(--app-line)] bg-[var(--app-surface)] transition-colors hover:border-[var(--app-ink)] focus-visible:border-[var(--app-ink)] focus-visible:outline-none"
    :class="props.isCompact ? 'rounded-xl p-4' : 'rounded-2xl p-5'"
  >
    <slot />
  </NuxtLink>
</template>

<script lang="ts" setup>
import type { PropType } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import type { SiteCareLinkCardProps } from '../../types/SiteCareLinkCard'

/** A card that opens a page; `isCompact` is the smaller card of a board column. */
const props: SiteCareLinkCardProps = defineProps({
  to: {
    type: [String, Object] as PropType<RouteLocationRaw>,
    required: true,
  },
  isCompact: {
    type: Boolean,
    default: false,
  },
})
</script>
