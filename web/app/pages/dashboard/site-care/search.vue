<template>
  <div class="flex min-h-full flex-col">
    <div class="mb-5">
      <NuxtLink
        :to="SITE_CARE_SECTION_PATH"
        class="inline-flex min-h-11 items-center gap-1.5 text-[13px] font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
      >
        <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
        Mes prospects
      </NuxtLink>
      <h1 class="app-page-title mt-1">Nouvelle recherche</h1>
    </div>

    <UiLoader v-if="isLoadingOptions" label="Chargement de la recherche…" />

    <UiEmptyState
      v-else-if="searchOptions === null"
      title="Chargement impossible"
      description="Les métiers et les pays n’ont pas pu être chargés. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="btn-secondary" @click="loadSearchOptions">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <template v-else>
      <UiWizardStepper :model-value="currentStep" :steps="SEARCH_STEPS" class="mb-6" @update:model-value="goToStep" />

      <div class="flex min-w-0 flex-1 flex-col">
        <div v-if="currentStep === 1" class="wizard-step space-y-5 pb-20">
          <div class="app-card space-y-5 p-5 @2xl:p-6">
            <div>
              <h2 id="site-care-search-trades-title" class="text-base font-semibold text-[var(--app-ink)]">
                Métiers recherchés
              </h2>
              <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
                Cochez autant de métiers que vous voulez. Sans métier coché, la recherche prend toutes les entreprises
                de la zone.
              </p>
            </div>

            <div class="flex flex-wrap gap-2" role="group" aria-labelledby="site-care-search-trades-title">
              <button
                v-for="trade in tradeChoices"
                :key="trade.key"
                type="button"
                :class="choiceChipClass(trade.isSelected)"
                :aria-pressed="trade.isSelected"
                :disabled="trade.availableCount === 0"
                @click="toggleTrade(trade.key)"
              >
                {{ trade.label }}
                <span class="font-[family-name:var(--app-font-mono)] text-xs opacity-70">
                  {{ trade.availableCount }}
                </span>
              </button>
            </div>

            <div class="space-y-1.5 text-[13px] leading-relaxed text-[var(--app-ink-soft)]">
              <p v-if="selectedCountry">
                Le nombre à côté de chaque métier compte les entreprises disponibles. Pays choisi :
                {{ selectedCountry.label }}.
              </p>
              <p>
                Un métier manque ? Lancez une recherche du module Sites web sur ce métier : les entreprises qui ont déjà
                un site arrivent ici.
              </p>
            </div>

            <div class="border-t border-[var(--app-line-soft)] pt-5">
              <label for="site-care-search-count" class="app-label mb-1.5 block">Nombre de prospects</label>
              <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
                <input
                  id="site-care-search-count"
                  v-model.number="wantedProspectCount"
                  type="number"
                  inputmode="numeric"
                  min="1"
                  step="1"
                  class="app-input w-28"
                />
                <p class="text-sm text-[var(--app-ink-soft)]">{{ wantedProspectCountHint }}</p>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="currentStep === 2" class="wizard-step space-y-5 pb-20">
          <div class="app-card space-y-5 p-5 @2xl:p-6">
            <div>
              <h2 id="site-care-search-country-title" class="text-base font-semibold text-[var(--app-ink)]">Pays</h2>
              <div class="mt-3 flex flex-wrap gap-2" role="radiogroup" aria-labelledby="site-care-search-country-title">
                <button
                  v-for="country in searchOptions.countries"
                  :key="country.code"
                  type="button"
                  role="radio"
                  :aria-checked="country.code === selectedCountryCode"
                  :class="choiceChipClass(country.code === selectedCountryCode)"
                  @click="selectCountry(country.code)"
                >
                  {{ country.label }}
                  <span class="font-[family-name:var(--app-font-mono)] text-xs opacity-70">
                    {{ country.available_count }}
                  </span>
                </button>
              </div>
            </div>

            <div class="border-t border-[var(--app-line-soft)] pt-5">
              <label for="site-care-search-city" class="text-base font-semibold text-[var(--app-ink)]">
                Villes
                <span class="text-sm font-normal text-[var(--app-ink-soft)]">(facultatif)</span>
              </label>
              <p class="mt-1 text-sm text-[var(--app-ink-soft)]">
                Laissez vide : l’app choisit les villes et en change jusqu’au compte.
              </p>
              <ul v-if="cities.length > 0" class="mt-3 flex flex-wrap gap-2">
                <li v-for="city in cities" :key="city">
                  <button
                    type="button"
                    :class="choiceChipClass(true)"
                    :aria-label="`Retirer ${city}`"
                    @click="removeCity(city)"
                  >
                    {{ city }}
                    <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
                  </button>
                </li>
              </ul>
              <form class="mt-3 flex gap-2 @2xl:max-w-md" @submit.prevent="addTypedCity">
                <input
                  id="site-care-search-city"
                  v-model="cityInput"
                  type="text"
                  autocomplete="off"
                  placeholder="Ajouter une ville"
                  class="app-input min-w-0 flex-1"
                />
                <button
                  type="submit"
                  class="btn-secondary shrink-0 disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="cityInput.trim() === ''"
                >
                  Ajouter
                </button>
              </form>
            </div>
          </div>
        </div>

        <div v-else-if="currentStep === 3" class="wizard-step space-y-5 pb-20">
          <div class="app-card space-y-5 p-5 @2xl:p-6">
            <div>
              <h2 id="site-care-search-channel-title" class="text-base font-semibold text-[var(--app-ink)]">
                Comment les joindre
              </h2>
              <ul class="mt-3 grid gap-2" aria-labelledby="site-care-search-channel-title">
                <li
                  v-for="channel in CONTACT_CHANNEL_CHOICES"
                  :key="channel.key"
                  class="flex items-start gap-3 rounded-xl border px-3.5 py-3"
                  :class="
                    channel.isSelected
                      ? 'border-[var(--app-ink)] bg-[var(--app-surface-2)]'
                      : 'border-[var(--app-line)] opacity-70'
                  "
                  :aria-current="channel.isSelected ? 'true' : undefined"
                >
                  <UIcon :name="channel.icon" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-ink)]" />
                  <span class="min-w-0 flex-1">
                    <span class="flex flex-wrap items-center gap-2 text-sm font-medium text-[var(--app-ink)]">
                      {{ channel.label }}
                      <span v-if="!channel.isAvailable" class="app-badge">Bientôt</span>
                    </span>
                    <span class="mt-0.5 block text-xs leading-relaxed text-[var(--app-ink-soft)]">
                      {{ channel.description }}
                    </span>
                  </span>
                  <span
                    class="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border"
                    :class="
                      channel.isSelected ? 'border-[var(--app-ink)] bg-[var(--app-ink)]' : 'border-[var(--app-faint)]'
                    "
                  >
                    <UIcon v-if="channel.isSelected" name="i-lucide-check" class="h-3 w-3 text-[var(--app-bg)]" />
                  </span>
                </li>
              </ul>
            </div>

            <div class="border-t border-[var(--app-line-soft)] pt-5">
              <p class="app-label mb-2">Site web</p>
              <p class="text-sm leading-relaxed text-[var(--app-ink-soft)]">
                Ce module garde les entreprises qui ont un site en ligne. Le site de chacune est regardé pendant la
                recherche.
              </p>
            </div>
          </div>
        </div>

        <div v-else class="wizard-step space-y-5 pb-20">
          <div class="app-card space-y-5 p-5 @2xl:p-6">
            <h2 class="text-base font-semibold text-[var(--app-ink)]">Objectif</h2>
            <dl class="divide-y divide-[var(--app-line-soft)]">
              <div
                v-for="row in recapRows"
                :key="row.label"
                class="flex flex-col gap-0.5 py-2.5 first:pt-0 @2xl:flex-row @2xl:items-baseline @2xl:justify-between @2xl:gap-6"
              >
                <dt class="app-label @2xl:shrink-0">{{ row.label }}</dt>
                <dd class="min-w-0 text-sm font-medium break-words text-[var(--app-ink)] @2xl:text-right">
                  {{ row.value }}
                </dd>
              </div>
            </dl>
            <p class="text-sm text-[var(--app-ink-soft)]">Les entreprises déjà connues ne sont jamais reprises.</p>
            <p v-if="hasNoAvailableBusiness" class="text-sm text-[var(--app-red)]">
              Aucune entreprise disponible pour ces critères.
            </p>
            <p v-if="launchFailureMessage" class="text-sm leading-relaxed text-[var(--app-red)]" role="alert">
              {{ launchFailureMessage }}
            </p>
            <div
              v-if="launchedSearch"
              class="flex items-start gap-3 rounded-xl bg-[var(--app-green-soft)] p-4 text-sm leading-relaxed text-[var(--app-green)]"
              role="status"
            >
              <UIcon name="i-lucide-check" class="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                Recherche lancée. Vous pouvez changer de page pendant qu’elle tourne : les prospects arrivent dans « Mes
                prospects » au fur et à mesure.
              </span>
            </div>
          </div>
        </div>

        <!-- Stuck to the bottom of the scrolling area, like the core's search wizard; on a phone the main button takes the width. -->
        <div
          class="sticky bottom-0 z-10 mt-auto flex items-center gap-2 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)]/90 p-1.5 shadow-lg backdrop-blur sm:justify-between sm:gap-3 sm:px-3 sm:py-2"
        >
          <button
            v-if="currentStep > 1 && launchedSearch === null"
            type="button"
            class="btn-secondary h-11 disabled:cursor-not-allowed disabled:opacity-50 sm:h-9"
            :disabled="isLaunching"
            @click="goToStep(currentStep - 1)"
          >
            <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
            Précédent
          </button>
          <span v-else class="hidden sm:block" />

          <button
            v-if="currentStep < SEARCH_STEPS.length"
            type="button"
            class="btn-primary h-11 flex-1 disabled:cursor-not-allowed disabled:opacity-50 sm:h-9 sm:flex-none"
            :disabled="!canContinue"
            @click="goToStep(currentStep + 1)"
          >
            Suivant
            <UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
          </button>
          <NuxtLink
            v-else-if="launchedSearch"
            :to="SITE_CARE_SECTION_PATH"
            class="btn-primary h-11 flex-1 sm:h-9 sm:flex-none"
          >
            Voir mes prospects
          </NuxtLink>
          <button
            v-else
            type="button"
            class="btn-primary h-11 flex-1 disabled:cursor-not-allowed disabled:opacity-50 sm:h-9 sm:flex-none"
            :disabled="!canLaunch"
            @click="launchSearch"
          >
            <UIcon
              :name="isLaunching ? 'i-lucide-loader-circle' : 'i-lucide-search'"
              class="h-3.5 w-3.5"
              :class="{ 'animate-spin': isLaunching }"
            />
            Lancer la recherche
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { UseDashboardScrollReturn } from '~/types/Composables'
import type { UiWizardStep } from '~/types/UiWizardStepper'
import type {
  SiteCareSearch,
  SiteCareSearchCountryOption,
  SiteCareSearchOptions,
  SiteCareSearchTradeOption,
} from '../../../types/SiteCareSearch'
import type {
  SiteCareContactChannelChoice,
  SiteCareSearchRecapRow,
  SiteCareSearchTradeChoice,
} from '../../../types/SiteCareSearchPage'
import { computed, onMounted, ref } from 'vue'
import { useDashboardScroll } from '~/composables/useDashboardScroll'
import { SITE_CARE_SECTION_PATH } from '../../../constants/siteCareModule'
import { SiteCareService } from '../../../services/siteCareService'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Nouvelle recherche · DevLeadHunter' })

