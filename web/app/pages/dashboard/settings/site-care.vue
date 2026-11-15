<template>
  <div class="flex max-w-4xl flex-col gap-7">
    <SiteCarePageHeader
      title="Entretien de sites"
      description="Vos prix, quand écrire, et ce qui est regardé sur chaque site."
    >
      <template v-if="form !== null" #action>
        <SiteCareButton v-if="hasUnsavedChanges" :is-disabled="!canSave" :is-loading="isSaving" @click="saveSettings">
          Enregistrer
        </SiteCareButton>
        <span
          v-else
          class="inline-flex min-h-12 items-center rounded-full bg-[var(--app-surface-2)] px-[22px] text-[15px] font-medium text-[var(--app-ink-soft)]"
          role="status"
        >
          À jour
        </span>
      </template>
    </SiteCarePageHeader>

    <UiLoader v-if="isLoadingSettings" label="Chargement des réglages…" />

    <UiEmptyState
      v-else-if="form === null || savedSettings === null"
      title="Chargement impossible"
      description="Les réglages n’ont pas pu être chargés. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="app-btn-secondary" @click="loadSettings">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <template v-else>
      <p v-if="saveProblemMessage" class="-mt-3 text-sm text-[var(--app-red)]" role="alert">{{ saveProblemMessage }}</p>

      <div
        class="flex flex-wrap gap-1 border-b border-[var(--app-line)]"
        role="tablist"
        aria-label="Sections des réglages"
      >
        <button
          v-for="sectionTab in SETTINGS_SECTION_TABS"
          :key="sectionTab.key"
          type="button"
          role="tab"
          :aria-selected="sectionTab.key === activeSection"
          class="min-h-12 cursor-pointer px-[18px] text-base transition-colors"
          :class="
            sectionTab.key === activeSection
              ? 'font-semibold text-[var(--app-ink)] shadow-[inset_0_-2px_0_var(--app-ink)]'
              : 'font-medium text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
          "
          @click="activeSection = sectionTab.key"
        >
          {{ sectionTab.label }}
        </button>
      </div>

      <section
        class="flex flex-col gap-6 rounded-2xl border border-[var(--app-line)] bg-[var(--app-surface)] p-6 @2xl:p-8"
        role="tabpanel"
        :aria-labelledby="SECTION_TITLE_ID"
      >
        <div class="flex items-center gap-0.5">
          <h2 :id="SECTION_TITLE_ID" class="text-xl font-semibold tracking-[-0.01em] text-[var(--app-ink)]">
            {{ activeSectionTab.title }}
          </h2>
          <SiteCareInfoTip
            :accessible-label="activeSectionTab.infoAccessibleLabel"
            :info-text="activeSectionTab.infoText"
          />
        </div>

        <ul v-if="activeSection === 'prices'" class="flex flex-col">
          <li
            v-for="price in form.fixedPrices"
            :key="price.key"
            class="flex min-h-[68px] items-center justify-between gap-4 border-t border-[var(--app-line)] py-2.5 first:border-t-0"
          >
            <label :for="`site-care-price-${price.key}`" class="min-w-0 text-base text-[var(--app-ink)]">
              {{ price.label }}
            </label>
            <span class="flex shrink-0 items-center gap-2.5">
              <input
                :id="`site-care-price-${price.key}`"
                v-model.number="price.euros"
                type="number"
                inputmode="numeric"
                min="0"
                step="10"
                class="app-input h-12 w-24 rounded-xl text-right text-base font-semibold"
              />
              <span class="w-4 text-[15px] text-[var(--app-ink-soft)]">€</span>
            </span>
          </li>
          <li
            class="flex min-h-[68px] items-center justify-between gap-4 border-t border-[var(--app-line)] py-2.5 first:border-t-0"
          >
            <label for="site-care-monthly-price" class="min-w-0 text-base text-[var(--app-ink)]">
              Suivi mensuel, par mois
            </label>
            <span class="flex shrink-0 items-center gap-2.5">
              <input
                id="site-care-monthly-price"
                v-model.number="form.monthlyPriceEuros"
                type="number"
                inputmode="numeric"
                min="0"
                step="10"
                class="app-input h-12 w-24 rounded-xl text-right text-base font-semibold"
              />
              <span class="w-4 text-[15px] text-[var(--app-ink-soft)]">€</span>
            </span>
          </li>
          <li
            v-for="price in quotedPrices"
            :key="price.key"
            class="flex min-h-[68px] items-center justify-between gap-4 border-t border-[var(--app-line)] py-2.5"
          >
            <span class="min-w-0 text-base text-[var(--app-ink)]">{{ price.label }}</span>
            <span
              class="inline-flex shrink-0 items-center rounded-full bg-[var(--app-surface-2)] px-3 py-1 text-[13px] font-medium text-[var(--app-ink-soft)]"
            >
              Sur devis
            </span>
          </li>
        </ul>

        <template v-else-if="activeSection === 'trigger'">
          <div class="flex flex-col" role="radiogroup" :aria-labelledby="SECTION_TITLE_ID">
            <SiteCareChoiceRow
              v-for="triggerOption in WRITING_TRIGGER_OPTIONS"
              :key="triggerOption.value"
              :title="triggerOption.label"
              :description="triggerOption.description"
              :is-selected="form.trigger === triggerOption.value"
              @click="form.trigger = triggerOption.value"
            />
          </div>

          <div class="flex flex-col gap-5 border-t border-[var(--app-line)] pt-6">
            <div class="flex flex-wrap items-center gap-x-4 gap-y-3">
              <img
                v-if="profilePhotoObjectUrl"
                :src="profilePhotoObjectUrl"
                alt=""
                class="h-12 w-12 shrink-0 rounded-full border border-[var(--app-line)] object-cover"
              />
              <span
                v-else
                class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[var(--app-surface-2)] text-[15px] font-semibold text-[var(--app-ink-soft)]"
                aria-hidden="true"
              >
                {{ SiteCareBusinessLabels.initialsOf(savedSettings.presenter.name) }}
              </span>
              <div class="min-w-0 flex-[999_1_10rem]">
                <span class="block text-base font-semibold text-[var(--app-ink)]">Signé avec votre profil</span>
                <span class="block text-sm text-[var(--app-ink-soft)]">{{ profileLine }}</span>
              </div>
              <SiteCareButton variant="secondary" size="small" @click="openProfile">Modifier mon profil</SiteCareButton>
            </div>
            <SiteCareTextField
              v-model="form.presenterRole"
              :field-label="`Votre métier, après « Je suis ${presenterName}, »`"
              placeholder="développeur web à Rennes"
            />
            <SiteCareTextField
              v-model="form.presenterTagline"
              field-label="Une ligne sur vous, sur la page préparée pour le prospect"
            />
          </div>
        </template>

        <div v-else class="grid gap-x-11 gap-y-8 @3xl:grid-cols-2">
          <div v-for="family in checkedPointFamilies" :key="family.label">
            <h3 class="border-b border-[var(--app-line)] pb-3 text-base font-semibold text-[var(--app-ink)]">
              {{ family.label }}
            </h3>
            <ul>
              <li
                v-for="point in family.points"
                :key="point.key"
                class="flex min-h-[54px] items-center justify-between gap-4 border-t border-[var(--app-line)] first:border-t-0"
              >
                <label :for="`site-care-point-${point.key}`" class="min-w-0 flex-1 text-[15px] text-[var(--app-ink)]">
                  {{ point.label }}
                </label>
                <UiSwitch :id="`site-care-point-${point.key}`" v-model="point.is_enabled" />
              </li>
            </ul>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { UseProfilePhotoReturn, UseToastReturn } from '~/types/Composables'
