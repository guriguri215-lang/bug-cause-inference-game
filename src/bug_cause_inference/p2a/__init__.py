"""P2a patch-grounded adapter feasibility boundary."""

from bug_cause_inference.p2a.compatibility import (
    FORMAL_SIX_POLICY_IDS,
    LEGACY_VARIANT_IDS,
    LegacyCompatibilityError,
    LegacyCompatibilityReport,
    run_legacy_exact_compatibility,
)

__all__ = [
    "FORMAL_SIX_POLICY_IDS",
    "LEGACY_VARIANT_IDS",
    "LegacyCompatibilityError",
    "LegacyCompatibilityReport",
    "run_legacy_exact_compatibility",
]
