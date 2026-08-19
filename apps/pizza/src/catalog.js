import { readFile } from 'node:fs/promises';

const money = value => {
  const normalized = String(value).trim().replace(',', '.').replace(/\s*€$/, '');
  if (!/^\d+(?:\.\d{1,2})?$/.test(normalized)) throw new Error(`Invalid price: ${value}`);
  return Math.round(Number(normalized) * 100);
};

export function parseCatalog(text) {
  const trimmed = text.trim();
  if (!trimmed) return { restaurant: '', website: '', items: [] };
  if (trimmed.startsWith('{')) {
    const value = JSON.parse(trimmed);
    return {
      restaurant: String(value.restaurant || ''),
      website: String(value.website || ''),
      items: value.items.map((item, index) => ({
        id: String(item.id || `item-${index + 1}`),
        category: String(item.category || 'Pizza'),
        name: String(item.name),
        description: String(item.description || ''),
        priceCents: Number.isInteger(item.priceCents) ? item.priceCents : money(item.price),
      })),
    };
  }

  const result = { restaurant: '', website: '', items: [] };
  for (const rawLine of trimmed.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    if (line.startsWith('@restaurant=')) result.restaurant = line.slice(12).trim();
    else if (line.startsWith('@website=')) result.website = line.slice(9).trim();
    else {
      const [category, name, price, description = ''] = line.split('|').map(value => value.trim());
      if (!category || !name || !price) throw new Error(`Invalid catalog line: ${rawLine}`);
      result.items.push({ id: `item-${result.items.length + 1}`, category, name, description, priceCents: money(price) });
    }
  }
  return result;
}

export async function loadCatalog(path) {
  return parseCatalog(await readFile(path, 'utf8'));
}
