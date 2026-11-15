<template>
  <div class="flex min-h-full flex-col gap-7">
    <div class="flex items-center">
      <SiteCareBackLink :to="SITE_CARE_SECTION_PATH">Mes prospects</SiteCareBackLink>
    </div>

    <UiLoader v-if="isLoadingOptions" label="Chargement de la recherche…" />

    <UiEmptyState
      v-else-if="searchOptions === null"
      title="Chargement impossible"
      description="Les métiers et les départements n’ont pas pu être chargés. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="app-btn-secondary" @click="loadSearchOptions">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <div v-else class="flex flex-wrap items-start gap-7">
      <div class="flex min-w-0 flex-[999_1_30rem] flex-col gap-5">
        <SiteCarePageHeader
          title="Nouvelle recherche"
          description="Fait entrer dans le module des entreprises qui ont déjà un site."
          has-large-title
        />

        <template v-if="launchedSearch === null">
          <SiteCareCard v-if="currentStep === 'source'" title="Où chercher" title-id="site-care-search-source-title">
            <div class="flex flex-col" role="radiogroup" aria-labelledby="site-care-search-source-title">
              <SiteCareChoiceRow
                v-for="source in searchOptions.sources"
                :key="source.key"
                :title="source.label"
                :description="source.hint"
                :is-selected="source.key === selectedSource"
                @click="selectedSource = source.key"
              >
                <template #leading>
                  <span
                    class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
                    :class="SEARCH_SOURCE_TILE_CLASSES[source.key]"
                    aria-hidden="true"
                  >
                    <UIcon :name="SEARCH_SOURCE_ICONS[source.key]" class="h-[18px] w-[18px]" />
                  </span>
                </template>
              </SiteCareChoiceRow>
            </div>
          </SiteCareCard>

          <template v-else-if="currentStep === 'zone' && isSearchingOpenMap">
            <SiteCareCard title="Les départements">
              <template #info>
                <SiteCareInfoTip
                  accessible-label="À propos des départements"
                  info-text="La recherche lit tous les sites d’un département avant de passer au suivant. Les départements d’outre-mer ne sont pas proposés."
                />
              </template>
              <SiteCareDepartmentPicker
                v-model="selectedDepartmentCodes"
                :departments="searchOptions.open_map.departments"
                :maximum-count="searchOptions.open_map.max_departments"
              />
            </SiteCareCard>

            <SiteCareCard title="Les types d’entreprises">
              <template #info>
                <SiteCareInfoTip
                  accessible-label="À propos des types d’entreprises"
                  info-text="Sans rien cocher, la recherche prend toutes les entreprises. Les enseignes, les réseaux, les organismes publics et les associations sont laissés de côté."
                />
              </template>
              <div class="flex flex-wrap gap-2" role="group" aria-label="Types d’entreprises">
                <SiteCareChoiceChip
                  v-for="family in searchOptions.open_map.families"
                  :key="family.key"
                  :is-selected="selectedFamilyKeys.includes(family.key)"
                  @click="toggleFamily(family.key)"
                >
                  {{ family.label }}
                </SiteCareChoiceChip>
              </div>
            </SiteCareCard>
          </template>

          <template v-else-if="currentStep === 'zone'">
            <SiteCareCard v-if="searchOptions.countries.length > 1" title="Le pays">
              <div class="flex flex-wrap gap-2" role="group" aria-label="Pays">
                <SiteCareChoiceChip
                  v-for="country in searchOptions.countries"
                  :key="country.code"
                  :is-selected="country.code === selectedCountryCode"
                  @click="selectCountry(country.code)"
                >
                  {{ country.label }}
                  <span class="text-sm opacity-70">{{ country.available_count }}</span>
                </SiteCareChoiceChip>
              </div>
            </SiteCareCard>

            <SiteCareCard title="Les métiers">
              <template #info>
                <SiteCareInfoTip
                  accessible-label="À propos des métiers"
                  info-text="Sans métier coché, la recherche prend toutes les entreprises du pays. Le nombre compte les entreprises disponibles. Un métier manque ? Lancez une recherche du module Sites web sur ce métier : les entreprises qui ont déjà un site arrivent ici."
                />
              </template>
              <div class="flex flex-wrap gap-2" role="group" aria-label="Métiers">
                <SiteCareChoiceChip
                  v-for="trade in tradeChoices"
                  :key="trade.key"
                  :is-selected="trade.isSelected"
                  :is-disabled="trade.availableCount === 0"
                  @click="toggleTrade(trade.key)"
                >
                  {{ trade.label }}
                  <span class="text-sm opacity-70">{{ trade.availableCount }}</span>
                </SiteCareChoiceChip>
              </div>
            </SiteCareCard>

            <SiteCareCard title="Les villes">
              <template #info>
                <SiteCareInfoTip
                  accessible-label="À propos des villes"
                  info-text="Facultatif. Sans ville, l’app choisit les villes du pays et en change jusqu’à atteindre le nombre demandé."
                />
              </template>
              <div v-if="cities.length > 0" class="flex flex-wrap gap-2" role="group" aria-label="Villes choisies">
                <SiteCareChoiceChip
                  v-for="city in cities"
                  :key="city"
                  is-selected
                  :aria-label="`Retirer ${city}`"
                  @click="removeCity(city)"
                >
                  {{ city }}
                </SiteCareChoiceChip>
              </div>
              <form class="flex max-w-md flex-wrap gap-2" @submit.prevent="addTypedCity">
                <input
                  v-model="cityInput"
                  type="text"
                  autocomplete="off"
                  placeholder="Ajouter une ville"
                  aria-label="Ville à ajouter"
                  class="app-input h-10 min-w-0 flex-[999_1_12rem] rounded-full px-4 text-sm"
                />
                <SiteCareButton type="submit" class="flex-[1_1_auto]" :is-disabled="cityInput.trim() === ''">
                  Ajouter
                </SiteCareButton>
              </form>
            </SiteCareCard>
          </template>

          <template v-else>
            <SiteCareCard v-if="isSearchingOpenMap" title="Les sites à garder" title-id="site-care-search-keep-title">
              <template #info>
                <SiteCareInfoTip
                  accessible-label="À propos des sites gardés"
                  info-text="Chaque site de la zone est lu. Un site lu n’est jamais relu par une recherche suivante, qu’il ait été gardé ou non."
                />
              </template>
              <div class="flex flex-col" role="radiogroup" aria-labelledby="site-care-search-keep-title">
                <SiteCareChoiceRow
                  v-for="keepRule in searchOptions.open_map.keep_rules"
                  :key="keepRule.key"
                  :title="keepRule.label"
                  :description="keepRule.hint"
                  :is-selected="keepRule.key === selectedKeepRule"
                  @click="selectedKeepRule = keepRule.key"
                />
              </div>
            </SiteCareCard>

            <SiteCareCard title="Combien de prospects, au plus" title-id="site-care-search-count-title">
              <div
                class="inline-flex flex-wrap gap-1 self-start rounded-[14px] bg-[var(--app-surface-2)] p-1"
                role="radiogroup"
                aria-labelledby="site-care-search-count-title"
              >
                <button
                  v-for="countChoice in countChoices"
                  :key="countChoice"
                  type="button"
                  role="radio"
                  :aria-checked="countChoice === wantedProspectCount"
                  class="min-h-11 cursor-pointer rounded-[10px] px-5 text-[15px] transition-colors"
                  :class="
                    countChoice === wantedProspectCount
                      ? 'bg-[var(--app-btn-bg)] font-semibold text-[var(--app-btn-text)]'
                      : 'font-medium text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
                  "
                  @click="wantedProspectCount = countChoice"
                >
                  {{ countChoice.toLocaleString('fr-FR') }}
                </button>
              </div>
              <p class="text-sm text-[var(--app-ink-soft)]">{{ countHint }}</p>
            </SiteCareCard>

            <p v-if="isSearchingOpenMap" class="text-sm text-[var(--app-ink-soft)]">
              {{ searchOptions.open_map.credit }}
            </p>
          </template>
        </template>

        <SiteCareOutcomeCard v-else title="Recherche lancée" :description="launchedLine" />
      </div>

      <SiteCareStepActionCard
        class="flex-[1_1_22rem] @4xl:max-w-[26rem]"
        :title="stepTitle"
        :step-count="SEARCH_STEPS.length"
        :reached-step-count="reachedStepCount"
      >
        <dl class="flex flex-col">
          <div
            v-for="recapRow in recapRows"
            :key="recapRow.label"
            class="flex items-baseline justify-between gap-4 border-t border-[var(--app-line)] py-3 first:border-t-0 first:pt-0"
          >
            <dt class="shrink-0 text-[13px] font-medium text-[var(--app-ink-soft)]">{{ recapRow.label }}</dt>
            <dd class="min-w-0 text-right text-[15px] font-semibold break-words text-[var(--app-ink)]">
              {{ recapRow.value }}
            </dd>
          </div>
        </dl>

        <p v-if="blockerMessage" class="text-sm text-[var(--app-ink-soft)]">{{ blockerMessage }}</p>
        <p v-if="launchFailureMessage" class="text-sm leading-relaxed text-[var(--app-red)]" role="alert">
          {{ launchFailureMessage }}
        </p>

        <div class="flex flex-col gap-2.5">
          <template v-if="launchedSearch === null">
            <SiteCareButton
              v-if="currentStep !== 'keep'"
              size="large"
              class="w-full"
              trailing-icon="i-lucide-arrow-right"
              :is-disabled="!canContinue"
              @click="goToNextStep"
            >
              Continuer
            </SiteCareButton>
            <SiteCareButton
              v-else
              size="large"
              class="w-full"
              leading-icon="i-lucide-search"
              :is-disabled="!canLaunch"
              :is-loading="isLaunching"
              @click="launchSearch"
            >
              Lancer la recherche
            </SiteCareButton>
            <SiteCareButton
              v-if="currentStep !== 'source'"
              variant="secondary"
              size="large"
              class="w-full"
              leading-icon="i-lucide-arrow-left"
              :is-disabled="isLaunching"
              @click="goToPreviousStep"
            >
              Revenir
            </SiteCareButton>
          </template>
          <SiteCareButton v-else :to="SITE_CARE_SECTION_PATH" size="large" class="w-full">
            Voir mes prospects
          </SiteCareButton>
        </div>
      </SiteCareStepActionCard>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { UseDashboardScrollReturn } from '~/types/Composables'
