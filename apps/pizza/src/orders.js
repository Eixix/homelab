// Resolve all names and prices from the server catalog, never from the client.
export function priceOrder(selected, catalog) {
  if (!Array.isArray(selected) || !selected.length) throw new Error('Bitte mindestens einen Artikel wählen.');
  const counts = new Map();
  return selected.map(line => {
    const item = catalog.items.find(item => item.id === line?.itemId);
    const quantity = line?.quantity;
    if (!item || !Number.isInteger(quantity) || quantity < 1 || quantity > 20) throw new Error('Ungültiger Artikel oder Anzahl.');
    counts.set(item.id, (counts.get(item.id) || 0) + quantity);
    if (counts.get(item.id) > 20) throw new Error('Maximal 20 Portionen pro Artikel.');
    const ids = line.extraIds ?? [];
    if (!Array.isArray(ids) || new Set(ids).size !== ids.length) throw new Error('Ungültige Extras.');
    const extras = ids.map(id => {
      const extra = item.extras?.find(extra => extra.id === id);
      if (!extra) throw new Error('Dieses Extra ist für den Artikel nicht verfügbar.');
      return { id: extra.id, name: extra.name, priceCents: extra.priceCents };
    }).sort((a, b) => a.id.localeCompare(b.id));
    return {
      itemId: item.id,
      name: item.name + (extras.length ? ` + ${extras.map(extra => extra.name).join(', ')}` : ''),
      priceCents: item.priceCents + extras.reduce((sum, extra) => sum + extra.priceCents, 0),
      quantity,
      ...(extras.length ? { extras, extraIds: extras.map(extra => extra.id), basePriceCents: item.priceCents } : {}),
    };
  });
}

export function summarizeItems(orders) {
  const groups = new Map();
  for (const line of orders.flatMap(order => order.items)) {
    const key = JSON.stringify([line.itemId, [...(line.extraIds || [])].sort(), line.name, line.priceCents]);
    const group = groups.get(key) || { name: line.name, quantity: 0, totalCents: 0 };
    group.quantity += line.quantity;
    group.totalCents += line.quantity * line.priceCents;
    groups.set(key, group);
  }
  return [...groups.values()];
}
