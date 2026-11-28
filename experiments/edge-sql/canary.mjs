import assert from "node:assert/strict";
import { copyFile, mkdir, readFile, stat } from "node:fs/promises";
import { performance } from "node:perf_hooks";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";
import { Miniflare } from "miniflare";

const dir = resolve(process.argv[2]);
const fixture = JSON.parse(await readFile(resolve(dir, "reference.json")));
const bundle = resolve(dir, "bundle");
await mkdir(bundle, { recursive: true });
const wasm = fileURLToPath(import.meta.resolve("@ducklings/workers/wasm"));
await copyFile(wasm, resolve(bundle, "duckdb-workers.wasm"));
await build({
  entryPoints: [fileURLToPath(new URL("./worker.mjs", import.meta.url))],
  bundle: true, format: "esm", platform: "browser",
  external: ["*.wasm", "node:*"],
  outfile: resolve(bundle, "worker.mjs"), logLevel: "warning",
});
const total = (await stat(resolve(bundle,"worker.mjs"))).size + (await stat(wasm)).size;
assert.ok(total < 64 * 1024 * 1024, "bundle exceeds documented Workers size ceiling");
const body = JSON.stringify({
  sources: [...await readFile(resolve(dir, "sources.parquet"))],
  samples: [...await readFile(resolve(dir, "samples.parquet"))],
});
const started = performance.now();
const mf = new Miniflare({
  modules: true,
  modulesRoot: bundle,
  scriptPath: resolve(bundle, "worker.mjs"),
  modulesRules: [{ type: "CompiledWasm", include: ["**/*.wasm"] }],
  compatibilityDate: "2026-07-30",
  compatibilityFlags: ["nodejs_compat"],
});
try {
  const times = [];
  let engine;
  for (let i = 0; i < 3; i++) {
    const t = performance.now();
    const response = await mf.dispatchFetch("http://localhost/fixture", {
      method: "POST", body, headers: { "content-type": "application/json" },
    });
    assert.equal(response.status, 200, await response.clone().text());
    const value = await response.json();
    engine = value.version;
    assert.deepEqual(value.results, fixture.expected);
    times.push(Math.round((performance.now() - t) * 100) / 100);
  }
  console.log(JSON.stringify({
    status: "PARITY_OK", runtime: "miniflare/workerd local on hosted runner",
    revision: fixture.revision, engine, bundle_bytes: total,
    request_wall_ms: times, total_wall_ms: Math.round(performance.now()-started),
    cloud_cpu_limit_verified: false,
  }));
} finally {
  await mf.dispose();
}
