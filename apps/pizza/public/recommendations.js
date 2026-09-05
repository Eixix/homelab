// Explicit recipe connections only: similar names do not establish equivalence.
export function buildRecommendations(items, mapping) {
  const base = items.find(item => item.name === mapping.baseName);
  if (!base || base.description !== mapping.baseDescription) return [];
  return mapping.connections.flatMap(connection => {
    const original = items.find(item => item.name === connection.name);
    if (!original || original.description !== connection.description) return [];
    const extras = connection.extraIds.map(id => base.extras?.find(extra => extra.id === id));
    if (extras.some(extra => !extra) || new Set(connection.extraIds).size !== extras.length) return [];
    return [{ itemId: original.id, baseItemId: base.id, extraIds: connection.extraIds }];
  });
}

export function cheaperAlternative(line, items, connections) {
  const connection = connections.find(connection => connection.itemId === line.itemId);
  if (!connection) return null;
  const original = items.find(item => item.id === line.itemId);
  const base = items.find(item => item.id === connection.baseItemId);
  const selected = line.extraIds || [];
  // An extra already in the recipe means an additional helping. The options
  // cannot represent double toppings, so do not silently drop that helping.
  if (!original || !base || selected.some(id => connection.extraIds.includes(id))) return null;
  const extraIds = [...connection.extraIds, ...selected];
  const extras = extraIds.map(id => base.extras?.find(extra => extra.id === id));
  const originalExtras = selected.map(id => original.extras?.find(extra => extra.id === id));
  if ([...extras, ...originalExtras].some(extra => !extra)) return null;
  const originalPriceCents = original.priceCents + originalExtras.reduce((sum, extra) => sum + extra.priceCents, 0);
  const priceCents = base.priceCents + extras.reduce((sum, extra) => sum + extra.priceCents, 0);
  if (priceCents >= originalPriceCents) return null;
  return {
    originalName: original.name, name: `${base.name} + ${extras.map(extra => extra.name).join(', ')}`,
    originalPriceCents, priceCents, savingCents: originalPriceCents - priceCents,
    line: { itemId: base.id, quantity: line.quantity, extraIds },
  };
}

// Called before submission. A declined suggestion leaves that order line intact.
export function recommendOrder(lines, items, connections, decide) {
  const counts = new Map();
  const groups = new Map();
  const replacements = new Map();
  for (const line of lines) {
    counts.set(line.itemId, (counts.get(line.itemId) || 0) + line.quantity);
    const key = JSON.stringify([line.itemId, [...(line.extraIds || [])].sort()]);
    const group = groups.get(key) || [];
    group.push(line);
    groups.set(key, group);
  }
  for (const group of groups.values()) {
    const alternative = cheaperAlternative(group[0], items, connections);
    const quantity = group.reduce((sum, line) => sum + line.quantity, 0);
    if (!alternative || (counts.get(alternative.line.itemId) || 0) + quantity > 20) continue;
    if (!decide(alternative)) continue;
    counts.set(group[0].itemId, counts.get(group[0].itemId) - quantity);
    counts.set(alternative.line.itemId, (counts.get(alternative.line.itemId) || 0) + quantity);
    for (const line of group) replacements.set(line, { ...alternative.line, quantity: line.quantity });
  }
  return lines.map(line => replacements.get(line) || line);
}
