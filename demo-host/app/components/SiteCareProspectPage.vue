<template>
  <main class="font-site-care text-site-care-ink min-h-dvh bg-white text-[17px] leading-7 wrap-break-word antialiased">
    <header class="px-6 pt-14 pb-12 sm:pt-22 sm:pb-16">
      <div class="mx-auto flex w-full max-w-140 flex-col gap-5">
        <p class="text-site-care-ink-soft text-xs font-medium tracking-[0.08em] uppercase">
          Pour {{ props.page.business_name }}
        </p>
        <h1 class="text-[32px] leading-[1.15] font-medium tracking-[-0.01em] text-balance sm:text-[40px]">
          {{ props.page.title.start }}<span class="text-site-care-violet">{{ props.page.title.mark }}</span
          >{{ props.page.title.end }}
        </h1>
        <p class="text-site-care-ink-muted">
          {{ introAroundDomain.beforeDomain
          }}<strong v-if="introAroundDomain.domain" class="text-site-care-ink font-medium">{{
            introAroundDomain.domain
          }}</strong
          >{{ introAroundDomain.afterDomain }}
        </p>
      </div>
    </header>

    <SiteCarePageSection eyebrow="Le constat" heading="Ce que j’ai vu" has-tinted-background>
      <div class="border-site-care-amber-line bg-site-care-amber-soft flex flex-col gap-3 rounded-xl border p-6">
        <p class="text-site-care-amber flex items-center gap-2.5 text-xs font-medium tracking-[0.08em] uppercase">
          <span
            class="inline-flex size-8 flex-none items-center justify-center rounded-full bg-white"
            aria-hidden="true"
          >
            <svg
              class="size-4.5 flex-none"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3M12 9v4M12 17h.01" />
            </svg>
          </span>
          {{ props.page.seen.label }}
        </p>
        <p class="text-[19px] leading-6.75 font-medium">
          {{ props.page.seen.lead }}
        </p>
        <p v-if="props.page.seen.rest" class="text-site-care-ink-muted text-[15px] leading-6">
          {{ props.page.seen.rest }}
        </p>
      </div>
    </SiteCarePageSection>

    <SiteCarePageSection
      v-if="props.page.changes.length > 0"
      eyebrow="Les conséquences"
      heading="Ce que ça change pour vous"
    >
      <ul class="border-site-care-line flex flex-col rounded-xl border bg-white px-6 py-1">
        <li
          v-for="(change, changeIndex) in props.page.changes"
          :key="changeIndex"
          class="border-site-care-line border-t py-4.5 text-base leading-6.5 first:border-t-0"
        >
          {{ change }}
        </li>
      </ul>
    </SiteCarePageSection>

    <SiteCarePageSection
      v-if="props.page.proof_steps.length > 0"
      eyebrow="La preuve"
      heading="Vérifiez-le vous-même"
      has-tinted-background
    >
      <ol class="border-site-care-line flex flex-col rounded-xl border bg-white px-6 py-1">
        <li
          v-for="(proofStep, proofStepIndex) in props.page.proof_steps"
          :key="proofStepIndex"
          class="border-site-care-line border-t py-4.5 text-base leading-6.5 first:border-t-0"
        >
          <span class="text-site-care-violet mb-1 block text-xs font-medium tracking-[0.08em] uppercase">
            Étape {{ proofStepIndex + 1 }}
          </span>
          <p>{{ proofStep }}</p>
        </li>
      </ol>
    </SiteCarePageSection>

    <SiteCarePageSection eyebrow="Le prix" heading="Ce que je vous propose">
      <div class="border-site-care-violet shadow-site-care-offer flex flex-col gap-3 rounded-xl border bg-white p-6">
        <span
          v-if="props.page.offer.tag_label"
          class="bg-site-care-violet self-start rounded-md px-2.5 py-1 text-xs font-medium text-white"
        >
          {{ props.page.offer.tag_label }}
        </span>
        <h3 class="text-site-care-ink-muted text-base leading-[1.35] font-medium">
          {{ props.page.offer.label }}
        </h3>
        <p class="text-[40px] leading-[1.1] font-medium">
          {{ props.page.offer.price_label }}
        </p>
        <p v-if="props.page.offer.note" class="text-site-care-ink-muted text-[15px] leading-6">
          {{ props.page.offer.note }}
        </p>
      </div>
      <ul
        v-if="props.page.offer.reassurances.length > 0"
        class="bg-site-care-lavender-soft flex flex-col gap-3 rounded-xl p-6"
      >
        <SiteCareMarkedLine
          v-for="reassurance in props.page.offer.reassurances"
          :key="reassurance"
          :text="reassurance"
        />
      </ul>
    </SiteCarePageSection>

    <SiteCarePageSection
      v-if="hasOtherPoints"
      eyebrow="Le reste de votre site"
      :heading="otherPointsHeading"
      has-tinted-background
    >
      <div
        v-if="props.page.goods.length > 0"
        class="border-site-care-line flex flex-col gap-3 rounded-xl border bg-white p-6"
      >
        <h3 class="text-lg leading-[1.35] font-medium">Ce qui va bien</h3>
        <ul class="flex flex-col gap-3">
          <SiteCareMarkedLine v-for="(good, goodIndex) in props.page.goods" :key="goodIndex" :text="good" />
        </ul>
      </div>
      <div
        v-if="props.page.other_fixes.length > 0"
        class="border-site-care-line flex flex-col gap-3 rounded-xl border bg-white p-6"
      >
        <h3 class="text-lg leading-[1.35] font-medium">À corriger aussi</h3>
        <ul class="flex flex-col gap-3">
          <SiteCareMarkedLine
            v-for="(otherFix, otherFixIndex) in props.page.other_fixes"
            :key="otherFixIndex"
            :text="otherFix"
            mark="info"
          />
        </ul>
      </div>
      <div
        v-if="props.page.watches.length > 0"
        class="border-site-care-line flex flex-col gap-3 rounded-xl border bg-white p-6"
      >
        <h3 class="text-lg leading-[1.35] font-medium">À regarder un jour, sans urgence</h3>
        <ul class="flex flex-col gap-3">
          <SiteCareMarkedLine
            v-for="(watch, watchIndex) in props.page.watches"
            :key="watchIndex"
            :text="watch"
            mark="info"
          />
        </ul>
      </div>
    </SiteCarePageSection>

    <SiteCarePageSection eyebrow="Qui vous écrit">
      <div class="flex items-center gap-5">
        <div v-if="props.page.presenter.photo_url" class="relative h-32.5 w-26 flex-none">
          <span class="bg-site-care-lavender absolute -top-2.5 -left-2.5 size-16 rounded-[14px]" aria-hidden="true" />
          <img
            class="shadow-site-care-portrait relative block h-32.5 w-26 rounded-xl object-cover"
            :src="props.page.presenter.photo_url"
            :alt="`Portrait de ${props.page.presenter.name}`"
            width="104"
            height="130"
          />
        </div>
        <div
          v-else
          class="bg-site-care-lavender text-site-care-violet flex h-32.5 w-26 flex-none items-center justify-center rounded-xl text-[32px] leading-none font-medium"
          aria-hidden="true"
        >
          {{ presenterInitials }}
        </div>
        <div>
          <h2 class="text-2xl leading-[1.15] font-medium tracking-[-0.01em] text-balance">
            {{ props.page.presenter.name }}
          </h2>
          <p class="text-site-care-ink-muted mt-1.5 text-[15px] leading-6">
            {{ props.page.presenter.tagline }}
          </p>
        </div>
      </div>
      <p v-if="props.page.presenter.site_url" class="text-site-care-ink-muted text-[15px] leading-6">
        Mon site&nbsp;:
        <a
          class="text-site-care-violet hover:text-site-care-violet-strong focus-visible:text-site-care-violet-strong font-medium underline underline-offset-2"
          :href="props.page.presenter.site_url"
          target="_blank"
          rel="noopener"
          >{{ props.page.presenter.site_label || props.page.presenter.site_url }}</a
        >
      </p>
    </SiteCarePageSection>

    <section class="px-6 pb-12 sm:pb-16">
      <div
        class="bg-site-care-lavender mx-auto flex w-full max-w-140 flex-col items-center gap-5 rounded-2xl px-6 py-10 text-center"
      >
        <h2 class="text-[28px] leading-[1.15] font-medium tracking-[-0.01em] text-balance">
          Vous voulez que je m’en occupe&nbsp;?
        </h2>
        <p class="text-site-care-ink-muted text-[15px] leading-6">
          Répondez à mon message, c’est tout. Et si cela ne vous intéresse pas, dites-le-moi&nbsp;: je ne vous écrirai
          plus.
        </p>
        <div class="flex w-full flex-col gap-3">
          <a
            v-if="props.page.reply_mailto"
            class="bg-site-care-violet hover:bg-site-care-violet-strong focus-visible:bg-site-care-violet-strong focus-visible:outline-site-care-ink flex min-h-13 w-full items-center justify-center rounded-lg border border-transparent px-6 py-3.5 text-base font-medium text-white transition-colors focus-visible:outline-2 focus-visible:outline-offset-2"
            :href="props.page.reply_mailto"
            @click="emit('reply-click')"
          >
            Me répondre
          </a>
          <a
            v-if="props.page.forward_mailto"
            class="border-site-care-line-strong text-site-care-ink hover:bg-site-care-band focus-visible:bg-site-care-band focus-visible:outline-site-care-ink flex min-h-13 w-full items-center justify-center rounded-lg border bg-transparent px-6 py-3.5 text-base font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2"
            :href="props.page.forward_mailto"
            @click="emit('forward-click')"
          >
            Ce n’est pas moi qui gère le site
          </a>
        </div>
        <p class="text-site-care-ink-muted text-[13px] leading-5">Cette page n’est visible que par vous.</p>
      </div>
    </section>
  </main>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type {
  SiteCareIntroAroundDomain,
  SiteCareProspectPageEmits,
  SiteCareProspectPageProps,
} from '../types/SiteCareProspectPage'
import type { SiteCarePublicPage } from '../types/SiteCarePublicPage'
import { computed } from 'vue'
import SiteCareMarkedLine from './SiteCareMarkedLine.vue'
import SiteCarePageSection from './SiteCarePageSection.vue'

