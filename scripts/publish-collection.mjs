#!/usr/bin/env node
import { execFileSync, spawnSync } from "node:child_process";
import { appendFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { isDeepStrictEqual } from "node:util";
import { renderReport } from "./collect-public-status.mjs";
import { checkRepositoryProjections } from "./projection-consistency.mjs";
import { validateSnapshot } from "./validate-public-data.mjs";

const MAX_ATTEMPTS = 3;
const options = { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], maxBuffer: 32 * 1024 * 1024 };

function git(root, ...args) {
  return execFileSync("git", ["-C", root, ...args], options).trim();
}

function fetchTip(root, ref) {
  git(root, "fetch", "--no-tags", "origin", ref);
  return git(root, "rev-parse", "FETCH_HEAD");
}

function ancestor(root, older, newer) {
  return spawnSync("git", ["-C", root, "merge-base", "--is-ancestor", older, newer], options).status === 0;
}

function rows(text) {
  return text.split(/\r?\n/).filter(line => line.trim()).map(line => JSON.parse(line));
}

function identicalRun(a, b) {
  const id = a.run?.github_run_id;
  const attempt = a.run?.github_run_attempt;
  return id != null && attempt != null && id === b.run?.github_run_id && attempt === b.run?.github_run_attempt;
}

function replay(root, snapshot, day) {
  const current = checkRepositoryProjections(root);
  const path = join("data", day, "public-status.jsonl");
  const latest = join("data", "latest", "public-status.json");
  const report = join("reports", day + ".md");
  const journal = join(root, path);
  const text = existsSync(journal) ? readFileSync(journal, "utf8") : "";
  const existing = rows(text);
  if (existing.some(item => isDeepStrictEqual(item, snapshot))) return null;
  if (existing.some(item => identicalRun(item, snapshot))) throw new Error("conflicting collection run identity");
  if (Date.parse(snapshot.collected_at) <= Date.parse(current.collected_at)) {
    throw new Error("stale collection; preserve snapshot for recovery");
  }
  mkdirSync(join(root, "data", day), { recursive: true });
  appendFileSync(journal, (text && !text.endsWith("\n") ? "\n" : "") + JSON.stringify(snapshot) + "\n", "utf8");
  writeFileSync(join(root, latest), JSON.stringify(snapshot, null, 2) + "\n");
  writeFileSync(join(root, report), renderReport(snapshot));
  checkRepositoryProjections(root);
  // Recheck the rebased data with the target revision's own validation commands.
  const env = { ...process.env };
  delete env.GH_TOKEN;
  delete env.GITHUB_TOKEN;
  for (const command of ["validate", "projection-check"]) {
    execFileSync("npm", ["run", command], { ...options, cwd: root, env });
  }
  return [path, latest, report];
}

export async function publishSnapshot(repoRoot, branch, snapshot) {
  const root = resolve(repoRoot);
  const ref = "refs/heads/" + branch;
  git(root, "check-ref-format", ref);
  validateSnapshot(snapshot, "publication input");
  const date = new Date(snapshot.collected_at);
  if (date.toISOString() !== snapshot.collected_at) throw new Error("expected canonical UTC collection timestamp");
  const day = snapshot.collected_at.slice(0, 10);
  let base = fetchTip(root, ref);
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    const dir = mkdtempSync(join(tmpdir(), "observatory-publish-"));
    const checkout = join(dir, "checkout");
    let attached = false;
    try {
      git(root, "worktree", "add", "--detach", checkout, base);
      attached = true;
      const paths = replay(checkout, snapshot, day);
      if (paths === null) return { status: "ALREADY_PRESENT", attempt, head: base };
      git(checkout, "add", "--", ...paths);
      git(checkout, "commit", "-m", "Collect public observatory data");
      const commit = git(checkout, "rev-parse", "HEAD");
      const push = spawnSync("git", ["-C", checkout, "push", "origin", "HEAD:" + ref], options);
      const tip = fetchTip(root, ref);
      if (ancestor(root, commit, tip)) {
        const canonical = git(root, "show", tip + ":" + paths[0]);
        if (!rows(canonical).some(item => isDeepStrictEqual(item, snapshot))) {
          throw new Error("published commit missing exact snapshot");
        }
        return { status: "PUBLISHED", attempt, head: tip };
      }
      if (push.status === 0 || tip === base || !ancestor(root, base, tip)) {
        throw new Error("publication failed without a safe fast-forward retry");
      }
      base = tip;
    } finally {
      if (attached) git(root, "worktree", "remove", "--force", checkout);
      rmSync(dir, { recursive: true, force: true });
    }
  }
  throw new Error("publication retry limit reached; preserve snapshot for recovery");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [branch, input] = process.argv.slice(2);
  if (!branch || !input) throw new Error("usage: publish-collection.mjs BRANCH SNAPSHOT");
  const snapshot = JSON.parse(readFileSync(input, "utf8"));
  console.log(JSON.stringify(await publishSnapshot(".", branch, snapshot)));
}
