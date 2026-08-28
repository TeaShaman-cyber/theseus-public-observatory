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

export function validateClaimGraph(graph, claims, receipts) {
  const nodeIds = new Set(graph.nodes.map((node) => node.claim_id));

  for (const edge of graph.edges) {
    if (!nodeIds.has(edge.from) || !nodeIds.has(edge.to)) {
      throw new Error(`unknown graph node in edge ${edge.from} -> ${edge.to}`);
    }
  }

  const nodes = graph.nodes.map((node) => {
    const claim = claims[node.claim_path];
    const receipt = receipts[node.receipt_path];

    if (!claim || claim.claim_id !== node.claim_id) {
      throw new Error(`claim binding mismatch for ${node.claim_id}`);
    }
    if (claim.expected_verification_status !== node.expected_status) {
      throw new Error(`claim expected status mismatch for ${node.claim_id}`);
    }
    if (!receipt || receipt.claim_id !== node.claim_id) {
      throw new Error(`receipt binding mismatch for ${node.claim_id}`);
    }
    if (receipt.verification_status !== node.expected_status) {
      throw new Error(`receipt status mismatch for ${node.claim_id}`);
    }

    return {
      claim_id: node.claim_id,
      verification_status: receipt.verification_status
    };
  });

  return {
    graph_status: 'PASS',
    node_count: graph.nodes.length,
    edge_count: graph.edges.length,
    nodes
  };
}
