# P2c Result Interpretation

## Question and Frozen Inputs

P2c answers one fixed-input descriptive question: under the accepted P2a/P2b contract, did each frozen policy select a P2b direct detector, did an unselected detector remain budget-feasible at recorded states, and where did the accepted runner terminate?

The inputs are the accepted P2a expansion-only buggy cohort, P2a runner and saved outcomes, P2b detector mapping and minimum detecting costs, fixed catalog, budget, settings, seed, and six formal policies. P2c does not change or tune any of them. It replays the accepted P2a semantic path only to record the frozen trajectories and requires exact agreement with the accepted P2a outcomes and P2b mapping.

The population is 10 variants by 6 policies, or 60 ordered pairs. Variants are ordered `P2A-BUG-001` through `P2A-BUG-010`. Within each variant, the formal policy order is:

1. `fixed_checklist`
2. `test_first`
3. `coverage_first`
4. `recent_diff_first`
5. `cause_only_p1a_style`
6. `expected_utility_per_cost`

The cohort is hand-authored, same-domain, fixed, and non-iid. These 60 pairs are the entire P2c support; they are not a sample that supports population inference.

## Three Overlapping Axes

P2c records three axes for each pair:

- **Selection:** whether the policy selected an accepted P2b direct detecting action. On this fixed replay, selected detectors and observed discoveries agree exactly.
- **Recorded budget state:** whether an unexecuted direct detector fit the remaining budget at an initial, pre-action, or terminal recorded state.
- **Termination:** the exact accepted runner stop reason, step, and cumulative cost.

These axes overlap. They are not mutually exclusive causal partitions of a miss. In particular, terminal feasibility is a budget fact at the recorded terminal state, not permission to continue execution. Once a stop condition has fired, `terminal detector feasible` does not mean the policy could still select the detector after stopping.

The detector mapping is inherited from P2b. It is ground-truth-informed and unavailable to the deployable policies, so P2c is analysis-only and non-deployable.

## Exact Overall Result

```text
ordered support                             60 / 60
accepted P2a replay agreement               60 / 60
accepted P2b detector mapping agreement     60 / 60
direct detector selected/discovered          8 / 60
direct detector not selected                52 / 60
initial detector budget-feasible            60 / 60
any pre-action detector budget-feasible     60 / 60
all pre-action states detector feasible     52 / 60
terminal detector feasible                  52 / 60
unselected terminal detector feasible       52 / 52
unselected terminal detector infeasible      0 / 52
stop: no-bug probability threshold          58
stop: budget limit                           2
other stop reasons                           0
```

The 24-row selection-by-terminal-feasibility-by-stop-reason cross-tab has three nonzero cells:

| Detector selected | Terminal detector feasible | Stop reason | Count |
|---|---|---|---:|
| no | yes | `no_bug_probability_threshold` | 52 |
| yes | no | `no_bug_probability_threshold` | 6 |
| yes | no | `budget_limit` | 2 |

This table preserves overlap; it does not assign a single causal reason to any miss.

## Result by Policy

| Policy | Support | Selected/discovered | Not selected | Unselected terminal-feasible | Threshold stops | Budget stops |
|---|---:|---:|---:|---:|---:|---:|
| `fixed_checklist` | 10 | 2 | 8 | 8/8 | 10 | 0 |
| `test_first` | 10 | 2 | 8 | 8/8 | 10 | 0 |
| `coverage_first` | 10 | 2 | 8 | 8/8 | 8 | 2 |
| `recent_diff_first` | 10 | 2 | 8 | 8/8 | 10 | 0 |
| `cause_only_p1a_style` | 10 | 0 | 10 | 10/10 | 10 | 0 |
| `expected_utility_per_cost` | 10 | 0 | 10 | 10/10 | 10 | 0 |

The equal `2/10` values for the first four policies and `0/10` values for the last two are descriptive observations on this support. They are not a policy ranking, superiority test, or inferential comparison.

## Result by Variant and Bucket

The eight discoveries are the first four formal policies on `P2A-BUG-001` and `P2A-BUG-002`.

