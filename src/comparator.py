"""
Comparator — Compares old vs new function fingerprints,
computes semantic deltas, and produces scored ChangeEvents.

This is the core logic that decides "did this function change enough
to potentially make documentation stale?"
"""

from typing import Dict, List, Tuple

from src.models import (
    ChangeEvent,
    FunctionFingerprint,
    SemanticDelta,
)


# ---------------------------------------------------------------------------
# Feature-level diff
# ---------------------------------------------------------------------------

def diff_features(old_fp: FunctionFingerprint,
                  new_fp: FunctionFingerprint) -> SemanticDelta:
    """
    Compare two fingerprints feature-by-feature and return a SemanticDelta
    describing what changed.

    Each boolean on SemanticDelta corresponds to a scoring category
    from the brainstorming doc.

    Args:
        old_fp: The stored (baseline) fingerprint.
        new_fp: The freshly extracted fingerprint.

    Returns:
        A SemanticDelta with flags set for each type of change detected.
    """
    delta = SemanticDelta()

    # --- Signature changes ---
    sig_changed = (
        old_fp.signature.params != new_fp.signature.params
        or old_fp.signature.name != new_fp.signature.name
        or old_fp.signature.return_annotation != new_fp.signature.return_annotation
    )
    if sig_changed and (old_fp.is_public or new_fp.is_public):
        delta.public_signature_changed = True

    # Default argument change (separate from full signature change)
    if old_fp.signature.defaults != new_fp.signature.defaults:
        delta.default_arg_changed = True

    # --- Public API visibility change ---
    if old_fp.is_public != new_fp.is_public:
        delta.public_api_added_or_removed = True

    # --- Condition logic changes ---
    if (old_fp.conditions.comparison_ops != new_fp.conditions.comparison_ops
            or old_fp.conditions.boolean_ops != new_fp.conditions.boolean_ops):
        delta.condition_logic_changed = True

    # --- Loop semantics changes ---
    if (old_fp.control_flow.for_count != new_fp.control_flow.for_count
            or old_fp.control_flow.while_count != new_fp.control_flow.while_count):
        delta.loop_semantics_changed = True

    # --- Return logic changes ---
    if (old_fp.returns.return_count != new_fp.returns.return_count
            or old_fp.returns.returns_none != new_fp.returns.returns_none):
        delta.return_logic_changed = True

    # --- Core control path changes ---
    old_cf = old_fp.control_flow
    new_cf = new_fp.control_flow
    if (old_cf.if_count != new_cf.if_count
            or old_cf.elif_count != new_cf.elif_count
            or old_cf.else_count != new_cf.else_count
            or old_cf.early_return_count != new_cf.early_return_count):
        delta.core_control_path_added_or_removed = True

    # --- Side-effect changes ---
    if (old_fp.side_effects.db_calls != new_fp.side_effects.db_calls
            or old_fp.side_effects.file_calls != new_fp.side_effects.file_calls
            or old_fp.side_effects.network_calls != new_fp.side_effects.network_calls):
        delta.side_effect_changed = True

    # --- Auth/permission logic changes ---
    if old_fp.side_effects.auth_calls != new_fp.side_effects.auth_calls:
        delta.auth_or_permission_logic_changed = True

    # --- Exception behavior changes ---
    if (old_fp.exceptions.raises != new_fp.exceptions.raises
            or old_fp.exceptions.except_handlers != new_fp.exceptions.except_handlers
            or old_fp.exceptions.has_bare_except != new_fp.exceptions.has_bare_except):
        delta.exception_behavior_changed = True

    # --- Literal/constant changes (calls differ but nothing else major) ---
    if (old_fp.calls.call_names != new_fp.calls.call_names
            and not delta.side_effect_changed
            and not delta.auth_or_permission_logic_changed):
        delta.literal_changed = True

    # --- Check if only non-semantic changes ---
    any_real_change = (
        delta.literal_changed
        or delta.default_arg_changed
        or delta.condition_logic_changed
        or delta.loop_semantics_changed
        or delta.return_logic_changed
        or delta.public_signature_changed
        or delta.public_api_added_or_removed
        or delta.side_effect_changed
        or delta.auth_or_permission_logic_changed
        or delta.exception_behavior_changed
        or delta.core_control_path_added_or_removed
    )
    if not any_real_change:
        delta.only_comment_or_formatting_changes = True

    return delta


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def score_semantic_delta(delta: SemanticDelta) -> Tuple[int, List[str], bool]:
    """
    Apply the weighted scoring model to a SemanticDelta.

    Scoring weights (from brainstorming.txt):
      0 pts — comment/formatting only, docstring-only
      1 pt  — literal/constant tweak, default argument tweak
      3 pts — condition changed, loop changed, return changed
      5 pts — public signature changed, public API added/removed (CRITICAL)
      6 pts — side-effect changed, auth/permission changed (CRITICAL)
      8 pts — exception behavior changed, core control path changed (CRITICAL)

    Args:
        delta: The SemanticDelta from diff_features().

    Returns:
        Tuple of (score, reasons_list, is_critical).
    """
    score = 0
    reasons: List[str] = []
    is_critical = False

    # 0-point noise — if only comments/formatting changed, short-circuit
    if delta.only_comment_or_formatting_changes:
        return 0, ["format/comment only"], False

    # 1-point minor changes
    if delta.literal_changed:
        score += 1
        reasons.append("literal/constant changed")
    if delta.default_arg_changed:
        score += 1
        reasons.append("default argument changed")

    # 3-point medium changes
    if delta.condition_logic_changed:
        score += 3
        reasons.append("branch condition changed")
    if delta.loop_semantics_changed:
        score += 3
        reasons.append("loop behavior changed")
    if delta.return_logic_changed:
        score += 3
        reasons.append("return behavior changed")

    # 5-point API contract changes (critical)
    if delta.public_signature_changed:
        score += 5
        reasons.append("public signature changed")
        is_critical = True
    if delta.public_api_added_or_removed:
        score += 5
        reasons.append("public API added/removed")
        is_critical = True

    # 6-point side effects / auth changes (critical)
    if delta.side_effect_changed:
        score += 6
        reasons.append("side-effect behavior changed")
        is_critical = True
    if delta.auth_or_permission_logic_changed:
        score += 6
        reasons.append("auth/permission logic changed")
        is_critical = True

    # 8-point high impact control/exception changes (critical)
    if delta.exception_behavior_changed:
        score += 8
        reasons.append("exception behavior changed")
        is_critical = True
    if delta.core_control_path_added_or_removed:
        score += 8
        reasons.append("core control path added/removed")
        is_critical = True

    return score, reasons, is_critical


