import type { RouteLocationRaw } from 'vue-router'

export type SiteCareButtonVariant = 'primary' | 'secondary'

export type SiteCareButtonSize = 'large' | 'medium' | 'small'

export type SiteCareButtonType = 'button' | 'submit'

export type SiteCareButtonProps = {
  variant: SiteCareButtonVariant
  size: SiteCareButtonSize
  to: RouteLocationRaw | null
  type: SiteCareButtonType
  leadingIcon: string | null
  trailingIcon: string | null
  isDisabled: boolean
  isLoading: boolean
}