| Variant | Support | Selected/discovered | Not selected | Unselected terminal-feasible | Threshold stops | Budget stops |
|---|---:|---:|---:|---:|---:|---:|
| `P2A-BUG-001` | 6 | 4 | 2 | 2/2 | 5 | 1 |
| `P2A-BUG-002` | 6 | 4 | 2 | 2/2 | 5 | 1 |
| `P2A-BUG-003` | 6 | 0 | 6 | 6/6 | 6 | 0 |
| `P2A-BUG-004` | 6 | 0 | 6 | 6/6 | 6 | 0 |
| `P2A-BUG-005` | 6 | 0 | 6 | 6/6 | 6 | 0 |
| `P2A-BUG-006` | 6 | 0 | 6 | 6/6 | 6 | 0 |
| `P2A-BUG-007` | 6 | 0 | 6 | 6/6 | 6 | 0 |
| `P2A-BUG-008` | 6 | 0 | 6 | 6/6 | 6 | 0 |
| `P2A-BUG-009` | 6 | 0 | 6 | 6/6 | 6 | 0 |
| `P2A-BUG-010` | 6 | 0 | 6 | 6/6 | 6 | 0 |

| Bucket | Support | Selected/discovered | Not selected | Unselected terminal-feasible | Threshold stops | Budget stops |
|---|---:|---:|---:|---:|---:|---:|
| `boundary_precision` | 12 | 8 | 4 | 4/4 | 10 | 2 |
| `missing_optional_input` | 12 | 0 | 12 | 12/12 | 12 | 0 |
| `config_normalization` | 12 | 0 | 12 | 12/12 | 12 | 0 |
| `state_sequence` | 12 | 0 | 12 | 12/12 | 12 | 0 |
| `spec_semantics` | 12 | 0 | 12 | 12/12 | 12 | 0 |

## P2a Replay and P2b Detector Provenance

All 60 replayed discovery outcomes match the accepted P2a expansion-only saved outcomes. P2c also requires exact agreement with the accepted P2b direct-detector IDs and minimum costs `2,2,2,2,3,3,4,4,2,2` in variant order.

The reduced trajectories record selected actions, observations needed for consistency checks, remaining budget, feasible detector IDs, stop reason, step, and cost. They intentionally exclude full posterior and action-score payloads. Exact stop reconstruction is therefore supported by generation-time reconstruction, frozen source identity, accepted pair-level anchors, and fresh replay evidence rather than by recomputing every internal score from the reduced artifact alone.

## Versioned Artifacts and Identity

The tracked artifacts contain the same validated summary:

- [Versioned JSON artifact](../src/bug_cause_inference/p2c/artifacts/p2c_frozen_policy_trajectory_audit_v1.json) — 387,424 bytes; SHA-256 `1ebfb62edd5034fd57ea69e18c3eb647a3a8746946ecb98d80b66fa127d989d7`.
- [Versioned Markdown artifact](../src/bug_cause_inference/p2c/artifacts/p2c_frozen_policy_trajectory_audit_v1.md) — 389,004 bytes; SHA-256 `ee9bfda6a7b352ff770fa3025dff4d4feb94e4e36201d256a76de6d569286666`.

The compact canonical validated-summary digest is `3872257449d76453f6910b56d28f8e4fdf6c7bb7de30410b2d26335143c0392c`. The 43-file identity-contract digest is `1a7c59b40dc837b1c2199a6f1fe8fc8016b87400df89eda05c00e28f0b0767bc`.

The 43-file contract covers accepted P1b/P2a/P2b inputs plus the P2b diagnostic source and artifact pair. Portable accepted identities use SHA-256 after CRLF-to-LF normalization so Linux LF and Windows CRLF checkouts share one accepted identity. Parsed-input caching and same-run pre/post drift detection separately use exact raw working-tree bytes. Portable identity and raw-byte drift protection serve different purposes and must not be substituted for each other.

Accepted upstream artifacts are unchanged:

```text
P2a JSON      1699240 / d7e69fa62513f5bbae22d570e39b841401f5110b6cd1e45701c53393eb0ef3df
P2a Markdown  1701581 / 017c5e3d9281e59e0b115a825a5f0e08f90a5e15a1e331514296adf443a2808a
P2a summary             / 3dea5aaf38e1d9a46fd1a9ed973cb02c3fabf7ec933f2bb1c6df4f97446a9629
P2b JSON       144393 / 1bbb71c5627f756f5dba3aba4f5f333f287f2fbacbb805e50118074d08ce928d
P2b Markdown   146660 / ad53651027e024febc04708763398112b81f1bf69aea4f104d94c70f4590ac3b
P2b summary             / 873423a2cd15908300d604a970664152d931a8a306f64c797122851f887702e2
```

## Reproduction and Verification

Run the targeted P2c tests, full suite, and P1b real-diff validator without overwriting tracked artifacts:

```bash
python -B -m pytest tests/test_p2c_trajectory_audit.py tests/test_p2c_reports.py -q -p no:cacheprovider
python -B -m pytest -q -p no:cacheprovider
python -m bug_cause_inference.p1b.real_diff --validate
```

