"""
Fingerprint Builder — Extracts semantic features from a normalized
function AST node and produces a FunctionFingerprint.

Each feature extractor targets one dimension of the scoring model
from brainstorming.txt (signature, control-flow, conditions, calls,
side-effects, exceptions, returns).
"""

import ast
import copy
import hashlib
import json
from typing import List, Optional

from src.models import (
    CallFeatures,
    ConditionFeatures,
    ControlFlowFeatures,
    ExceptionFeatures,
    FunctionFingerprint,
    ReturnFeatures,
    SideEffectFeatures,
    SignatureFeatures,
)


# ---------------------------------------------------------------------------
# Side-effect keyword classifiers
# ---------------------------------------------------------------------------

_DB_KEYWORDS = {
    "execute", "executemany", "commit", "rollback", "cursor",
    "query", "fetchone", "fetchall", "fetchmany",
    "insert", "update", "delete", "create_engine", "session",
}

_FILE_KEYWORDS = {
    "open", "read", "write", "close", "readlines", "writelines",
    "readline", "seek", "truncate", "flush", "mkdir", "makedirs",
    "remove", "unlink", "rename", "rmdir", "rmtree", "copyfile",
    "shutil.copy", "shutil.move", "pathlib",
}

_NETWORK_KEYWORDS = {
    "get", "post", "put", "patch", "delete", "head", "options",
    "request", "urlopen", "fetch", "send", "recv", "connect",
    "socket", "requests", "httpx", "aiohttp", "urllib",
}

_AUTH_KEYWORDS = {
    "login", "logout", "authenticate", "authorize", "auth",
    "permission", "permissions", "check_permission", "has_perm",
    "is_authenticated", "token", "jwt", "verify_token", "hash_password",
    "check_password", "set_password", "create_user",
}


# ---------------------------------------------------------------------------
# Feature extractors — one per fingerprint dimension
# ---------------------------------------------------------------------------

def extract_signature_features(fn_node: ast.FunctionDef) -> SignatureFeatures:
    """
    Extract function name, parameter names, default values, and return annotation.

    Maps to scoring:
      - Public signature change → +5 pts, critical trigger

    Args:
        fn_node: A (normalized) FunctionDef AST node.

    Returns:
        SignatureFeatures dataclass.
    """
    args = fn_node.args

    # Collect all parameter names (positional, keyword-only, *args, **kwargs)
    params: List[str] = []
    for arg in args.posonlyargs:
        params.append(arg.arg)
    for arg in args.args:
        params.append(arg.arg)
    if args.vararg:
        params.append(f"*{args.vararg.arg}")
    for arg in args.kwonlyargs:
        params.append(arg.arg)
    if args.kwarg:
        params.append(f"**{args.kwarg.arg}")

    # Collect default values as their AST dump strings for comparison
    defaults: List[str] = []
    for default_node in args.defaults:
        defaults.append(ast.dump(default_node))
    for default_node in args.kw_defaults:
        if default_node is not None:
            defaults.append(ast.dump(default_node))
        else:
            defaults.append("None")

    # Return annotation
    return_annotation: Optional[str] = None
    if fn_node.returns is not None:
        return_annotation = ast.dump(fn_node.returns)

    return SignatureFeatures(
        name=fn_node.name,
        params=params,
        defaults=defaults,
        return_annotation=return_annotation,
    )


def extract_control_flow_features(fn_node: ast.FunctionDef) -> ControlFlowFeatures:
    """
    Count control-flow structures: if/elif/else, for, while, early returns.

    Maps to scoring:
      - Core control path added/removed → +8 pts, critical trigger
      - Loop semantics changed → +3 pts

    Args:
        fn_node: A (normalized) FunctionDef AST node.

    Returns:
        ControlFlowFeatures dataclass.
    """
    if_count = 0
    elif_count = 0
    else_count = 0
    for_count = 0
    while_count = 0
    early_return_count = 0

    for node in ast.walk(fn_node):
        if isinstance(node, ast.If):
            if_count += 1
            # Count elif branches (chained If nodes in orelse)
            for child in node.orelse:
                if isinstance(child, ast.If):
                    elif_count += 1
            # Count else branch (orelse that is not empty and not just an If)
            if node.orelse and not isinstance(node.orelse[0], ast.If):
                else_count += 1
        elif isinstance(node, ast.For):
            for_count += 1
            if node.orelse:
                else_count += 1
        elif isinstance(node, ast.While):
            while_count += 1
            if node.orelse:
                else_count += 1
        elif isinstance(node, ast.Return):
            early_return_count += 1

    return ControlFlowFeatures(
        if_count=if_count,
        elif_count=elif_count,
        else_count=else_count,
        for_count=for_count,
        while_count=while_count,
        early_return_count=early_return_count,
    )


