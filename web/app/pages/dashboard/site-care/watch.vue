<template>
  <div class="flex min-h-full flex-col gap-6">
    <SiteCarePageHeader
      title="Veille"
      :description="watchBoard?.summary_line ?? null"
      info-text="Chaque site est relu tous les sept jours. La veille montre ce qui a changé depuis la lecture d’avant, et les dates après lesquelles d’autres sites auront un souci. Ouvrez-la le matin et commencez par la colonne de gauche."
    />

    <UiLoader v-if="watchBoard === null && isLoadingWatch" label="Chargement de la veille…" />

    <UiEmptyState
      v-else-if="watchBoard === null"
      title="Chargement impossible"
      description="La veille n’a pas pu être chargée. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="app-btn-secondary" @click="loadWatch">
          <UIcon name="i-lucide-refresh-cw" class="h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <UiEmptyState
      v-else-if="watchBoard.summary_line === null"
      title="Aucun site à surveiller pour le moment"
      description="Lancez une recherche : chaque site trouvé est relu tous les sept jours, et ce qui change arrive ici."
    >
      <template #action>
        <SiteCareButton :to="SITE_CARE_SEARCH_PATH" leading-icon="i-lucide-search">Nouvelle recherche</SiteCareButton>
      </template>
    </UiEmptyState>

    <div v-else class="grid grid-cols-1 items-start gap-4 @4xl:grid-cols-3">
      <SiteCareBoardColumn
        title="Nouveaux soucis"
        hint="À écrire en premier : c’est récent."
        tone="red"
        :count="watchBoard.new_issues.length"
        empty-text="Rien de nouveau cette semaine."
      >
        <SiteCareWatchSiteCard
          v-for="siteChange in watchBoard.new_issues"
          :key="siteChange.key"
          :site-change="siteChange"
        />
      </SiteCareBoardColumn>

      <SiteCareBoardColumn
        title="Dates qui approchent"
        hint="Ces sites auront un souci après la date."
        tone="amber"
        :count="watchBoard.upcoming_dates.length"
        empty-text="Aucune date dans les semaines qui viennent."
      >
        <SiteCareWatchDateCard
          v-for="watchDate in watchBoard.upcoming_dates"
          :key="watchDate.key"
          :watch-date="watchDate"
        />
      </SiteCareBoardColumn>

      <SiteCareBoardColumn
        title="Sites disparus"
        hint="Leur adresse ne répond plus."
        tone="neutral"
        :count="watchBoard.gone_sites.length"
        empty-text="Aucun site n’a disparu cette semaine."
      >
        <SiteCareWatchSiteCard
          v-for="siteChange in watchBoard.gone_sites"
          :key="siteChange.key"
          :site-change="siteChange"
        />
      </SiteCareBoardColumn>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { Ref } from 'vue'
import type { SiteCareWatchResponse } from '../../../types/SiteCareWatch'
import { onMounted, ref } from 'vue'
import { SITE_CARE_SEARCH_PATH } from '../../../constants/siteCareModule'
import { SiteCareService } from '../../../services/siteCareService'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Veille · DevLeadHunter' })

const watchBoard: Ref<SiteCareWatchResponse | null> = ref(null)
const isLoadingWatch: Ref<boolean> = ref(true)

/**
 * Read the watch.
 * @returns A promise resolved once the board is shown, or the failure is.
 */
async function loadWatch(): Promise<void> {
  isLoadingWatch.value = true
  try {
    watchBoard.value = await SiteCareService.getWatch()
  } catch {
    watchBoard.value = null
  } finally {
    isLoadingWatch.value = false
  }
}

onMounted(async (): Promise<void> => {
  await loadWatch()
})
</script>
