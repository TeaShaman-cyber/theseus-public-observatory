import test from 'node:test';
import assert from 'node:assert/strict';
import { parseMcporterWolframJson, classifyEquality } from './verifier-lib.mjs';

const sample = JSON.stringify({
  content: [{
    type: 'text',
    text: 'Out[1]= "{\\n\\t\\"exact\\":\\"1\\\\/7\\",\\n\\t\\"decimal\\":0.142857142857,\\n\\t\\"equals_asserted\\":false\\n}"'
  }]
});

test('parses nested RawJSON returned by Wolfram through mcporter', () => {
  const parsed = parseMcporterWolframJson(sample);
  assert.deepEqual(parsed, {
    exact: '1/7',
    decimal: 0.142857142857,
    equals_asserted: false
  });
});

test('classifies an explicit false equality as VERIFIED_FALSE', () => {
  assert.equal(classifyEquality(false), 'VERIFIED_FALSE');
});

test('classifies missing/non-boolean equality as UNKNOWN', () => {
  assert.equal(classifyEquality(null), 'UNKNOWN');
});

import * as verifierModule from './verifier-lib.mjs';

test('validates a two-node claim graph against claim and receipt status', () => {
  assert.equal(typeof verifierModule.validateClaimGraph, 'function');

  const graph = {
    nodes: [
      { claim_id: 'A', claim_path: 'claims/a.json', expected_status: 'VERIFIED_FALSE', receipt_path: 'receipts/a.json' },
      { claim_id: 'B', claim_path: 'claims/b.json', expected_status: 'VERIFIED_TRUE', receipt_path: 'receipts/b.json' }
    ],
    edges: [{ from: 'A', to: 'B', relation: 'related_to' }]
  };
  const claims = {
    'claims/a.json': { claim_id: 'A', expected_verification_status: 'VERIFIED_FALSE' },
    'claims/b.json': { claim_id: 'B', expected_verification_status: 'VERIFIED_TRUE' }
  };
  const receipts = {
    'receipts/a.json': { claim_id: 'A', verification_status: 'VERIFIED_FALSE' },
    'receipts/b.json': { claim_id: 'B', verification_status: 'VERIFIED_TRUE' }
  };

  assert.deepEqual(verifierModule.validateClaimGraph(graph, claims, receipts), {
    graph_status: 'PASS',
    node_count: 2,
    edge_count: 1,
    nodes: [
      { claim_id: 'A', verification_status: 'VERIFIED_FALSE' },
      { claim_id: 'B', verification_status: 'VERIFIED_TRUE' }
    ]
  });
});

test('rejects a claim graph edge that points to an unknown node', () => {
  const graph = {
    nodes: [
      { claim_id: 'A', claim_path: 'claims/a.json', expected_status: 'VERIFIED_FALSE', receipt_path: 'receipts/a.json' }
    ],
    edges: [{ from: 'A', to: 'B', relation: 'related_to' }]
  };
  const claims = {
    'claims/a.json': { claim_id: 'A', expected_verification_status: 'VERIFIED_FALSE' }
  };
  const receipts = {
    'receipts/a.json': { claim_id: 'A', verification_status: 'VERIFIED_FALSE' }
  };

  assert.throws(
    () => verifierModule.validateClaimGraph(graph, claims, receipts),
    /unknown graph node/
  );
});

test('rejects inconsistent claim or receipt bindings for a graph node', () => {
  const graph = {
    nodes: [
      { claim_id: 'A', claim_path: 'claims/a.json', expected_status: 'VERIFIED_FALSE', receipt_path: 'receipts/a.json' }
    ],
    edges: []
  };

  assert.throws(
    () => verifierModule.validateClaimGraph(
      graph,
      { 'claims/a.json': { claim_id: 'OTHER', expected_verification_status: 'VERIFIED_FALSE' } },
      { 'receipts/a.json': { claim_id: 'A', verification_status: 'VERIFIED_FALSE' } }
    ),
    /claim binding mismatch/
  );

  assert.throws(
    () => verifierModule.validateClaimGraph(
      graph,
      { 'claims/a.json': { claim_id: 'A', expected_verification_status: 'VERIFIED_FALSE' } },
      { 'receipts/a.json': { claim_id: 'A', verification_status: 'VERIFIED_TRUE' } }
    ),
    /receipt status mismatch/
  );
});