const { scrollToTop }: UseDashboardScrollReturn = useDashboardScroll()

const SEARCH_STEPS: UiWizardStep[] = [
  { id: 1, label: 'Cible' },
  { id: 2, label: 'Zone' },
  { id: 3, label: 'Critères' },
  { id: 4, label: 'Lancer' },
]

const DEFAULT_WANTED_PROSPECT_COUNT: number = 50

/** Email only for now: the SMS fallback is shown so it is known to come, but it cannot be picked. */
const CONTACT_CHANNEL_CHOICES: SiteCareContactChannelChoice[] = [
  {
    key: 'email',
    label: 'Par email',
    description:
      'Seules les entreprises dont on trouve l’adresse e-mail deviennent des prospects. Les autres sont gardées à part, dans « Sans email ».',
    icon: 'i-lucide-mail',
    isSelected: true,
    isAvailable: true,
  },
  {
    key: 'email-or-sms',
    label: 'Par email, sinon par SMS',
    description: 'Sans adresse e-mail, un numéro de portable suffit.',
    icon: 'i-lucide-message-square-text',
    isSelected: false,
    isAvailable: false,
  },
]

const searchOptions: Ref<SiteCareSearchOptions | null> = ref(null)
const isLoadingOptions: Ref<boolean> = ref(true)
const currentStep: Ref<number> = ref(1)
const selectedTradeKeys: Ref<string[]> = ref([])
const selectedCountryCode: Ref<string | null> = ref(null)
const cities: Ref<string[]> = ref([])
const cityInput: Ref<string> = ref('')
const wantedProspectCount: Ref<number> = ref(DEFAULT_WANTED_PROSPECT_COUNT)
const isLaunching: Ref<boolean> = ref(false)
const launchedSearch: Ref<SiteCareSearch | null> = ref(null)
const launchFailureMessage: Ref<string | null> = ref(null)