import type {
  SiteCareSearch,
  SiteCareSearchCountryOption,
  SiteCareSearchCreatePayload,
  SiteCareSearchKeepRule,
  SiteCareSearchLabelledChoice,
  SiteCareSearchOptions,
  SiteCareSearchSource,
  SiteCareSearchTradeOption,
} from '../../../types/SiteCareSearch'
import type {
  SiteCareSearchRecapRow,
  SiteCareSearchStep,
  SiteCareSearchTradeChoice,
} from '../../../types/SiteCareSearchPage'
import { computed, onMounted, ref, watch } from 'vue'
import { useDashboardScroll } from '~/composables/useDashboardScroll'
import { SITE_CARE_SECTION_PATH } from '../../../constants/siteCareModule'
import { SiteCareService } from '../../../services/siteCareService'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Nouvelle recherche · DevLeadHunter' })

const { scrollToTop }: UseDashboardScrollReturn = useDashboardScroll()

const SEARCH_STEPS: SiteCareSearchStep[] = ['source', 'zone', 'keep']

const SEARCH_STEP_NAMES: Record<SiteCareSearchStep, string> = {
  source: 'où chercher',
  zone: 'la zone',
  keep: 'les sites à garder',
}

const OWN_BASE_KEEP_STEP_NAME: string = 'le nombre'

