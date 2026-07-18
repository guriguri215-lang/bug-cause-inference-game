"""P2d one-step stop-relaxation audit.

P2d is an analysis-only, fixed-input, model-internal counterfactual. It does
not modify or recommend a deployable policy.
"""

from bug_cause_inference.p2d.stop_relaxation_audit import (
    P2DStopRelaxationAuditError,
    run_stop_relaxation_audit,
    validate_audit_summary,
)

__all__ = [
    "P2DStopRelaxationAuditError",
    "run_stop_relaxation_audit",
    "validate_audit_summary",
]
