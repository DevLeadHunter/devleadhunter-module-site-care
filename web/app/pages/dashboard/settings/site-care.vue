<template>
  <div class="max-w-3xl space-y-6">
    <UiPageHeader
      eyebrow="Paramètres"
      title="Entretien de sites"
      description="Vos prix, ce qui est regardé sur chaque site, et à partir de quand on écrit."
    />

    <UiLoader v-if="isLoadingSettings" label="Chargement des réglages…" />

    <UiEmptyState
      v-else-if="form === null || savedSettings === null"
      title="Chargement impossible"
      description="Les réglages n’ont pas pu être chargés. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="btn-secondary" @click="loadSettings">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <template v-else>
      <section class="app-card p-5 @2xl:p-6">
        <h2 class="text-base font-semibold text-[var(--app-ink)]">Prix des corrections</h2>
        <p class="mt-1 text-sm text-[var(--app-ink-soft)]">Annoncés dans le message, avant de commencer.</p>
        <ul class="mt-4 divide-y divide-[var(--app-line)]">
          <li
            v-for="price in form.fixedPrices"
            :key="price.key"
            class="flex items-center justify-between gap-4 py-3 first:pt-0"
          >
            <label :for="`site-care-price-${price.key}`" class="min-w-0 text-[15px] text-[var(--app-ink)]">
              {{ price.label }}
            </label>
            <span class="flex shrink-0 items-center gap-2 text-sm text-[var(--app-ink-soft)]">
              <input
                :id="`site-care-price-${price.key}`"
                v-model.number="price.euros"
                type="number"
                inputmode="numeric"
                min="0"
                step="10"
                class="app-input w-24 text-right"
              />
              €
            </span>
          </li>
          <li class="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
            <label for="site-care-monthly-price" class="min-w-0 text-[15px] text-[var(--app-ink)]">Suivi mensuel</label>
            <span class="flex shrink-0 items-center gap-2 text-sm text-[var(--app-ink-soft)]">
              <input
                id="site-care-monthly-price"
                v-model.number="form.monthlyPriceEuros"
                type="number"
                inputmode="numeric"
                min="0"
                step="10"
                class="app-input w-24 text-right"
              />
              € par mois
            </span>
          </li>
          <li
            v-for="price in quotedPrices"
            :key="price.key"
            class="flex min-h-11 items-center justify-between gap-4 py-3 last:pb-0"
          >
            <span class="min-w-0 text-[15px] text-[var(--app-ink)]">{{ price.label }}</span>
            <span class="app-badge shrink-0 whitespace-nowrap">Sur devis</span>
          </li>
        </ul>
      </section>

      <section class="app-card p-5 @2xl:p-6">
        <h2 id="site-care-trigger-title" class="text-base font-semibold text-[var(--app-ink)]">Quand écrire</h2>
        <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
          Un site sans rien à corriger reste dans « Rien à signaler » : on ne lui écrit pas.
        </p>
        <UiRadioCardGroup
          v-model="form.trigger"
          :options="WRITING_TRIGGER_OPTIONS"
          labelled-by="site-care-trigger-title"
          class="mt-4"
        />
      </section>

      <section class="app-card p-5 @2xl:p-6">
        <h2 class="text-base font-semibold text-[var(--app-ink)]">Ce qui est regardé sur chaque site</h2>
        <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
          Seulement ce que voit un visiteur : la page d’accueil et les réglages publics du nom de domaine.
        </p>
        <div v-for="family in checkedPointFamilies" :key="family.label" class="mt-5">
          <h3 class="app-label">{{ family.label }}</h3>
          <ul class="mt-1 divide-y divide-[var(--app-line)]">
            <li
              v-for="point in family.points"
              :key="point.key"
              class="flex min-h-11 items-center justify-between gap-4 py-2"
            >
              <label :for="`site-care-point-${point.key}`" class="min-w-0 flex-1 text-[15px] text-[var(--app-ink)]">
                {{ point.label }}
              </label>
              <UiSwitch :id="`site-care-point-${point.key}`" v-model="point.is_enabled" />
            </li>
          </ul>
        </div>
      </section>

      <section class="app-card p-5 @2xl:p-6">
        <h2 class="text-base font-semibold text-[var(--app-ink)]">Qui écrit</h2>
        <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
          Le message et la page préparée pour le prospect vous présentent avec ces informations.
        </p>
        <div class="mt-4 grid gap-4 @2xl:grid-cols-2">
          <label class="block">
            <span class="app-label mb-1.5 block">Nom</span>
            <input v-model="form.presenter.name" type="text" autocomplete="name" class="app-input" />
          </label>
          <label class="block">
            <span class="app-label mb-1.5 block">Adresse du site</span>
            <input
              v-model="form.presenter.site_url"
              type="url"
              inputmode="url"
              autocomplete="off"
              placeholder="https://"
              class="app-input"
            />
          </label>
          <label class="block @2xl:col-span-2">
            <span class="app-label mb-1.5 block">Votre métier, après « Je suis {{ presenterNameExample }}, »</span>
            <input
              v-model="form.presenter.role"
              type="text"
              autocomplete="off"
              placeholder="développeur web à Rennes"
              class="app-input"
            />
          </label>
          <label class="block @2xl:col-span-2">
            <span class="app-label mb-1.5 block">Présentation en une ligne</span>
            <input v-model="form.presenter.tagline" type="text" autocomplete="off" class="app-input" />
          </label>
          <label class="block @2xl:col-span-2">
            <span class="app-label mb-1.5 block">Adresse de la photo</span>
            <input
              v-model="form.presenter.photo_url"
              type="url"
              inputmode="url"
              autocomplete="off"
              placeholder="https://"
              class="app-input"
            />
          </label>
        </div>
      </section>

      <section class="app-card p-5 @2xl:p-6">
        <h2 class="text-base font-semibold text-[var(--app-ink)]">Adresse d’envoi</h2>
        <p class="mt-1 text-sm break-words text-[var(--app-ink-soft)]">
          {{
            savedSettings.sender_email === null
              ? 'L’envoi d’emails n’est pas encore configuré.'
              : `Les messages partent de ${savedSettings.sender_email}.`
          }}
        </p>
      </section>

      <div
        class="sticky bottom-0 z-10 flex items-center justify-between gap-3 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)]/90 py-1.5 pr-1.5 pl-4 shadow-lg backdrop-blur"
      >
        <p
          class="min-w-0 text-sm"
          :class="saveFailureMessage ? 'text-[var(--app-red)]' : 'text-[var(--app-ink-soft)]'"
          role="status"
        >
          {{ saveStatusMessage }}
        </p>
        <button
          type="button"
          class="btn-primary h-11 shrink-0 disabled:cursor-not-allowed disabled:opacity-50 sm:h-9"
          :disabled="!canSave"
          @click="saveSettings"
        >
          <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
          Enregistrer
        </button>
      </div>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { UiRadioCardOption } from '~/types/UiRadioCardGroup'