const DEFAULT_WANTED_PROSPECT_COUNT: number = 50
const DEFAULT_OPEN_MAP_WANTED_PROSPECT_COUNT: number = 300

const OWN_BASE_COUNT_CHOICES: number[] = [25, 50, 100, 300]
const OPEN_MAP_COUNT_CHOICES: number[] = [100, 300, 1000, 2000]

const SEARCH_SOURCE_ICONS: Record<SiteCareSearchSource, string> = {
  base: 'i-lucide-database',
  open_map: 'i-lucide-map',
}

const SEARCH_SOURCE_TILE_CLASSES: Record<SiteCareSearchSource, string> = {
  base: 'bg-[var(--app-blue-soft)] text-[var(--app-blue)]',
  open_map: 'bg-[var(--app-green-soft)] text-[var(--app-green)]',
}

const KEEP_RULE_SHORT_LABELS: Record<SiteCareSearchKeepRule, string> = {
  security: 'Avec un souci de sécurité',
  issues: 'Avec un souci',
  all: 'Tous',
}

const searchOptions: Ref<SiteCareSearchOptions | null> = ref(null)
const isLoadingOptions: Ref<boolean> = ref(true)
const currentStep: Ref<SiteCareSearchStep> = ref('source')
const selectedSource: Ref<SiteCareSearchSource> = ref('base')
const selectedTradeKeys: Ref<string[]> = ref([])
const selectedCountryCode: Ref<string | null> = ref(null)
const cities: Ref<string[]> = ref([])
const cityInput: Ref<string> = ref('')
const selectedFamilyKeys: Ref<string[]> = ref([])
const selectedDepartmentCodes: Ref<string[]> = ref([])
const selectedKeepRule: Ref<SiteCareSearchKeepRule> = ref('security')
const wantedProspectCount: Ref<number> = ref(DEFAULT_WANTED_PROSPECT_COUNT)
const isLaunching: Ref<boolean> = ref(false)
const launchedSearch: Ref<SiteCareSearch | null> = ref(null)
const launchFailureMessage: Ref<string | null> = ref(null)