import type { SiteCareCheckedPoint, SiteCarePrice, SiteCareSettings } from '../../../types/SiteCareSettings'
import type {
  SiteCareCheckedPointFamily,
  SiteCareFixedPriceField,
  SiteCareSettingsForm,
  SiteCareSettingsSection,
  SiteCareSettingsSectionTab,
  SiteCareWritingTriggerOption,
} from '../../../types/SiteCareSettingsPage'
import { computed, onMounted, ref } from 'vue'
import { useProfilePhoto } from '~/composables/useProfilePhoto'
import { useToast } from '~/composables/useToast'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { SiteCareService } from '../../../services/siteCareService'
import { SiteCareBusinessLabels } from '../../../utils/siteCareBusinessLabels'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Entretien de sites · DevLeadHunter' })

const toast: UseToastReturn = useToast()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
const { profilePhotoObjectUrl, ensureProfilePhotoLoaded }: UseProfilePhotoReturn = useProfilePhoto()

const CENTS_PER_EURO: number = 100

const SECTION_TITLE_ID: string = 'site-care-settings-section-title'

const SETTINGS_SECTION_TABS: Record<SiteCareSettingsSection, SiteCareSettingsSectionTab> = {
  prices: {
    key: 'prices',
    label: 'Prix',
    title: 'Vos prix',
    infoAccessibleLabel: 'À propos des prix',
    infoText:
      'Le prix de la correction est annoncé dans le message, avant de commencer. Le suivi mensuel n’est proposé qu’ensuite.',
  },
  trigger: {
    key: 'trigger',
    label: 'Quand écrire',
    title: 'Quand écrire',
    infoAccessibleLabel: 'À propos des messages',
    infoText:
      'Un site sans rien à corriger reste dans « Rien à signaler » : on ne lui écrit pas. Rien ne part jamais seul : chaque message est relu, puis envoyé par vous.',
  },
  points: {
    key: 'points',
    label: 'Points regardés',
    title: 'Ce qui est regardé sur chaque site',
    infoAccessibleLabel: 'À propos du contrôle',
    infoText:
      'Seulement ce que voit un visiteur : la page d’accueil et les réglages publics du nom de domaine. Rien n’est envoyé au site, aucune connexion n’est essayée.',
  },
}

