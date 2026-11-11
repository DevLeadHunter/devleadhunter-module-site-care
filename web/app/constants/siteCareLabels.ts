import type {
  SiteCareIssueKindFilter,
  SiteCareLeadKind,
  SiteCareSiteTabLabel,
  SiteCareTone,
} from '../types/SiteCareSite'

export const SITE_CARE_ISSUE_KIND_ICONS: Record<SiteCareLeadKind, string> = {
  hack: 'i-lucide-shield-alert',
  security: 'i-lucide-lock',
  risk: 'i-lucide-triangle-alert',
  late: 'i-lucide-refresh-cw',
  mail: 'i-lucide-mail',
  mobile: 'i-lucide-smartphone',
  contact: 'i-lucide-phone',
  dated: 'i-lucide-calendar',
  google: 'i-lucide-search',
  ok: 'i-lucide-check',
  review: 'i-lucide-circle-help',
}

export const SITE_CARE_ISSUE_KIND_FILTERS: SiteCareIssueKindFilter[] = [
  { kind: 'hack', label: 'Site piraté' },
  { kind: 'security', label: 'Sécurité' },
  { kind: 'risk', label: 'Version à risque' },
  { kind: 'late', label: 'Mise à jour en retard' },
  { kind: 'mail', label: 'E-mails' },
  { kind: 'mobile', label: 'Sur téléphone' },
  { kind: 'contact', label: 'Coordonnées' },
  { kind: 'dated', label: 'Site daté' },
  { kind: 'google', label: 'Dans Google' },
]

export const SITE_CARE_SITE_TABS: SiteCareSiteTabLabel[] = [
  { key: 'to_write', label: 'À écrire' },
  { key: 'written', label: 'Écrits' },
  { key: 'no_email', label: 'Sans email' },
  { key: 'nothing', label: 'Rien à signaler' },
  { key: 'review', label: 'À revoir' },
  { key: 'all', label: 'Tous' },
]

export const SITE_CARE_TONE_BADGE_CLASSES: Record<SiteCareTone, string> = {
  red: 'app-badge--danger',
  amber: 'app-badge--progress',
  green: 'app-badge--success',
  violet: 'app-badge--engaged',
  ink: 'app-badge--strong',
  neutral: '',
}