const isSearchingOpenMap: ComputedRef<boolean> = computed((): boolean => selectedSource.value === 'open_map')

const maximumWantedProspectCount: ComputedRef<number> = computed((): number => {
  if (searchOptions.value === null) {
    return DEFAULT_WANTED_PROSPECT_COUNT
  }
  return isSearchingOpenMap.value ? searchOptions.value.open_map.max_count : searchOptions.value.max_count
})

const countChoices: ComputedRef<number[]> = computed((): number[] =>
  (isSearchingOpenMap.value ? OPEN_MAP_COUNT_CHOICES : OWN_BASE_COUNT_CHOICES).filter(
    (countChoice: number): boolean => countChoice <= maximumWantedProspectCount.value,
  ),
)

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

/** Why the search cannot go on from the zone, once the zone is shown. */
const blockerMessage: ComputedRef<string | null> = computed((): string | null => {
  if (currentStep.value === 'source' || launchedSearch.value !== null) {
    return null
  }

  if (isSearchingOpenMap.value) {
    return selectedDepartmentCodes.value.length === 0 ? 'Choisissez au moins un département.' : null
  }
  if (selectedCountry.value === null) {
    return 'Aucun pays n’a d’entreprise disponible.'
  }
  return cities.value.length === 0 && availableBusinessCount.value === 0
    ? 'Aucune entreprise disponible pour ces critères.'
    : null
})

const canContinue: ComputedRef<boolean> = computed(
  (): boolean => currentStep.value === 'source' || blockerMessage.value === null,
)

const hasValidWantedProspectCount: ComputedRef<boolean> = computed(
  (): boolean =>
    Number.isInteger(wantedProspectCount.value) &&
    wantedProspectCount.value >= 1 &&
    wantedProspectCount.value <= maximumWantedProspectCount.value,
)

const canLaunch: ComputedRef<boolean> = computed(
  (): boolean =>
    currentStep.value === 'keep' &&
    blockerMessage.value === null &&
    hasValidWantedProspectCount.value &&
    !isLaunching.value &&
    launchedSearch.value === null,
)

