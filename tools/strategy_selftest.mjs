import fs from "node:fs";
import path from "node:path";

function die(msg) {
  console.error(msg);
  process.exit(1);
}

function parseStrategies(text) {
  const trimmed = (text || "").trim();
  if (!trimmed) return [];

  // Full JSON (array or {strategies:[]}) is supported.
  try {
    const parsed = JSON.parse(trimmed);
    if (Array.isArray(parsed)) return parsed.filter((x) => x && typeof x === "object");
    if (Array.isArray(parsed?.strategies)) return parsed.strategies.filter((x) => x && typeof x === "object");
  } catch {
    // fall through to line-based parsing
  }

  const lines = trimmed.split(/\r?\n/);
  const strategies = [];
  for (const line of lines) {
    const cleaned = line.trim();
    if (!cleaned || cleaned.startsWith("#")) continue;
    try {
      strategies.push(JSON.parse(cleaned));
    } catch {
      // ignore invalid lines
    }
  }
  return strategies.filter((x) => x && typeof x === "object");
}

async function main() {
  const root = process.cwd();
  const configPath = path.join(root, "config.json");
  if (!fs.existsSync(configPath)) die(`Missing config.json at: ${configPath}`);

  const cfg = JSON.parse(fs.readFileSync(configPath, "utf-8"));
  const url = cfg?.strategyUrl;
  if (typeof url !== "string" || !url.trim()) die("config.json missing strategyUrl");

  const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
  if (!res.ok) die(`Fetch failed: HTTP ${res.status}`);

  const text = await res.text();
  const strategies = parseStrategies(text);
  if (strategies.length === 0) die("Parsed 0 strategies from remote file");

  // A basic sanity check: the first strategy should be JSON object.
  if (typeof strategies[0] !== "object") die("First strategy is not an object");

  console.log(`OK: fetched ${strategies.length} strategies`);
}

main().catch((e) => die(`Selftest error: ${String(e)}`));

