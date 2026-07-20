# P2h task-scheduler second-domain replication audit

## Boundary

This is an analysis-only, fixed-input, hand-authored, non-IID, non-causal, non-deployable observation in one toy task-scheduler domain. It does not establish policy superiority, population generalization, or production scheduler properties.

## Frozen support

- Inputs: 10 buggy and 5 benign clean inputs.
- Policies: six accepted formal policies in their accepted order.
- Actions: ten accepted action IDs with accepted costs and semantics.
- Trajectories: 60 buggy plus 30 clean rows, normal execution only.

## Descriptive result

- Bug discovery: 12/60 (0.200000)
- First failure observed: 12/60 (0.200000)
- Clean false positive: 0/30 (0.000000)
- Function location top-1: 25/60 (0.416667)
- Function location top-3: 35/60 (0.583333)
- Function location MRR: 0.555192 (denominator 60)
- Cause top-1: 16/60 (0.266667)
- Fix-intent top-1: 16/60 (0.266667)
- Mean penalized cost to first failure: 11.733333
- Mean cumulative cost: 3.922222

## Per-policy description

| Policy | Bug discovery | Clean FP | Location top-3 | Cause top-1 | Fix top-1 | Mean cost |
|---|---:|---:|---:|---:|---:|---:|
| `fixed_checklist` | 2/10 (0.200000) | 0/5 (0.000000) | 5/10 (0.500000) | 2/10 (0.200000) | 3/10 (0.300000) | 4.2 |
| `test_first` | 2/10 (0.200000) | 0/5 (0.000000) | 5/10 (0.500000) | 2/10 (0.200000) | 3/10 (0.300000) | 4.2 |
| `coverage_first` | 2/10 (0.200000) | 0/5 (0.000000) | 5/10 (0.500000) | 2/10 (0.200000) | 3/10 (0.300000) | 4.133333 |
| `recent_diff_first` | 2/10 (0.200000) | 0/5 (0.000000) | 10/10 (1.000000) | 2/10 (0.200000) | 3/10 (0.300000) | 5.933333 |
| `cause_only_p1a_style` | 2/10 (0.200000) | 0/5 (0.000000) | 5/10 (0.500000) | 4/10 (0.400000) | 2/10 (0.200000) | 2.533333 |
| `expected_utility_per_cost` | 2/10 (0.200000) | 0/5 (0.000000) | 5/10 (0.500000) | 4/10 (0.400000) | 2/10 (0.200000) | 2.533333 |

## Identity

- Schema: `p2h_task_scheduler_second_domain_replication.v1`
- Domain manifest: `343746ea65d6649726e116e529c8a0e83d07f7c8d72e76c2074e21f24941304b`
- Accepted dependency identity: `c3ca2a00d1729b003a6ac12ba73853cb3d1c86710d0fa29b4aee61e55c19179f`
- Pre-outcome freeze identity: `105a0076aaedef34c06f00b1ce43b351a74f07a364e5f23b2e72e41646e09b52`
- Row digest: `f53d6a1d2d74cca3510ca1495814baa096ef4b1e114f22c7797a3cf3aab4ee72`
- Aggregate digest: `6befa920087340f33d69ac8912cf4c5e129980b5f2e6a2087e022e01e1a8e531`
- Summary digest: `68a169c60dc25eda886df608560f1698eb5e09f05ed2563f2aef622b49ae3df3`

The JSON artifact is authoritative for per-input, per-family, per-policy, raw trace, denominator, terminal-partition, and identity details.