const reachedStepCount: ComputedRef<number> = computed((): number =>
  launchedSearch.value !== null ? SEARCH_STEPS.length : SEARCH_STEPS.indexOf(currentStep.value) + 1,
)

const stepTitle: ComputedRef<string> = computed((): string => {
  if (launchedSearch.value !== null) {
    return 'Recherche lancée'
  }
  const stepName: string =
    currentStep.value === 'keep' && !isSearchingOpenMap.value
      ? OWN_BASE_KEEP_STEP_NAME
      : SEARCH_STEP_NAMES[currentStep.value]
  return `Étape ${reachedStepCount.value} sur ${SEARCH_STEPS.length} : ${stepName}`
})

const countHint: ComputedRef<string> = computed((): string => {
  if (isSearchingOpenMap.value) {
    return 'La recherche s’arrête à ce nombre de sites gardés, ou quand toute la zone est lue.'
  }
  if (cities.value.length > 0) {
    return 'Le nombre d’entreprises disponibles dans ces villes est vérifié au lancement.'
  }
  return `${availableBusinessCount.value} ${availableBusinessCount.value > 1 ? 'entreprises disponibles' : 'entreprise disponible'} pour ces critères. Les entreprises déjà connues ne sont jamais reprises.`
})

const launchedLine: ComputedRef<string> = computed((): string =>
  isSearchingOpenMap.value
    ? 'Elle tourne toute seule : comptez 20 à 40 minutes par département. Les prospects arrivent dans « Mes prospects » au fur et à mesure, et la recherche s’arrête depuis cette page.'
    : 'Elle tourne toute seule. Les prospects arrivent dans « Mes prospects » au fur et à mesure.',
)

const recapRows: ComputedRef<SiteCareSearchRecapRow[]> = computed((): SiteCareSearchRecapRow[] => {
  const sourceLabel: string =
    searchOptions.value?.sources.find(
      (source: SiteCareSearchLabelledChoice<SiteCareSearchSource>): boolean => source.key === selectedSource.value,
    )?.label ?? ''
  const countLabel: string = `${wantedProspectCount.value.toLocaleString('fr-FR')} prospects au plus`
  if (isSearchingOpenMap.value) {
    const departmentLabels: string[] = labelsOfSelectedChoices(
      searchOptions.value?.open_map.departments ?? [],
      selectedDepartmentCodes.value,
    )
    const familyLabels: string[] = labelsOfSelectedChoices(
      searchOptions.value?.open_map.families ?? [],
      selectedFamilyKeys.value,
    )
    return [
      { label: 'Source', value: sourceLabel },
      { label: 'Zone', value: departmentLabels.join(', ') || 'À choisir' },
      { label: 'Entreprises', value: familyLabels.join(', ') || 'Toutes' },
      { label: 'Sites gardés', value: KEEP_RULE_SHORT_LABELS[selectedKeepRule.value] },
      { label: 'Nombre', value: countLabel },
    ]
  }
  return [
    { label: 'Source', value: sourceLabel },
    { label: 'Pays', value: selectedCountry.value?.label ?? 'Aucun' },
    {
      label: 'Métiers',
      value:
        selectedTradeChoices.value.map((trade: SiteCareSearchTradeChoice): string => trade.label).join(', ') || 'Tous',
    },
    { label: 'Villes', value: cities.value.join(', ') || 'Choisies par l’app' },
    { label: 'Nombre', value: countLabel },
  ]
})

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
 * Read the labels of the choices picked, in the order the choices are offered.
 * @param choices - The choices offered.
 * @param selectedKeys - The keys of those picked.
 * @returns The labels of the picked ones.
 */
function labelsOfSelectedChoices(choices: SiteCareSearchLabelledChoice[], selectedKeys: string[]): string[] {
  return choices
    .filter((choice: SiteCareSearchLabelledChoice): boolean => selectedKeys.includes(choice.key))
    .map((choice: SiteCareSearchLabelledChoice): string => choice.label)
}

