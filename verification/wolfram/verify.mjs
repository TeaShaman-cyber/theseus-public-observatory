import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { classifyEquality, parseMcporterWolframJson } from './verifier-lib.mjs';

const verifierDir = path.dirname(fileURLToPath(import.meta.url));
const claimPath = path.resolve(process.argv[2] ?? 'verification/claims/tid-navier-stokes-threshold.json');
const receiptPath = path.resolve(process.argv[3] ?? 'verification/receipts/tid-navier-stokes-threshold.json');
const claim = JSON.parse(readFileSync(claimPath, 'utf8'));

const mcporter = path.join(verifierDir, 'node_modules', '.bin', 'mcporter');
const args = [
  'call',
  'wolfram.WolframLanguageEvaluator',
  '--args',
  JSON.stringify({ code: claim.wolfram_code, timeConstraint: 30 }),
  '--output',
  'json',
  '--timeout',
  '45000'
];

const startedAt = new Date().toISOString();
const run = spawnSync(mcporter, args, {
  cwd: verifierDir,
  encoding: 'utf8',
  timeout: 50000
});

const baseReceipt = {
  schema_version: 'theseus.verification.receipt.v1',
  claim_id: claim.claim_id,
  claim_path: path.relative(process.cwd(), claimPath),
  verifier: 'WolframLanguageEvaluator',
  verifier_endpoint: 'https://agenttools.wolfram.com/mcp',
  mcp_client: 'mcporter',
  mcp_client_version: '0.9.0',
  wolfram_code_sha256: createHash('sha256').update(claim.wolfram_code).digest('hex'),
  started_at: startedAt,
  finished_at: new Date().toISOString()
};

function persist(receipt) {
  mkdirSync(path.dirname(receiptPath), { recursive: true });
  writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`);
}

if (run.error || run.status !== 0) {
  const receipt = {
    ...baseReceipt,
    verification_status: 'VERIFIER_ERROR',
    transport_exit_code: run.status,
    error: run.error?.message ?? run.stderr.trim().slice(0, 2000)
  };
  persist(receipt);
  console.error(JSON.stringify(receipt, null, 2));
  process.exit(2);
}

let result;
try {
  result = parseMcporterWolframJson(run.stdout);
} catch (error) {
  const receipt = {
    ...baseReceipt,
    verification_status: 'VERIFIER_ERROR',
    transport_exit_code: run.status,
    error: error.message
  };
  persist(receipt);
  console.error(JSON.stringify(receipt, null, 2));
  process.exit(2);
}

const verificationStatus = classifyEquality(result.equals_asserted);
const receipt = {
  ...baseReceipt,
  verification_status: verificationStatus,
  transport_exit_code: run.status,
  exact_result: result.exact,
  decimal_result: result.decimal,
  asserted_exact_value: claim.asserted_exact_value,
  asserted_decimal_value: claim.asserted_decimal_value,
  expected_verification_status: claim.expected_verification_status,
  expected_exact_result: claim.expected_exact_result,
  scope_note: claim.does_not_establish
};
persist(receipt);
console.log(JSON.stringify(receipt, null, 2));

const expected =
  verificationStatus === claim.expected_verification_status &&
  result.exact === claim.expected_exact_result;
process.exit(expected ? 0 : 1);
