export function effectiveCatalog(catalog, settings = {}) {
  return { ...catalog, items: catalog.items.map(item => item.name === 'Pizza Margherita' && settings.dealEnabled === false
    ? { ...item, priceCents: (settings.regularPriceCents ?? 1040) } : item) };
}

export function validateDeal(input) {
  if (typeof input.dealEnabled !== 'boolean' || !Number.isSafeInteger(input.regularPriceCents) || input.regularPriceCents < 1 || input.regularPriceCents > 100000) {
    throw new Error('Bitte einen gültigen regulären Preis angeben.');
  }
  return { dealEnabled: input.dealEnabled, regularPriceCents: input.regularPriceCents };
}
