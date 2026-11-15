<template>
  <UiModuleAssistantChat :load-home="SiteCareService.getAssistantHome" :ask-question="SiteCareService.askAssistant">
    <template #card="{ card }">
      <SiteCareSitePreviewCard :site="card" />
    </template>
  </UiModuleAssistantChat>
</template>

<script lang="ts" setup>
import { SiteCareService } from '../../../services/siteCareService'

definePageMeta({ layout: 'dashboard', middleware: ['auth', 'site-care-module'] })

useSeoMeta({ title: 'Assistant · Entretien de sites · DevLeadHunter' })
</script>