# ---------------------------------------------------------------------------
# File-level comparison
# ---------------------------------------------------------------------------

def compare_file_functions(old_funcs: Dict[str, FunctionFingerprint],
                           new_funcs: Dict[str, FunctionFingerprint],
                           file_path: str) -> List[ChangeEvent]:
    """
    Compare all functions in a file between old and new snapshots.

    Handles three cases per function:
      - Added (in new but not old)   → score=5, critical if public
      - Removed (in old but not new) → score=5, critical if public
      - Modified (hash differs)      → diff_features → score_semantic_delta

    Functions whose hashes are identical are skipped entirely (no event).

    Args:
        old_funcs: Dict of {stable_id: FunctionFingerprint} from baseline.
        new_funcs: Dict of {stable_id: FunctionFingerprint} freshly extracted.
        file_path: Path to the source file (attached to events).

    Returns:
        List of ChangeEvent objects for functions that changed.
    """
    events: List[ChangeEvent] = []
    all_ids = set(old_funcs.keys()) | set(new_funcs.keys())

    for fn_id in sorted(all_ids):
        old_fp = old_funcs.get(fn_id)
        new_fp = new_funcs.get(fn_id)

        if old_fp is None and new_fp is not None:
            # Function was added
            is_critical = new_fp.is_public
            reasons = ["function added"]
            if is_critical:
                reasons[0] += " (public API)"
            events.append(ChangeEvent(
                function_id=fn_id,
                code_path=file_path,
                event_type="function_added",
                score=5,
                critical=is_critical,
                reasons=reasons,
            ))
        elif new_fp is None and old_fp is not None:
            # Function was removed
            is_critical = old_fp.is_public
            reasons = ["function removed"]
            if is_critical:
                reasons[0] += " (public API)"
            events.append(ChangeEvent(
                function_id=fn_id,
                code_path=file_path,
                event_type="function_removed",
                score=5,
                critical=is_critical,
                reasons=reasons,
            ))
        elif old_fp is not None and new_fp is not None:
            # Both exist — compare hashes first (fast path)
            if old_fp.fingerprint_hash == new_fp.fingerprint_hash:
                continue  # No change — skip entirely

            delta = diff_features(old_fp, new_fp)
            score, reasons, is_critical = score_semantic_delta(delta)
            if score > 0 or is_critical:
                events.append(ChangeEvent(
                    function_id=fn_id,
                    code_path=file_path,
                    event_type="semantic_change",
                    score=score,
                    critical=is_critical,
                    reasons=reasons,
                ))

    return events