const selectedCountry: ComputedRef<SiteCareSearchCountryOption | null> = computed(
  (): SiteCareSearchCountryOption | null =>
    searchOptions.value?.countries.find(
      (country: SiteCareSearchCountryOption): boolean => country.code === selectedCountryCode.value,
    ) ?? null,
)

const tradeChoices: ComputedRef<SiteCareSearchTradeChoice[]> = computed((): SiteCareSearchTradeChoice[] =>
  (searchOptions.value?.trades ?? []).map(
    (trade: SiteCareSearchTradeOption): SiteCareSearchTradeChoice => ({
      key: trade.key,
      label: trade.label,
      availableCount: availableTradeCount(trade, selectedCountryCode.value),
      isSelected: selectedTradeKeys.value.includes(trade.key),
    }),
  ),
)

const selectedTradeChoices: ComputedRef<SiteCareSearchTradeChoice[]> = computed((): SiteCareSearchTradeChoice[] =>
  tradeChoices.value.filter((trade: SiteCareSearchTradeChoice): boolean => trade.isSelected),
)

const hasValidWantedProspectCount: ComputedRef<boolean> = computed(
  (): boolean => Number.isInteger(wantedProspectCount.value) && wantedProspectCount.value >= 1,
)

const wantedProspectCountHint: ComputedRef<string> = computed((): string =>
  selectedTradeChoices.value.length > 1
    ? `en tout, répartis entre les ${selectedTradeChoices.value.length} métiers`
    : 'en tout',
)

