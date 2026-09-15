import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { validateClaimGraph } from './verifier-lib.mjs';

const graphPath = path.resolve(process.argv[2] ?? 'verification/claim-graph.json');
const outputPath = path.resolve(process.argv[3] ?? 'verification/receipts/claim-graph.json');
const graph = JSON.parse(readFileSync(graphPath, 'utf8'));

function readJson(relativePath) {
  return JSON.parse(readFileSync(path.resolve(relativePath), 'utf8'));
}

const claims = Object.fromEntries(graph.nodes.map((node) => [node.claim_path, readJson(node.claim_path)]));
const receipts = Object.fromEntries(graph.nodes.map((node) => [node.receipt_path, readJson(node.receipt_path)]));

try {
  const checked = validateClaimGraph(graph, claims, receipts);
  const receipt = {
    schema_version: 'theseus.verification.graph_receipt.v1',
    graph_id: graph.graph_id,
    graph_path: path.relative(process.cwd(), graphPath),
    ...checked,
    finished_at: new Date().toISOString(),
    scope_note: graph.does_not_establish
  };
  mkdirSync(path.dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, `${JSON.stringify(receipt, null, 2)}\n`);
  console.log(JSON.stringify(receipt, null, 2));
} catch (error) {
  const receipt = {
    schema_version: 'theseus.verification.graph_receipt.v1',
    graph_id: graph.graph_id,
    graph_path: path.relative(process.cwd(), graphPath),
    graph_status: 'FAIL',
    error: error.message,
    finished_at: new Date().toISOString()
  };
  mkdirSync(path.dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, `${JSON.stringify(receipt, null, 2)}\n`);
  console.error(JSON.stringify(receipt, null, 2));
  process.exit(1);
}
