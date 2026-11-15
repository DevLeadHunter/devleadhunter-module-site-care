import type {
  SiteCareIssueKindFilter,
  SiteCareLeadKind,
  SiteCareSiteTab,
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
]

export const SITE_CARE_SITE_TAB_HINTS: Record<SiteCareSiteTab, string> = {
  to_write: 'Du plus grave au plus léger.',
  written: 'L’ouverture et la réponse sont détectées toutes seules.',
  no_email: 'Ouvrez un prospect pour chercher son adresse sur son site, ou la saisir.',
  nothing: 'On ne leur écrit pas : leur site est relu tous les sept jours.',
  review: 'Ces sites seront relus au prochain contrôle.',
  all: 'Tous vos prospects, tous onglets confondus.',
}

export const SITE_CARE_TONE_CLASSES: Record<SiteCareTone, string> = {
  red: 'bg-[var(--app-red-soft)] text-[var(--app-red)]',
  amber: 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]',
  green: 'bg-[var(--app-green-soft)] text-[var(--app-green)]',
  violet: 'bg-[var(--app-violet-soft)] text-[var(--app-violet)]',
  ink: 'bg-[var(--app-ink)] text-[var(--app-bg)]',
  neutral: 'bg-[var(--app-surface-2)] text-[var(--app-ink-soft)]',
}
