# Compilence public mathematical claims audit

This is a narrow, reproducible external audit of four mathematical formulations published by Compilence. It is not an assessment of the project as a whole, its private specifications, or unpublished books.

## Source scope

Inspected public sources:

- Compilence Technology Overview: https://www.compilence.com/overview
- Compilence Research page: https://www.compilence.com/research
- Dual-Layer SPO Architecture: https://doi.org/10.5281/zenodo.19261510
- Deterministic Inference Engine: https://doi.org/10.5281/zenodo.19319709
- Stationarity by Governance: https://doi.org/10.5281/zenodo.19367887

The public pages explicitly state that fuller derivations exist in the Semantic Science Series. Therefore a negative result here means only that the tested public wording does not follow under the minimal assumptions encoded in the corresponding claim. A private or later specification may add assumptions that change the result.

## Results

| Claim | Public formulation tested | Result | Boundary |
| --- | --- | --- | --- |
| Authority tier lock | `score = embedding_similarity × tier_weight` together with non-overridable `T1 > T2` authority | `VERIFIED_FALSE` | Multiplicative scoring alone cannot guarantee strict T1-over-T2 ordering for unrestricted positive similarities and finite positive weights. Lexicographic gating or additional bounds could restore the invariant. |
| Frozen VAR stationarity | A frozen semantic graph / fixed VAR coefficients are sufficient by themselves for stationarity | `VERIFIED_FALSE` | Fixed coefficients alone do not imply covariance stationarity. The claim may be repairable if the full system also enforces a stability condition such as spectral radius `< 1`. |
| Structural refusal by rank deficit | Rank deficiency of `A` by itself means `Ax=b` cannot be satisfied | `VERIFIED_FALSE` | A rank-deficient system can be consistent with non-unique solutions. Refusal can still be a valid policy if uniqueness is required, or inconsistency can be tested via `rank(A) < rank([A|b])`. |
| Algebra of Meaning semiring | Public material is sufficient to independently verify the claimed non-commutative semiring | `UNDER_SPECIFIED` | The public overview exposes examples and identities but not enough of the full operator/axiom system to independently establish the semiring laws. |

## Reproduce

The three mathematical checks use the same pinned Wolfram MCP verifier introduced by the parent verification pilot. CI executes each claim independently and then validates the Compilence claim graph against the generated receipts plus the stable source-scope receipt.

```bash
npm ci --prefix verification/wolfram
node --test verification/wolfram/verify.test.mjs

node verification/wolfram/verify.mjs \
  verification/claims/compilence-tier-lock.json \
  verification/receipts/compilence-tier-lock.json

node verification/wolfram/verify.mjs \
  verification/claims/compilence-stationarity-freeze.json \
  verification/receipts/compilence-stationarity-freeze.json

node verification/wolfram/verify.mjs \
  verification/claims/compilence-rank-deficit.json \
  verification/receipts/compilence-rank-deficit.json

node verification/wolfram/verify-graph.mjs \
  verification/compilence-audit-claim-graph.json \
  verification/receipts/compilence-audit-claim-graph.json
```

## Epistemic interpretation

`VERIFIED_FALSE` is deliberately local: the exact public formulation encoded in the claim fails under the stated assumptions. It does **not** mean that Compilence, E.L.I.A., ARC, or the unpublished Algebra/Geometry/Theory of Meaning is invalid.

`UNDER_SPECIFIED` is not a failure result. It means the inspected public sources do not currently expose enough formal material for the independent proof requested by that claim.

The purpose of this artifact is constructive reproducibility: make assumptions explicit, attach executable checks, and make it easy for the authors to point to missing premises or stronger formulations.
