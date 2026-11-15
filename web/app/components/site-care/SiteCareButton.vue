<template>
  <NuxtLink
    v-if="props.to !== null"
    :to="props.to"
    :class="[LINK_VARIANT_CLASSES[props.variant], sizeAndOutlineClasses]"
  >
    <UIcon v-if="props.leadingIcon" :name="props.leadingIcon" class="h-4 w-4 shrink-0" aria-hidden="true" />
    <slot />
    <UIcon v-if="props.trailingIcon" :name="props.trailingIcon" class="h-4 w-4 shrink-0" aria-hidden="true" />
  </NuxtLink>
  <UiDlhButton
    v-else
    :variant="props.variant"
    :type="props.type"
    :disabled="props.isDisabled"
    :loading="props.isLoading"
    :class="sizeAndOutlineClasses"
  >
    <UIcon
      v-if="props.leadingIcon && !props.isLoading"
      :name="props.leadingIcon"
      class="h-4 w-4 shrink-0"
      aria-hidden="true"
    />
    <slot />
    <UIcon v-if="props.trailingIcon" :name="props.trailingIcon" class="h-4 w-4 shrink-0" aria-hidden="true" />
  </UiDlhButton>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import type {
  SiteCareButtonProps,
  SiteCareButtonSize,
  SiteCareButtonType,
  SiteCareButtonVariant,
} from '../../types/SiteCareButton'
import { computed } from 'vue'

const props: SiteCareButtonProps = defineProps({
  variant: {
    type: String as PropType<SiteCareButtonVariant>,
    default: 'primary',
  },
  size: {
    type: String as PropType<SiteCareButtonSize>,
    default: 'medium',
  },
  to: {
    type: [String, Object] as PropType<RouteLocationRaw | null>,
    default: null,
  },
  type: {
    type: String as PropType<SiteCareButtonType>,
    default: 'button',
  },
  leadingIcon: {
    type: String as PropType<string | null>,
    default: null,
  },
  trailingIcon: {
    type: String as PropType<string | null>,
    default: null,
  },
  isDisabled: {
    type: Boolean,
    default: false,
  },
  isLoading: {
    type: Boolean,
    default: false,
  },
})

const LINK_VARIANT_CLASSES: Record<SiteCareButtonVariant, string> = {
  primary: 'app-btn-primary',
  secondary: 'app-btn-secondary',
}

const OUTLINE_CLASSES: Record<SiteCareButtonVariant, string> = {
  primary: '',
  secondary: 'border-[var(--app-ink)] bg-transparent',
}

const SIZE_CLASSES: Record<SiteCareButtonSize, string> = {
  large: 'h-[52px] min-h-[52px] px-6 text-base',
  medium: 'h-12 min-h-12 px-6 text-[15px]',
  small: 'h-11 min-h-11 px-5',
}

const sizeAndOutlineClasses: ComputedRef<string> = computed(
  (): string => `${SIZE_CLASSES[props.size]} ${OUTLINE_CLASSES[props.variant]}`,
)
</script>