/** Businesses available for the country and trades chosen; the cities typed are not counted here. */
const availableBusinessCount: ComputedRef<number> = computed((): number => {
  if (selectedCountry.value === null) {
    return 0
  }

  if (selectedTradeChoices.value.length === 0) {
    return selectedCountry.value.available_count
  }
  return selectedTradeChoices.value.reduce(
    (total: number, trade: SiteCareSearchTradeChoice): number => total + trade.availableCount,
    0,
  )
})

const hasNoAvailableBusiness: ComputedRef<boolean> = computed(
  (): boolean => cities.value.length === 0 && availableBusinessCount.value === 0,
)

const recapRows: ComputedRef<SiteCareSearchRecapRow[]> = computed((): SiteCareSearchRecapRow[] => {
  const countryLabel: string = selectedCountry.value?.label ?? ''
  const hasTypedCities: boolean = cities.value.length > 0
  return [
    {
      label: 'Métiers',
      value:
        selectedTradeChoices.value.length === 0
          ? 'Tous les métiers'
          : selectedTradeChoices.value.map((trade: SiteCareSearchTradeChoice): string => trade.label).join(', '),
    },
    { label: 'Nombre', value: countedLabel(wantedProspectCount.value, 'prospect', 'prospects') },
    {
      label: 'Zone',
      value: hasTypedCities
        ? `${countryLabel} : ${cities.value.join(', ')}`
        : `${countryLabel}, villes choisies par l’app`,
    },
    { label: 'Joindre', value: 'Par email' },
    {
      label: 'Disponibles',
      value: hasTypedCities
        ? 'Le compte est vérifié au lancement'
        : countedLabel(availableBusinessCount.value, 'entreprise', 'entreprises'),
    },
  ]
})

const canContinue: ComputedRef<boolean> = computed(
  (): boolean => hasValidWantedProspectCount.value && selectedCountry.value !== null,
)

const canLaunch: ComputedRef<boolean> = computed(
  (): boolean =>
    canContinue.value && !hasNoAvailableBusiness.value && !isLaunching.value && launchedSearch.value === null,
)

/**
 * How many businesses of a trade are available in a country.
 * @param trade - The trade, with its counts by country.
 * @param countryCode - The country chosen, or null before the options are read.
 * @returns The count, 0 when the trade has no business there.
 */
function availableTradeCount(trade: SiteCareSearchTradeOption, countryCode: string | null): number {
  return countryCode === null ? 0 : (trade.available_by_country[countryCode] ?? 0)
}

/**
 * Write a count with its noun, singular or plural.
 * @param count - The count.
 * @param singular - The noun for one.
 * @param plural - The noun for several.
 * @returns The count followed by its noun (« 50 prospects »).
 */
function countedLabel(count: number, singular: string, plural: string): string {
  return `${count} ${count > 1 ? plural : singular}`
}