def extract_condition_features(fn_node: ast.FunctionDef) -> ConditionFeatures:
    """
    Collect comparison and boolean operators used in branching.

    Maps to scoring:
      - Condition expression changed → +3 pts

    Example: `if x > 10` uses Compare with op=Gt.

    Args:
        fn_node: A (normalized) FunctionDef AST node.

    Returns:
        ConditionFeatures dataclass.
    """
    comparison_ops: List[str] = []
    boolean_ops: List[str] = []

    for node in ast.walk(fn_node):
        if isinstance(node, ast.Compare):
            for op in node.ops:
                comparison_ops.append(type(op).__name__)
        elif isinstance(node, ast.BoolOp):
            boolean_ops.append(type(node.op).__name__)

    # Sort for deterministic comparison
    comparison_ops.sort()
    boolean_ops.sort()

    return ConditionFeatures(
        comparison_ops=comparison_ops,
        boolean_ops=boolean_ops,
    )


def _resolve_call_name(node: ast.Call) -> str:
    """Resolve a Call node's function to a dotted name string."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    elif isinstance(func, ast.Attribute):
        parts = []
        current = func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        parts.reverse()
        return ".".join(parts)
    return "<unknown>"


def extract_call_features(fn_node: ast.FunctionDef) -> CallFeatures:
    """
    Collect all function/method calls made inside the function body.

    Used for detecting side-effect and API call changes.

    Args:
        fn_node: A (normalized) FunctionDef AST node.

    Returns:
        CallFeatures dataclass.
    """
    call_names: List[str] = []

    for node in ast.walk(fn_node):
        if isinstance(node, ast.Call):
            name = _resolve_call_name(node)
            call_names.append(name)

    call_names.sort()
    return CallFeatures(call_names=call_names)


def _classify_call(name: str, keyword_set: set) -> bool:
    """Check if any part of the call name matches a keyword set."""
    name_lower = name.lower()
    parts = name_lower.split(".")
    for part in parts:
        if part in keyword_set:
            return True
    return False


def extract_side_effect_features(fn_node: ast.FunctionDef) -> SideEffectFeatures:
    """
    Classify calls into side-effect categories: DB, file, network, auth.

    Maps to scoring:
      - Side-effect behavior changed → +6 pts, critical trigger
      - Auth/permission logic changed → +6 pts, critical trigger

    Uses keyword lists to classify call names (e.g., "open" → file,
    "requests.get" → network, "cursor.execute" → db).

    Args:
        fn_node: A (normalized) FunctionDef AST node.

    Returns:
        SideEffectFeatures dataclass.
    """
    db_calls: List[str] = []
    file_calls: List[str] = []
    network_calls: List[str] = []
    auth_calls: List[str] = []

    for node in ast.walk(fn_node):
        if isinstance(node, ast.Call):
            name = _resolve_call_name(node)
            if _classify_call(name, _DB_KEYWORDS):
                db_calls.append(name)
            if _classify_call(name, _FILE_KEYWORDS):
                file_calls.append(name)
            if _classify_call(name, _NETWORK_KEYWORDS):
                network_calls.append(name)
            if _classify_call(name, _AUTH_KEYWORDS):
                auth_calls.append(name)

    db_calls.sort()
    file_calls.sort()
    network_calls.sort()
    auth_calls.sort()

    return SideEffectFeatures(
        db_calls=db_calls,
        file_calls=file_calls,
        network_calls=network_calls,
        auth_calls=auth_calls,
    )


def extract_exception_features(fn_node: ast.FunctionDef) -> ExceptionFeatures:
    """
    Detect raised exceptions, except handlers, and bare excepts.

    Maps to scoring:
      - Exception behavior changed significantly → +8 pts, critical trigger

    Args:
        fn_node: A (normalized) FunctionDef AST node.

    Returns:
        ExceptionFeatures dataclass.
    """
    raises: List[str] = []
    except_handlers: List[str] = []
    has_bare_except = False

    for node in ast.walk(fn_node):
        if isinstance(node, ast.Raise):
            if node.exc is not None:
                if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                    raises.append(node.exc.func.id)
                elif isinstance(node.exc, ast.Name):
                    raises.append(node.exc.id)
                else:
                    raises.append(ast.dump(node.exc))
            else:
                raises.append("re-raise")
        elif isinstance(node, ast.ExceptHandler):
            if node.type is not None:
                if isinstance(node.type, ast.Name):
                    except_handlers.append(node.type.id)
                elif isinstance(node.type, ast.Tuple):
                    for elt in node.type.elts:
                        if isinstance(elt, ast.Name):
                            except_handlers.append(elt.id)
                else:
                    except_handlers.append(ast.dump(node.type))
            else:
                has_bare_except = True

    raises.sort()
    except_handlers.sort()

    return ExceptionFeatures(
        raises=raises,
        except_handlers=except_handlers,
        has_bare_except=has_bare_except,
    )


def extract_return_features(fn_node: ast.FunctionDef) -> ReturnFeatures:
    """
    Count return statements and detect "returns None" patterns.

    Maps to scoring:
      - Return expression/branch outcome changed → +3 pts

    Args:
        fn_node: A (normalized) FunctionDef AST node.

    Returns:
        ReturnFeatures dataclass.
    """
    return_count = 0
    returns_none = False

    for node in ast.walk(fn_node):
        if isinstance(node, ast.Return):
            return_count += 1
            if node.value is None:
                returns_none = True
            elif isinstance(node.value, ast.Constant) and node.value.value is None:
                returns_none = True

    return ReturnFeatures(
        return_count=return_count,
        returns_none=returns_none,
    )


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_function_ast(fn_node: ast.FunctionDef) -> ast.FunctionDef:
    """
    Remove non-semantic noise from a function's AST so that
    formatting-only and comment-only edits are invisible.

    Normalization steps:
      - Strip leading docstring
      - (Post-MVP) Alpha-rename local variables to canonical names
      - (Post-MVP) Normalize import ordering if relevant

    Args:
        fn_node: The raw FunctionDef AST node.

    Returns:
        A cleaned copy of the node (or the same node, mutated).
    """
    # Deep copy to avoid mutating the original tree
    normalized = copy.deepcopy(fn_node)

    # Strip leading docstring from the function body
    if (normalized.body
            and isinstance(normalized.body[0], ast.Expr)
            and isinstance(normalized.body[0].value, ast.Constant)
            and isinstance(normalized.body[0].value.value, str)):
        normalized.body = normalized.body[1:]

    return normalized


# ---------------------------------------------------------------------------
# Hash
# ---------------------------------------------------------------------------

def stable_hash(features: dict) -> str:
    """
    Produce a deterministic hash string from a features dictionary.

    Used to quickly detect whether anything changed at all before
    doing an expensive feature-by-feature diff.

    Args:
        features: Dict of extracted features (must be JSON-serializable).

    Returns:
        A hex digest string.
    """
    canonical = json.dumps(features, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# High-level builder
# ---------------------------------------------------------------------------

def build_fingerprint(fn_node: ast.FunctionDef, file_path: str,
                      stable_id: str, is_public: bool) -> FunctionFingerprint:
    """
    Build a complete FunctionFingerprint from a (raw) function AST node.

    Orchestrates: normalize → extract all features → hash → assemble.

    Args:
        fn_node:   The FunctionDef AST node.
        file_path: Relative file path (stored in fingerprint for reference).
        stable_id: Pre-computed stable function ID.
        is_public: Whether the function is public.

    Returns:
        A fully populated FunctionFingerprint.
    """
    normalized = normalize_function_ast(fn_node)

    signature = extract_signature_features(normalized)
    control_flow = extract_control_flow_features(normalized)
    conditions = extract_condition_features(normalized)
    calls = extract_call_features(normalized)
    side_effects = extract_side_effect_features(normalized)
    exceptions = extract_exception_features(normalized)
    returns = extract_return_features(normalized)

    # Build a dict of all features for hashing
    features_dict = {
        "signature": {
            "name": signature.name,
            "params": signature.params,
            "defaults": signature.defaults,
            "return_annotation": signature.return_annotation,
        },
        "control_flow": {
            "if_count": control_flow.if_count,
            "elif_count": control_flow.elif_count,
            "else_count": control_flow.else_count,
            "for_count": control_flow.for_count,
            "while_count": control_flow.while_count,
            "early_return_count": control_flow.early_return_count,
        },
        "conditions": {
            "comparison_ops": conditions.comparison_ops,
            "boolean_ops": conditions.boolean_ops,
        },
        "calls": {
            "call_names": calls.call_names,
        },
        "side_effects": {
            "db_calls": side_effects.db_calls,
            "file_calls": side_effects.file_calls,
            "network_calls": side_effects.network_calls,
            "auth_calls": side_effects.auth_calls,
        },
        "exceptions": {
            "raises": exceptions.raises,
            "except_handlers": exceptions.except_handlers,
            "has_bare_except": exceptions.has_bare_except,
        },
        "returns": {
            "return_count": returns.return_count,
            "returns_none": returns.returns_none,
        },
        "is_public": is_public,
    }

    fp_hash = stable_hash(features_dict)

    return FunctionFingerprint(
        stable_id=stable_id,
        file_path=file_path,
        signature=signature,
        control_flow=control_flow,
        conditions=conditions,
        calls=calls,
        side_effects=side_effects,
        exceptions=exceptions,
        returns=returns,
        is_public=is_public,
        fingerprint_hash=fp_hash,
    )
