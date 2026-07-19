import http from "node:http";
import sharp from "sharp";

const port = Number(process.env.PORT || 3000);
const lokiUrl = process.env.LOKI_URL || "http://loki:3100";
const cacheSeconds = Number(process.env.CACHE_SECONDS || 300);
const query = String.raw`sum(rate({job="traefik-access", host!~".*\\.(home|localhost)$", host!=""}[5m])) * 60`;

let cached = null;
let cachedAt = 0;

const xml = (value) => String(value).replace(/[<>&"']/g, (character) => ({
  "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&apos;",
})[character]);

function formatNumber(value) {
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  if (value >= 100) return value.toFixed(0);
  if (value >= 10) return value.toFixed(1);
  return value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
}

async function loadSeries() {
  const end = Math.floor(Date.now() / 1000);
  const params = new URLSearchParams({
    query,
    start: String(end - 86400),
    end: String(end),
    step: "300",
  });
  const response = await fetch(`${lokiUrl}/loki/api/v1/query_range?${params}`, {
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new Error(`Loki returned ${response.status}`);
  const payload = await response.json();
  const values = payload?.data?.result?.[0]?.values ?? [];
  return values.map(([timestamp, value]) => [Number(timestamp), Number(value)])
    .filter(([, value]) => Number.isFinite(value));
}

function render(series) {
  const width = 800;
  const height = 480;
  const plot = { left: 74, top: 92, right: 770, bottom: 400 };
  const values = series.map(([, value]) => value);
  const observedMax = Math.max(1, ...values);
  const chartMax = observedMax * 1.12;
  const start = series[0]?.[0] ?? Math.floor(Date.now() / 1000) - 86400;
  const end = series.at(-1)?.[0] ?? Math.floor(Date.now() / 1000);
  const x = (time) => plot.left + ((time - start) / Math.max(1, end - start)) * (plot.right - plot.left);
  const y = (value) => plot.bottom - (value / chartMax) * (plot.bottom - plot.top);
  const points = series.map(([time, value]) => `${x(time).toFixed(1)},${y(value).toFixed(1)}`).join(" ");
  const area = points ? `${plot.left},${plot.bottom} ${points} ${plot.right},${plot.bottom}` : "";
  const current = values.at(-1) ?? 0;
  const generated = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit", minute: "2-digit", timeZone: "Europe/Berlin",
  }).format(new Date());
  const grid = [0, 0.25, 0.5, 0.75, 1].map((fraction) => {
    const gridY = plot.bottom - fraction * (plot.bottom - plot.top);
    return `<line x1="${plot.left}" y1="${gridY}" x2="${plot.right}" y2="${gridY}" class="grid"/>` +
      `<text x="${plot.left - 12}" y="${gridY + 5}" text-anchor="end" class="axis">${xml(formatNumber(chartMax * fraction))}</text>`;
  }).join("");
  const timeLabels = [0, 6, 12, 18, 24].map((hours) => {
    const labelX = plot.left + (hours / 24) * (plot.right - plot.left);
    const label = hours === 24 ? "now" : `−${24 - hours}h`;
    return `<text x="${labelX}" y="${plot.bottom + 32}" text-anchor="middle" class="axis">${label}</text>`;
  }).join("");

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="External request volume over the last 24 hours">
  <rect width="800" height="480" fill="#fffdf5"/>
  <style>
    text { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: #111111; }
    .title { font-size: 27px; font-weight: 800; }
    .metric { font-size: 16px; font-weight: 700; }
    .axis { font-size: 13px; }
    .grid { stroke: #111111; stroke-width: 1; opacity: .16; }
  </style>
  <text x="38" y="43" class="title">EXTERNAL TRAFFIC · 24 HOURS</text>
  <text x="762" y="35" text-anchor="end" class="metric">NOW ${xml(formatNumber(current))} req/min</text>
  <text x="762" y="58" text-anchor="end" class="metric">PEAK ${xml(formatNumber(observedMax))} req/min</text>
  ${grid}
  ${timeLabels}
  ${area ? `<polygon points="${area}" fill="#f2cf00" opacity=".45"/>` : ""}
  ${points ? `<polyline points="${points}" fill="none" stroke="#1565c0" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>` : `<text x="400" y="245" text-anchor="middle" class="title">NO EXTERNAL REQUESTS</text>`}
  <line x1="${plot.left}" y1="${plot.bottom}" x2="${plot.right}" y2="${plot.bottom}" stroke="#111" stroke-width="2"/>
  <text x="38" y="462" class="axis">5-minute rolling rate · updated ${xml(generated)} Europe/Berlin</text>
</svg>`;
}

async function chart() {
  const now = Date.now();
  if (cached && now - cachedAt < cacheSeconds * 1000) return cached;
  const svg = render(await loadSeries());
  cached = await sharp(Buffer.from(svg))
    .png({ palette: true, colours: 5, compressionLevel: 9 })
    .toBuffer();
  cachedAt = now;
  return cached;
}

http.createServer(async (request, response) => {
  if (request.url === "/healthz") {
    response.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("ok\n");
    return;
  }
  if (!["GET", "HEAD"].includes(request.method) || !["/", "/external-traffic.png"].includes(request.url)) {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("not found\n");
    return;
  }
  try {
    const body = await chart();
    response.writeHead(200, {
      "Content-Type": "image/png",
      "Cache-Control": `public, max-age=${cacheSeconds}, stale-if-error=3600`,
      "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
      "Access-Control-Allow-Origin": "*",
    });
    response.end(request.method === "HEAD" ? undefined : body);
  } catch (error) {
    console.error(error);
    response.writeHead(503, { "Content-Type": "text/plain; charset=utf-8", "Retry-After": "30" });
    response.end("chart temporarily unavailable\n");
  }
}).listen(port, "0.0.0.0", () => console.log(`traffic image listening on ${port}`));