The targeted tests verify the exact population and order, accepted P2a replay, P2b mapping and costs, trajectory and stop consistency, aggregate and 24-row cross-tab reconstruction, fail-closed mutations, 43-file identity, deterministic bytes, and JSON/Markdown semantic agreement.

For two isolated fresh P2c runs, use temporary output paths and compare them with the tracked pair. This procedure does not write to tracked artifacts:

```python
import hashlib
import json
import tempfile
from pathlib import Path

from bug_cause_inference.p2c import reports
from bug_cause_inference.p2c import trajectory_audit as audit

root = Path.cwd()
tracked_json = root / "src/bug_cause_inference/p2c/artifacts/p2c_frozen_policy_trajectory_audit_v1.json"
tracked_md = root / "src/bug_cause_inference/p2c/artifacts/p2c_frozen_policy_trajectory_audit_v1.md"

with tempfile.TemporaryDirectory(prefix="p2c-verify-") as work:
    outputs = []
    for label in ("a", "b"):
        out = Path(work) / label
        summary = audit.run_trajectory_audit()
        reports.save_p2c_report(
            summary,
            json_path=out / "audit.json",
            markdown_path=out / "audit.md",
        )
        outputs.append(out)

    assert outputs[0].joinpath("audit.json").read_bytes() == tracked_json.read_bytes()
    assert outputs[1].joinpath("audit.json").read_bytes() == tracked_json.read_bytes()
    assert outputs[0].joinpath("audit.md").read_bytes() == tracked_md.read_bytes()
    assert outputs[1].joinpath("audit.md").read_bytes() == tracked_md.read_bytes()

summary = json.loads(tracked_json.read_text(encoding="utf-8"))
compact = json.dumps(summary, ensure_ascii=False, separators=(",", ":")).encode()
assert hashlib.sha256(compact).hexdigest() == "3872257449d76453f6910b56d28f8e4fdf6c7bb7de30410b2d26335143c0392c"
assert reports.summary_from_markdown(tracked_md.read_text(encoding="utf-8")) == summary
assert audit.identity_contract_digest(audit._identity_rows()) == audit.IDENTITY_CONTRACT_DIGEST
```

Closeout and release verification must not rerun the P2a or P2b outcome runners. Do not redirect any verification output onto the tracked P2c JSON or Markdown files.

## Acceptance and Provenance

The pre-outcome specification was independently reviewed before the first pair execution. The implementation review then required two P2c-only fail-closed validation corrections. Those corrections strengthened rejection of identity, mapping, type, discovery, and termination mutations without changing the frozen schema, metrics, classifications, support, order, observed 60 rows, aggregate result, or non-claims.

The controlling implementation was merged by [PR #30](https://github.com/guriguri215-lang/bug-cause-inference-game/pull/30):

```text
final accepted head   067b3c81eadaaf796a4dc9a3e3d7cbb58cedb6e9
merge commit          e58bbaf2a5eda90e21c8f578209f327f35f7a92d
PR CI                 29631772242 (run #54, success)
post-merge main CI    29632045921 (run #55, success)
```

Acceptance decisions remain separate:

- P2c software conformance final audit: accepted after final merged-tree review.
- P2c versioned artifact identity: accepted.
- P2c descriptive result: accepted for the exact fixed-input observations above.
- P2c public documentation: accepted after independent documentation review, required verification, and a separate status-closure re-review in this documentation slice.

The artifact's embedded acceptance fields remain non-self-accepting implementation-time records. External acceptance and review records provide these decisions; the artifact does not accept itself.

## Limitations and Non-Claims

- The cohort contains only 60 fixed same-domain pairs and is hand-authored and non-iid.
- The detector mapping is ground-truth-informed and unavailable to deployable policies.
- The three axes overlap and are not causal labels or mutually exclusive miss explanations.
- Terminal detector feasibility is not post-stop selectability and does not show that a policy “could have selected” an action after termination.
- The result does not establish policy superiority, inferiority, ranking, or a policy implementation defect.
- P2c does not add a seventh or new policy and does not tune the six frozen policies.
- There is no counterfactual replay, multi-step sequence or DP ceiling, optimality result, or general upper bound.
- There is no second domain, no-diff clean stress, confidence interval, bootstrap, significance, causal, inferential, generalization, production-performance, or production-readiness claim.
- Reduced traces exclude full posterior and action-score payloads.

## Deferred Questions

The following require separate pre-outcome specifications and reviews:

- a new or tuned deployable policy;
- counterfactual, sequence, or dynamic-programming analysis;
- no-diff clean stress or a second benchmark domain;
- inferential uncertainty, external validity, or production-readiness work.