/**
 * Classes of a chip that can be picked: filled once picked, outlined otherwise, a finger wide in both cases.
 * @param isSelected - Whether the chip is picked.
 * @returns The Tailwind classes of the chip.
 */
function choiceChipClass(isSelected: boolean): string {
  const base: string =
    'inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border px-4 text-sm transition-colors focus-visible:ring-2 focus-visible:ring-[var(--app-ink-soft)] focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50'
  return isSelected
    ? `${base} border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-bg)]`
    : `${base} border-[var(--app-line)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]`
}

/**
 * Tick a trade, or untick it.
 * @param tradeKey - The key of the trade clicked.
 */
function toggleTrade(tradeKey: string): void {
  selectedTradeKeys.value = selectedTradeKeys.value.includes(tradeKey)
    ? selectedTradeKeys.value.filter((selectedKey: string): boolean => selectedKey !== tradeKey)
    : [...selectedTradeKeys.value, tradeKey]
}

/**
 * Choose the country of the search; the trades ticked that have no business there are unticked.
 * @param countryCode - The code of the country clicked.
 */
function selectCountry(countryCode: string): void {
  selectedCountryCode.value = countryCode
  selectedTradeKeys.value = (searchOptions.value?.trades ?? [])
    .filter(
      (trade: SiteCareSearchTradeOption): boolean =>
        selectedTradeKeys.value.includes(trade.key) && availableTradeCount(trade, countryCode) > 0,
    )
    .map((trade: SiteCareSearchTradeOption): string => trade.key)
}

/** Add the city typed to the list, once, then empty the field. */
function addTypedCity(): void {
  const typedCity: string = cityInput.value.trim()
  const isAlreadyListed: boolean = cities.value.some(
    (city: string): boolean => city.toLowerCase() === typedCity.toLowerCase(),
  )
  if (typedCity !== '' && !isAlreadyListed) {
    cities.value = [...cities.value, typedCity]
  }
  cityInput.value = ''
}

/**
 * Take a city out of the list.
 * @param removedCity - The city to remove.
 */
function removeCity(removedCity: string): void {
  cities.value = cities.value.filter((city: string): boolean => city !== removedCity)
}

/**
 * Show a step and bring the page back to its top; a city still in the field is kept. Nothing moves once the
 * search is launched.
 * @param step - Target step (1-based).
 */
function goToStep(step: number): void {
  if (isLaunching.value || launchedSearch.value !== null) {
    return
  }

  if (step > currentStep.value && !canContinue.value) {
    return
  }
  addTypedCity()
  currentStep.value = Math.min(Math.max(step, 1), SEARCH_STEPS.length)
  scrollToTop()
}

/**
 * Read the countries and trades a search can target, and choose the first country.
 * @returns A promise resolved once the options are shown, or the failure is.
 */
async function loadSearchOptions(): Promise<void> {
  isLoadingOptions.value = true
  try {
    const options: SiteCareSearchOptions = await SiteCareService.getSearchOptions()
    searchOptions.value = options
    selectedCountryCode.value = options.countries[0]?.code ?? null
  } catch {
    searchOptions.value = null
  } finally {
    isLoadingOptions.value = false
  }
}

/**
 * Launch the search with the criteria chosen; a refusal of the API (a search already running) is written in plain.
 * @returns A promise resolved once the search is launched, or the refusal is shown.
 */
async function launchSearch(): Promise<void> {
  const country: SiteCareSearchCountryOption | null = selectedCountry.value
  if (!canLaunch.value || country === null) {
    return
  }
  isLaunching.value = true
  launchFailureMessage.value = null
  try {
    launchedSearch.value = await SiteCareService.startSearch({
      trades: selectedTradeChoices.value.map((trade: SiteCareSearchTradeChoice): string => trade.key),
      country: country.code,
      cities: cities.value,
      count: wantedProspectCount.value,
    })
  } catch (error: unknown) {
    launchFailureMessage.value = SiteCareService.failureMessage(
      error,
      'La recherche n’a pas pu être lancée. Réessayez dans un instant.',
    )
  } finally {
    isLaunching.value = false
  }
}

onMounted(async (): Promise<void> => {
  await loadSearchOptions()
})
</script>

<style scoped>
.wizard-step {
  animation: wizard-step-in 0.3s ease;
}
@keyframes wizard-step-in {
  from {
    opacity: 0;
    transform: translateX(18px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .wizard-step {
    animation: none;
  }
}
</style>
