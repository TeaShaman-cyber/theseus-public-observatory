import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const scanner = fileURLToPath(new URL("./check-no-secrets.mjs", import.meta.url));
function scan(relative, content) {
  const cwd = mkdtempSync(join(tmpdir(), "observatory-secret-test-"));
  try {
    mkdirSync(join(cwd, ".github", "workflows"), { recursive: true });
    writeFileSync(join(cwd, relative), content);
    return spawnSync(process.execPath, [scanner], { cwd, encoding: "utf8" }).status;
  } finally {
    rmSync(cwd, { recursive: true, force: true });
  }
}

const reference = "$" + "{{ secrets.CLOUDFLARE_RADAR_TOKEN }}";
const variable = "CLOUDFLARE_RADAR_" + "TOKEN";
const assignment = (value) => "          " + variable + ": " + value + "\n";

test("workflow permits an exact Actions secret reference", () => {
  assert.equal(scan(".github/workflows/radar.yml", assignment(reference)), 0);
});
test("literal secret-like assignment remains rejected", () => {
  assert.equal(scan(".github/workflows/radar.yml", assignment("fake-literal-value")), 1);
});
test("reference exemption is restricted to workflow YAML and exact full line", () => {
  assert.equal(scan("plain.txt", assignment(reference)), 1);
  assert.equal(scan(".github/workflows/radar.yml", assignment(reference + " fake")), 1);
});
