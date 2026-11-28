import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { cpSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { renderReport } from "./collect-public-status.mjs";
import { publishSnapshot } from "./publish-collection.mjs";

function git(root, ...args) {
  return execFileSync("git", ["-C", root, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
}

const snapshot = (hour, attempt = 1) => ({
  schema_version: 1,
  collected_at: `2026-09-09T${hour}:00:00.000Z`,
  run: { collector: "collect-public-status-v1", github_run_id: hour, github_run_attempt: attempt },
  sources: [],
});

function writeInitial(root, item) {
  mkdirSync(join(root, "data/2026-09-09"), { recursive: true });
  mkdirSync(join(root, "data/latest"), { recursive: true });
  mkdirSync(join(root, "reports"), { recursive: true });
  writeFileSync(join(root, "data/2026-09-09/public-status.jsonl"), JSON.stringify(item) + "\n");
  writeFileSync(join(root, "data/latest/public-status.json"), JSON.stringify(item, null, 2) + "\n");
  writeFileSync(join(root, "reports/2026-09-09.md"), renderReport(item));
}

function fixture(t) {
  const dir = mkdtempSync(join(tmpdir(), "obs-publish-test-"));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const remote = join(dir, "remote.git");
  const root = join(dir, "repo");
  git(dir, "init", "--bare", "--initial-branch=main", remote);
  git(dir, "clone", remote, root);
  git(root, "config", "user.name", "Fixture");
  git(root, "config", "user.email", "fixture@example.invalid");
  writeInitial(root, snapshot("06"));
  cpSync(fileURLToPath(new URL(".", import.meta.url)), join(root, "scripts"), { recursive: true });
  cpSync(fileURLToPath(new URL("../package.json", import.meta.url)), join(root, "package.json"));
  git(root, "add", ".");
  git(root, "commit", "-m", "base");
  git(root, "push", "origin", "main");
  return { root, remote };
}

function remoteRows(remote) {
  return git(remote, "show", "main:data/2026-09-09/public-status.jsonl").split("\n").map(JSON.parse);
}

test("publication appends once and exact replay does not create another commit", async (t) => {
  const { root, remote } = fixture(t);
  const item = snapshot("07");
  await publishSnapshot(root, "main", item);
  const head = git(remote, "rev-parse", "main");
  await publishSnapshot(root, "main", item);
  assert.equal(git(remote, "rev-parse", "main"), head);
  assert.deepEqual(remoteRows(remote), [snapshot("06"), item]);
  assert.deepEqual(JSON.parse(git(remote, "show", "main:data/latest/public-status.json")), item);
  assert.equal(git(root, "status", "--porcelain"), "");
});

test("stale or conflicting snapshots leave the remote history untouched", async (t) => {
  const { root, remote } = fixture(t);
  await publishSnapshot(root, "main", snapshot("08"));
  const head = git(remote, "rev-parse", "main");
  await assert.rejects(publishSnapshot(root, "main", snapshot("07")), /stale/);
  await assert.rejects(publishSnapshot(root, "main", snapshot("08", 2)), /stale|conflict/);
  assert.equal(git(remote, "rev-parse", "main"), head);
});

function installRace(root, remote, rival) {
  // Transfer the competing commit's objects before the race, then advance main
  // inside the bare server's receive hook, between advertisement and ref update.
  git(rival, "push", "origin", "HEAD:refs/heads/rival");
  const rivalHead = git(rival, "rev-parse", "HEAD");
  const marker = join(root, "..", "raced");
  const hooks = join(remote, "hooks");
  git(remote, "config", "core.hooksPath", hooks);
  const hook = join(hooks, "pre-receive");
  writeFileSync(hook, `#!/bin/sh\nif [ ! -e '${marker}' ]; then\n  touch '${marker}'\n  env -u GIT_QUARANTINE_PATH -u GIT_OBJECT_DIRECTORY -u GIT_ALTERNATE_OBJECT_DIRECTORIES git update-ref refs/heads/main '${rivalHead}' || exit 1\nfi\n`, { mode: 0o755 });
  return marker;
}

test("a concurrent unrelated commit is preserved by bounded replay", async (t) => {
  const { root, remote } = fixture(t);
  const rival = join(root, "..", "rival");
  git(root, "clone", remote, rival);
  git(rival, "config", "user.name", "Fixture");
  git(rival, "config", "user.email", "fixture@example.invalid");
  writeFileSync(join(rival, "other.txt"), "concurrent\n");
  git(rival, "add", "other.txt");
  git(rival, "commit", "-m", "concurrent");
  const marker = installRace(root, remote, rival);
  const result = await publishSnapshot(root, "main", snapshot("07"));
  assert.equal(result.attempt, 2);
  assert.equal(git(remote, "show", "main:other.txt"), "concurrent");
  assert.deepEqual(remoteRows(remote), [snapshot("06"), snapshot("07")]);
  assert.equal(readFileSync(marker, "utf8"), "");
});

test("a newer concurrent observation is preserved and stale input is not admitted", async (t) => {
  const { root, remote } = fixture(t);
  const rival = join(root, "..", "rival");
  git(root, "clone", remote, rival);
  git(rival, "config", "user.name", "Fixture");
  git(rival, "config", "user.email", "fixture@example.invalid");
  const newer = snapshot("08");
  const journal = join(rival, "data/2026-09-09/public-status.jsonl");
  writeFileSync(journal, readFileSync(journal, "utf8") + JSON.stringify(newer) + "\n");
  writeFileSync(join(rival, "data/latest/public-status.json"), JSON.stringify(newer, null, 2) + "\n");
  writeFileSync(join(rival, "reports/2026-09-09.md"), renderReport(newer));
  git(rival, "add", ".");
  git(rival, "commit", "-m", "newer collection");
  installRace(root, remote, rival);
  await assert.rejects(publishSnapshot(root, "main", snapshot("07")), /stale/);
  assert.deepEqual(remoteRows(remote), [snapshot("06"), newer]);
  assert.deepEqual(JSON.parse(git(remote, "show", "main:data/latest/public-status.json")), newer);
});

test("permanent server rejection never retries or alters canonical history", async (t) => {
  const { root, remote } = fixture(t);
  const head = git(remote, "rev-parse", "main");
  const marker = join(root, "..", "rejected");
  const hooks = join(remote, "hooks");
  git(remote, "config", "core.hooksPath", hooks);
  writeFileSync(join(hooks, "pre-receive"), `#!/bin/sh\necho rejected >> '${marker}'\nexit 1\n`, { mode: 0o755 });
  await assert.rejects(publishSnapshot(root, "main", snapshot("07")), /without a safe fast-forward retry/);
  assert.equal(git(remote, "rev-parse", "main"), head);
  assert.equal(readFileSync(marker, "utf8"), "rejected\n");
});

test("same collection identity with different bytes cannot be republished", async (t) => {
  const { root, remote } = fixture(t);
  const original = snapshot("07");
  await publishSnapshot(root, "main", original);
  await assert.rejects(publishSnapshot(root, "main", {...snapshot("08"),run:original.run}), /conflicting/);
  assert.deepEqual(remoteRows(remote), [snapshot("06"), original]);
});