const props: SiteCareProspectPageProps = defineProps({
  page: {
    type: Object as PropType<SiteCarePublicPage>,
    required: true,
  },
})

const emit: EmitFn<SiteCareProspectPageEmits> = defineEmits<SiteCareProspectPageEmits>()

const introAroundDomain: ComputedRef<SiteCareIntroAroundDomain> = computed((): SiteCareIntroAroundDomain => {
  const intro: string = props.page.intro
  const domain: string = props.page.domain
  const domainStart: number = domain ? intro.indexOf(domain) : -1

  if (domainStart === -1) {
    return { beforeDomain: intro, domain: null, afterDomain: '' }
  }

  return {
    beforeDomain: intro.slice(0, domainStart),
    domain,
    afterDomain: intro.slice(domainStart + domain.length),
  }
})

const hasOtherPoints: ComputedRef<boolean> = computed(
  (): boolean => props.page.goods.length > 0 || props.page.other_fixes.length > 0 || props.page.watches.length > 0,
)

const otherPointsHeading: ComputedRef<string> = computed((): string => {
  const otherPointsCount: number = props.page.other_points_count
  return otherPointsCount === 1 ? 'J’ai regardé 1 autre point' : `J’ai regardé ${otherPointsCount} autres points`
})

const presenterInitials: ComputedRef<string> = computed((): string => {
  const nameWords: string[] = props.page.presenter.name
    .trim()
    .split(/\s+/)
    .filter((word: string): boolean => word !== '')
  const firstWord: string = nameWords[0] ?? ''
  const lastWord: string = nameWords.length > 1 ? (nameWords.at(-1) ?? '') : ''
  return `${firstWord.charAt(0)}${lastWord.charAt(0)}`.toLocaleUpperCase('fr-FR')
})
</script>
