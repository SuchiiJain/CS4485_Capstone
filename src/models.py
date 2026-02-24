"""
Data models for the Docrot Detector.

Contains dataclasses representing fingerprints, semantic deltas,
change events, and doc alerts used throughout the pipeline.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Semantic Fingerprint — captures the "meaning" of a single function/method
# ---------------------------------------------------------------------------

@dataclass
class SignatureFeatures:
    """Function signature details (name, params, defaults, return annotation)."""
    name: str = ""
    params: List[str] = field(default_factory=list)
    defaults: List[str] = field(default_factory=list)
    return_annotation: Optional[str] = None


@dataclass
class ControlFlowFeatures:
    """Shape of if/elif/else, loops, early returns."""
    if_count: int = 0
    elif_count: int = 0
    else_count: int = 0
    for_count: int = 0
    while_count: int = 0
    early_return_count: int = 0


@dataclass
class ConditionFeatures:
    """Operators and comparisons used in branching."""
    comparison_ops: List[str] = field(default_factory=list)   # e.g. ["Gt", "Eq"]
    boolean_ops: List[str] = field(default_factory=list)      # e.g. ["And", "Or"]


@dataclass
class CallFeatures:
    """External / notable function/method calls."""
    call_names: List[str] = field(default_factory=list)       # e.g. ["db.query", "requests.get"]


@dataclass
class SideEffectFeatures:
    """Signals for DB/file/network/auth writes."""
    db_calls: List[str] = field(default_factory=list)
    file_calls: List[str] = field(default_factory=list)
    network_calls: List[str] = field(default_factory=list)
    auth_calls: List[str] = field(default_factory=list)


@dataclass
class ExceptionFeatures:
    """Raised / caught / propagated exceptions."""
    raises: List[str] = field(default_factory=list)
    except_handlers: List[str] = field(default_factory=list)
    has_bare_except: bool = False


@dataclass
class ReturnFeatures:
    """Return expressions and branch outcomes."""
    return_count: int = 0
    returns_none: bool = False


@dataclass
class FunctionFingerprint:
    """Complete semantic fingerprint for one function/method."""
    stable_id: str = ""                         # unique ID: "file::class.method" or "file::func"
    file_path: str = ""
    signature: SignatureFeatures = field(default_factory=SignatureFeatures)
    control_flow: ControlFlowFeatures = field(default_factory=ControlFlowFeatures)
    conditions: ConditionFeatures = field(default_factory=ConditionFeatures)
    calls: CallFeatures = field(default_factory=CallFeatures)
    side_effects: SideEffectFeatures = field(default_factory=SideEffectFeatures)
    exceptions: ExceptionFeatures = field(default_factory=ExceptionFeatures)
    returns: ReturnFeatures = field(default_factory=ReturnFeatures)
    is_public: bool = True                      # True if name does NOT start with "_"
    fingerprint_hash: str = ""                  # deterministic hash of all features

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for JSON persistence."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FunctionFingerprint":
        """Reconstruct a FunctionFingerprint from a plain dict."""
        return cls(
            stable_id=data.get("stable_id", ""),
            file_path=data.get("file_path", ""),
            signature=SignatureFeatures(**data.get("signature", {})),
            control_flow=ControlFlowFeatures(**data.get("control_flow", {})),
            conditions=ConditionFeatures(**data.get("conditions", {})),
            calls=CallFeatures(**data.get("calls", {})),
            side_effects=SideEffectFeatures(**data.get("side_effects", {})),
            exceptions=ExceptionFeatures(**data.get("exceptions", {})),
            returns=ReturnFeatures(**data.get("returns", {})),
            is_public=data.get("is_public", True),
            fingerprint_hash=data.get("fingerprint_hash", ""),
        )


# ---------------------------------------------------------------------------
# Semantic Delta — diff between old and new fingerprints of one function
# ---------------------------------------------------------------------------

@dataclass
class SemanticDelta:
    """Result of comparing two FunctionFingerprints."""
    only_comment_or_formatting_changes: bool = False
    literal_changed: bool = False
    default_arg_changed: bool = False
    condition_logic_changed: bool = False
    loop_semantics_changed: bool = False
    return_logic_changed: bool = False
    public_signature_changed: bool = False
    public_api_added_or_removed: bool = False
    side_effect_changed: bool = False
    auth_or_permission_logic_changed: bool = False
    exception_behavior_changed: bool = False
    core_control_path_added_or_removed: bool = False


# ---------------------------------------------------------------------------
# Change Event — one per function that changed, emitted by the comparator
# ---------------------------------------------------------------------------

@dataclass
class ChangeEvent:
    """A scored change event for a single function."""
    function_id: str = ""
    code_path: str = ""
    event_type: str = ""          # "function_added" | "function_removed" | "semantic_change"
    score: int = 0
    critical: bool = False
    reasons: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Doc Alert — final output telling user which docs may be stale
# ---------------------------------------------------------------------------

@dataclass
class DocAlert:
    """Alert recommending a documentation file be reviewed."""
    doc_path: str = ""
    message: str = ""
    cumulative_score: int = 0
    critical_found: bool = False
    reasons: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
