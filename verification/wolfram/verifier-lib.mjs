export function parseMcporterWolframJson(stdout) {
  const envelope = JSON.parse(stdout);
  const textBlock = envelope?.content?.find?.((item) => item?.type === 'text');
  if (!textBlock || typeof textBlock.text !== 'string') {
    throw new Error('Wolfram MCP response has no text content block');
  }

  const match = textBlock.text.match(/^Out\[\d+\]=\s*("(?:[^"\\]|\\.)*")\s*$/s);
  if (!match) {
    throw new Error(`Unexpected Wolfram evaluator output: ${textBlock.text}`);
  }

  const rawJson = JSON.parse(match[1]);
  return JSON.parse(rawJson);
}

export function classifyEquality(value) {
  if (value === true) return 'VERIFIED_TRUE';
  if (value === false) return 'VERIFIED_FALSE';
  return 'UNKNOWN';
}