const WRITING_TRIGGER_OPTIONS: SiteCareWritingTriggerOption[] = [
  {
    value: 'fix',
    label: 'Dès qu’un point est à corriger',
    description: 'Le réglage conseillé : un message par vrai problème.',
  },
  {
    value: 'watch',
    label: 'Aussi quand trois points sont à surveiller',
    description: 'Plus de messages, pour des corrections plus petites.',
  },
]

/** The settings as the API holds them; nothing can be saved until they are read, so a failed read never overwrites them. */
const savedSettings: Ref<SiteCareSettings | null> = ref(null)
const form: Ref<SiteCareSettingsForm | null> = ref(null)
const savedFormSnapshot: Ref<string> = ref('')
const activeSection: Ref<SiteCareSettingsSection> = ref('prices')
const isLoadingSettings: Ref<boolean> = ref(true)
const isSaving: Ref<boolean> = ref(false)
const saveFailureMessage: Ref<string | null> = ref(null)

const activeSectionTab: ComputedRef<SiteCareSettingsSectionTab> = computed(
  (): SiteCareSettingsSectionTab => SETTINGS_SECTION_TABS[activeSection.value],
)

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

const saveProblemMessage: ComputedRef<string | null> = computed((): string | null => {
  if (saveFailureMessage.value !== null) {
    return saveFailureMessage.value
  }
  return hasUnsavedChanges.value && !hasValidPrices.value ? 'Un prix est un nombre, zéro ou plus.' : null
})

const presenterName: ComputedRef<string> = computed(
  (): string => savedSettings.value?.presenter.name.trim() || 'votre nom',
)

const profileLine: ComputedRef<string> = computed((): string => {
  const sending: string =
    savedSettings.value?.sender_email === null || savedSettings.value?.sender_email === undefined
      ? 'L’envoi d’emails n’est pas encore configuré.'
      : `Les messages partent de ${savedSettings.value.sender_email}.`
  return `Votre nom, votre site et votre photo viennent de votre profil, commun à tous les modules. ${sending}`
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
function buildSettingsForm(settings: SiteCareSettings): SiteCareSettingsForm {
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
    presenterRole: settings.presenter.role,
    presenterTagline: settings.presenter.tagline,
  }
}

/**
 * The settings to send: the form's values back in cents, in the shape the API gave them.
 * @param editedForm - The form as edited.
 * @param currentSettings - The settings the form was built from.
 * @returns The settings to save; the API keeps the name, the site and the photo of the profile.
 */
function buildSettingsToSave(editedForm: SiteCareSettingsForm, currentSettings: SiteCareSettings): SiteCareSettings {
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
      ...currentSettings.presenter,
      role: editedForm.presenterRole.trim(),
      tagline: editedForm.presenterTagline.trim(),
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
  form.value = buildSettingsForm(settings)
  savedFormSnapshot.value = JSON.stringify(buildSettingsForm(settings))
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
  saveFailureMessage.value = null
  try {
    showSettings(await SiteCareService.saveSettings(buildSettingsToSave(form.value, savedSettings.value)))
    toast.success('Réglages enregistrés.')
  } catch (error: unknown) {
    saveFailureMessage.value = SiteCareService.failureMessage(error, 'Les réglages n’ont pas pu être enregistrés.')
  } finally {
    isSaving.value = false
  }
}

/** Open the profile, where the name, the site and the photo of every module are changed. */
function openProfile(): void {
  drawerStack.push({ kind: 'profile' })
}

onMounted(async (): Promise<void> => {
  await Promise.all([loadSettings(), ensureProfilePhotoLoaded()])
})
</script>
