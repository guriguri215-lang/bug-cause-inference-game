"""P2e bounded threshold-relaxation continuation audit.

P2e is an analysis-only, fixed-input, model-internal diagnostic.  It does not
modify, rank, or recommend a deployable policy.
"""

from bug_cause_inference.p2e.continuation_audit import (
    P2EContinuationAuditError,
    run_continuation_audit,
    validate_audit_summary,
)

__all__ = [
    "P2EContinuationAuditError",
    "run_continuation_audit",
    "validate_audit_summary",
]
