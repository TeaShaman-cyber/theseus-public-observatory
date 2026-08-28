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
