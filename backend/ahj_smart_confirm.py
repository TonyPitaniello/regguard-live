"""
Paid-only AHJ confirm — thin wrapper over ``paid_local_confirm`` FinOps mode.

Kept for backward-compatible imports from pro_deep_analysis / tests.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def paid_smart_confirm_enabled() -> bool:
    from paid_local_confirm import paid_local_confirm_enabled

    return paid_local_confirm_enabled()


def run_paid_ahj_smart_confirm(
    analysis: Dict[str, Any],
    *,
    city: str = "",
    state: str = "",
    zip_code: str = "",
    email: str = "",
) -> Dict[str, Any]:
    """Delegate to paid_local_confirm FinOps mode."""
    if not isinstance(analysis, dict) or not paid_smart_confirm_enabled():
        return analysis
    from paid_local_confirm import run_paid_local_confirm

    return run_paid_local_confirm(
        analysis,
        city=city,
        state=state,
        zip_code=zip_code,
        email=email,
    )
