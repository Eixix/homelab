import { readFile, writeFile } from 'node:fs/promises';

const input = process.argv[2];
const output = process.argv[3];
if (!input || !output) throw new Error('Usage: node scripts/convert-menu.js INPUT.txt OUTPUT.json');

const categoryNames = new Map([
  ['AntipastiAntipasti', 'Antipasti'],
  ['SalateSalate', 'Salate'],
  ['PizzaPizza', 'Pizza'],
  ['Vegane PizzaVegane Pizza', 'Vegane Pizza'],
  ['Party-PizzaParty-Pizza', 'Party-Pizza'],
  ['PaninoPanino', 'Panino'],
  ['PastaPasta', 'Pasta'],
  ['DessertsDesserts', 'Desserts'],
]);
const pricePattern = /^(\d+),(\d{2}) €$/;
const deduplicate = value => {
  const text = value.trim();
  const middle = text.length / 2;
  return Number.isInteger(middle) && text.slice(0, middle) === text.slice(middle) ? text.slice(0, middle) : text;
};
const lines = (await readFile(input, 'utf8')).split(/\r?\n/);
const items = [];
let category = '';

for (let index = 0; index < lines.length; index += 1) {
  const text = lines[index].trim();
  if (categoryNames.has(text)) { category = categoryNames.get(text); continue; }
  if (!category || !lines[index].startsWith(' ') || !text || pricePattern.test(text)) continue;
  const priceMatch = lines[index + 1]?.trim().match(pricePattern);
  if (!priceMatch) continue;

  const name = deduplicate(text);
  const priceCents = Number(priceMatch[1]) * 100 + Number(priceMatch[2]);
  let cursor = index + 2;
  let previousPrice = '';
  if (pricePattern.test(lines[cursor]?.trim())) { previousPrice = lines[cursor].trim(); cursor += 1; }
  if (/^\d+% Rabatt$/.test(lines[cursor]?.trim())) cursor += 1;
  let description = '';
  const candidate = lines[cursor]?.trim();
  const candidateStartsNextItem = Boolean(candidate && pricePattern.test(lines[cursor + 1]?.trim()));
  if (lines[cursor]?.startsWith(' ') && candidate && !candidateStartsNextItem) {
    description = deduplicate(candidate); cursor += 1;
  }
  description = [description, previousPrice ? `Aktionspreis (statt ${previousPrice})` : ''].filter(Boolean).join(' · ');
  items.push({ id: `item-${items.length + 1}`, category, name, description, priceCents });
  index = cursor - 1;
}

const catalog = { restaurant: 'Va Bene', website: '', items };
await writeFile(output, `${JSON.stringify(catalog, null, 2)}\n`);
console.log(`Converted ${items.length} items to ${output}`);
