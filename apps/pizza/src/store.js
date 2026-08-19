import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';

export class Store {
  constructor(path) {
    this.path = path;
    this.data = { days: {} };
    this.pending = Promise.resolve();
  }

  async load() {
    await mkdir(dirname(this.path), { recursive: true });
    try { this.data = JSON.parse(await readFile(this.path, 'utf8')); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }

  day(date) {
    return this.data.days[date] ||= { unlocked: false, closed: false, summarySent: false, orders: {} };
  }

  save() {
    this.pending = this.pending.then(async () => {
      const temporary = `${this.path}.tmp`;
      await writeFile(temporary, `${JSON.stringify(this.data, null, 2)}\n`, { mode: 0o600 });
      await rename(temporary, this.path);
    });
    return this.pending;
  }
}