import type {
  SiteCareCheckedPoint,
  SiteCarePrice,
  SiteCareSettings,
  SiteCareWritingTrigger,
} from '../../../types/SiteCareSettings'
import type {
  SiteCareCheckedPointFamily,
  SiteCareFixedPriceField,
  SiteCareSettingsForm,
} from '../../../types/SiteCareSettingsPage'
import { computed, onMounted, ref } from 'vue'
import { SiteCareService } from '../../../services/siteCareService'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Entretien de sites · DevLeadHunter' })

const CENTS_PER_EURO: number = 100

const WRITING_TRIGGER_OPTIONS: UiRadioCardOption<SiteCareWritingTrigger>[] = [
  {
    value: 'fix',
    label: 'Dès qu’un point est à corriger',
    description: 'Le réglage conseillé : un message par vrai problème.',
    icon: 'i-lucide-triangle-alert',
  },
  {
    value: 'watch',
    label: 'Aussi quand trois points sont à surveiller',
    description: 'Plus de messages, pour des corrections plus petites.',
    icon: 'i-lucide-eye',
  },
]

/** The settings as the API holds them; nothing can be saved until they are read, so a failed read never overwrites them. */
const savedSettings: Ref<SiteCareSettings | null> = ref(null)
const form: Ref<SiteCareSettingsForm | null> = ref(null)
/** The form as it was when read or saved, to tell whether something changed since. */
const savedFormSnapshot: Ref<string> = ref('')
const isLoadingSettings: Ref<boolean> = ref(true)
const isSaving: Ref<boolean> = ref(false)
const hasJustSaved: Ref<boolean> = ref(false)
const saveFailureMessage: Ref<string | null> = ref(null)

const quotedPrices: ComputedRef<SiteCarePrice[]> = computed((): SiteCarePrice[] =>
  (savedSettings.value?.prices ?? []).filter((price: SiteCarePrice): boolean => price.price_cents === null),
)

const checkedPointFamilies: ComputedRef<SiteCareCheckedPointFamily[]> = computed((): SiteCareCheckedPointFamily[] => {
  const families: SiteCareCheckedPointFamily[] = []
  for (const point of form.value?.points ?? []) {
    const family: SiteCareCheckedPointFamily | undefined = families.find(
      (candidate: SiteCareCheckedPointFamily): boolean => candidate.label === point.family_label,
    )

    if (family) {
      family.points.push(point)
    } else {
      families.push({ label: point.family_label, points: [point] })
    }
  }
  return families
})

const hasUnsavedChanges: ComputedRef<boolean> = computed(
  (): boolean => form.value !== null && JSON.stringify(form.value) !== savedFormSnapshot.value,
)

