const WORDS_LEFT_OUT_OF_INITIALS: string[] = ['de', 'des', 'du', 'la', 'le', 'les', 'et', 'l', 'd']

const WORD_SEPARATORS_PATTERN: RegExp = /[\s’'-]+/

/** How the module names a business on its cards and pages: its initials, and where it works. */
export class SiteCareBusinessLabels {
  /**
   * The two letters of a business on its tile, its small words left out: « Jardins du Lac » gives « JL ».
   * @param businessName - The name of the business.
   * @returns One or two capital letters.
   */
  static initialsOf(businessName: string): string {
    return businessName
      .split(WORD_SEPARATORS_PATTERN)
      .filter((word: string): boolean => word !== '' && !WORDS_LEFT_OUT_OF_INITIALS.includes(word.toLowerCase()))
      .slice(0, 2)
      .map((word: string): string => word.charAt(0).toUpperCase())
      .join('')
  }

  /**
   * Where a business works: its trade, and its city when known.
   * @param tradeLabel - The trade, empty when unknown.
   * @param city - The city, null when unknown.
   * @returns « Paysagiste · Bruz », or the one of the two that is known.
   */
  static placeOf(tradeLabel: string, city: string | null): string {
    if (city === null || city === '') {
      return tradeLabel
    }
    return tradeLabel === '' ? city : `${tradeLabel} · ${city}`
  }
}