/**
 * Tick a key of a list of choices, or untick it.
 * @param selectedKeys - The keys ticked.
 * @param clickedKey - The key clicked.
 * @returns The keys ticked afterwards.
 */
function toggleKey(selectedKeys: string[], clickedKey: string): string[] {
  return selectedKeys.includes(clickedKey)
    ? selectedKeys.filter((selectedKey: string): boolean => selectedKey !== clickedKey)
    : [...selectedKeys, clickedKey]
}

/**
 * Tick a trade, or untick it.
 * @param tradeKey - The key of the trade clicked.
 */
function toggleTrade(tradeKey: string): void {
  selectedTradeKeys.value = toggleKey(selectedTradeKeys.value, tradeKey)
}

/**
 * Tick a family of businesses, or untick it.
 * @param familyKey - The key of the family clicked.
 */
function toggleFamily(familyKey: string): void {
  selectedFamilyKeys.value = toggleKey(selectedFamilyKeys.value, familyKey)
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
 * Show a step and bring the page back to its top.
 * @param step - The step to show.
 */
function showStep(step: SiteCareSearchStep): void {
  launchFailureMessage.value = null
  currentStep.value = step
  scrollToTop()
}

/** Go on to the next step, keeping a city still in the field. */
function goToNextStep(): void {
  if (!canContinue.value) {
    return
  }
  addTypedCity()
  const nextStep: SiteCareSearchStep | undefined = SEARCH_STEPS[SEARCH_STEPS.indexOf(currentStep.value) + 1]
  if (nextStep !== undefined) {
    showStep(nextStep)
  }
}

/** Go back to the previous step. */
function goToPreviousStep(): void {
  const previousStep: SiteCareSearchStep | undefined = SEARCH_STEPS[SEARCH_STEPS.indexOf(currentStep.value) - 1]
  if (previousStep !== undefined) {
    showStep(previousStep)
  }
}

/**
 * Write the search asked for, as the API reads it.
 * @returns The body of the request, or null while the base has no country chosen.
 */
function buildSearchPayload(): SiteCareSearchCreatePayload | null {
  if (isSearchingOpenMap.value) {
    return {
      source: 'open_map',
      departments: selectedDepartmentCodes.value,
      families: selectedFamilyKeys.value,
      keep_rule: selectedKeepRule.value,
      count: wantedProspectCount.value,
    }
  }

  if (selectedCountry.value === null) {
    return null
  }
  return {
    source: 'base',
    trades: selectedTradeChoices.value.map((trade: SiteCareSearchTradeChoice): string => trade.key),
    country: selectedCountry.value.code,
    cities: cities.value,
    count: wantedProspectCount.value,
  }
}

/**
 * Read what a search can target, choose the first country, and start on OpenStreetMap when the base is used up.
 * @returns A promise resolved once the options are shown, or the failure is.
 */
async function loadSearchOptions(): Promise<void> {
  isLoadingOptions.value = true
  try {
    const options: SiteCareSearchOptions = await SiteCareService.getSearchOptions()
    searchOptions.value = options
    selectedCountryCode.value = options.countries[0]?.code ?? null
    selectedSource.value = options.countries.length > 0 ? 'base' : 'open_map'
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
  const payload: SiteCareSearchCreatePayload | null = buildSearchPayload()
  if (!canLaunch.value || payload === null) {
    return
  }
  isLaunching.value = true
  launchFailureMessage.value = null
  try {
    launchedSearch.value = await SiteCareService.startSearch(payload)
    scrollToTop()
  } catch (error: unknown) {
    launchFailureMessage.value = SiteCareService.failureMessage(
      error,
      'La recherche n’a pas pu être lancée. Réessayez dans un instant.',
    )
  } finally {
    isLaunching.value = false
  }
}

watch(selectedSource, (source: SiteCareSearchSource): void => {
  wantedProspectCount.value =
    source === 'open_map' ? DEFAULT_OPEN_MAP_WANTED_PROSPECT_COUNT : DEFAULT_WANTED_PROSPECT_COUNT
})

onMounted(async (): Promise<void> => {
  await loadSearchOptions()
})
</script>