const hasValidPrices: ComputedRef<boolean> = computed(
  (): boolean =>
    form.value !== null &&
    isValidEuroAmount(form.value.monthlyPriceEuros) &&
    form.value.fixedPrices.every((price: SiteCareFixedPriceField): boolean => isValidEuroAmount(price.euros)),
)

const canSave: ComputedRef<boolean> = computed(
  (): boolean => hasUnsavedChanges.value && hasValidPrices.value && !isSaving.value,
)

const presenterNameExample: ComputedRef<string> = computed(
  (): string => form.value?.presenter.name.trim() || 'votre nom',
)

const saveStatusMessage: ComputedRef<string> = computed((): string => {
  if (saveFailureMessage.value !== null) {
    return saveFailureMessage.value
  }

  if (hasUnsavedChanges.value) {
    return hasValidPrices.value ? 'Des changements ne sont pas enregistrés.' : 'Un prix est un nombre, zéro ou plus.'
  }
  return hasJustSaved.value ? 'Réglages enregistrés.' : ''
})

/**
 * Whether a price field holds an amount that can be saved; an emptied field holds an empty text, not a number.
 * @param euros - The value of the field.
 * @returns True for a number, zero or more.
 */
function isValidEuroAmount(euros: unknown): boolean {
  return typeof euros === 'number' && Number.isFinite(euros) && euros >= 0
}

/**
 * The settings as the form edits them: prices in euros, the corrections quoted case by case left to their badge.
 * @param settings - The settings as the API holds them.
 * @returns The form.
 */
function formOf(settings: SiteCareSettings): SiteCareSettingsForm {
  const fixedPrices: SiteCareFixedPriceField[] = []
  for (const price of settings.prices) {
    if (price.price_cents !== null) {
      fixedPrices.push({ key: price.key, label: price.label, euros: price.price_cents / CENTS_PER_EURO })
    }
  }
  return {
    fixedPrices,
    monthlyPriceEuros: settings.monthly_price_cents / CENTS_PER_EURO,
    trigger: settings.trigger,
    points: settings.points.map((point: SiteCareCheckedPoint): SiteCareCheckedPoint => ({ ...point })),
    presenter: { ...settings.presenter },
  }
}

/**
 * The settings to send: the form's values back in cents, in the shape the API gave them.
 * @param editedForm - The form as edited.
 * @param currentSettings - The settings the form was built from.
 * @returns The settings to save.
 */
function settingsOf(editedForm: SiteCareSettingsForm, currentSettings: SiteCareSettings): SiteCareSettings {
  return {
    prices: currentSettings.prices.map((price: SiteCarePrice): SiteCarePrice => {
      const editedPrice: SiteCareFixedPriceField | undefined = editedForm.fixedPrices.find(
        (field: SiteCareFixedPriceField): boolean => field.key === price.key,
      )
      return editedPrice ? { ...price, price_cents: Math.round(editedPrice.euros * CENTS_PER_EURO) } : price
    }),
    monthly_price_cents: Math.round(editedForm.monthlyPriceEuros * CENTS_PER_EURO),
    trigger: editedForm.trigger,
    points: editedForm.points,
    presenter: {
      name: editedForm.presenter.name.trim(),
      role: editedForm.presenter.role.trim(),
      tagline: editedForm.presenter.tagline.trim(),
      site_url: editedForm.presenter.site_url.trim(),
      photo_url: editedForm.presenter.photo_url.trim(),
    },
    sender_email: currentSettings.sender_email,
  }
}

/**
 * Show settings as the API holds them, and remember them as the saved state.
 * @param settings - The settings read or just saved.
 */
function showSettings(settings: SiteCareSettings): void {
  savedSettings.value = settings
  form.value = formOf(settings)
  savedFormSnapshot.value = JSON.stringify(formOf(settings))
}

/**
 * Read the saved settings.
 * @returns A promise resolved once they are shown, or the failure is.
 */
async function loadSettings(): Promise<void> {
  isLoadingSettings.value = true
  try {
    showSettings(await SiteCareService.getSettings())
  } catch {
    savedSettings.value = null
    form.value = null
  } finally {
    isLoadingSettings.value = false
  }
}

/**
 * Save the settings as edited, then show them as the API saved them.
 * @returns A promise resolved once saved, or the failure is shown.
 */
async function saveSettings(): Promise<void> {
  if (!canSave.value || form.value === null || savedSettings.value === null) {
    return
  }
  isSaving.value = true
  hasJustSaved.value = false
  saveFailureMessage.value = null
  try {
    showSettings(await SiteCareService.saveSettings(settingsOf(form.value, savedSettings.value)))
    hasJustSaved.value = true
  } catch (error: unknown) {
    saveFailureMessage.value = SiteCareService.failureMessage(error, 'Les réglages n’ont pas pu être enregistrés.')
  } finally {
    isSaving.value = false
  }
}

onMounted(async (): Promise<void> => {
  await loadSettings()
})
</script>
