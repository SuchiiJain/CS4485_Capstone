"""
Example 3: Comparing Two Versions — See Docrot's Scoring in Action
===================================================================

This example parses two versions of the same function, extracts
fingerprint-like features from each, and shows you exactly what
changed and how Docrot would score it.

Usage:
    python examples/example_compare.py
"""

import ast


# ---------------------------------------------------------------------------
# Two versions of the same function
# ---------------------------------------------------------------------------

code_v1 = '''
def process_order(order_id, user_id):
    """Process an order for a user."""
    order = db.get_order(order_id)
    if order is None:
        raise ValueError("Order not found")

    if order.total > 100:
        apply_discount(order)

    charge_payment(order, user_id)
    return order
'''

code_v2 = '''
def process_order(order_id, user_id, use_new_billing=False):
    """Process an order for a user. Updated for new billing system."""
    order = db.get_order(order_id)
    if order is None:
        raise ValueError("Order not found")

    if order.total >= 100:
        apply_discount(order)
        log_discount(order_id)

    if use_new_billing:
        new_billing_service.charge(order, user_id)
    else:
        charge_payment(order, user_id)

    try:
        send_receipt(order, user_id)
    except EmailError:
        log.warning("Receipt email failed")

    return order
'''


# ---------------------------------------------------------------------------
# Helper to extract features from a function node
# ---------------------------------------------------------------------------

def extract_features(fn_node):
    """Extract a simple feature dict from a function AST node."""
    features = {}

    # Signature
    features["params"] = [a.arg for a in fn_node.args.args]
    features["defaults"] = [ast.dump(d) for d in fn_node.args.defaults]

    # Control flow counts
    features["if_count"] = sum(1 for n in ast.walk(fn_node) if isinstance(n, ast.If))
    features["for_count"] = sum(1 for n in ast.walk(fn_node) if isinstance(n, ast.For))
    features["return_count"] = sum(1 for n in ast.walk(fn_node) if isinstance(n, ast.Return))

    # Comparison operators
    comp_ops = []
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Compare):
            comp_ops.extend(type(op).__name__ for op in n.ops)
    features["comparison_ops"] = sorted(comp_ops)

    # Calls
    calls = []
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Call):
            func = n.func
            if isinstance(func, ast.Name):
                calls.append(func.id)
            elif isinstance(func, ast.Attribute):
                if isinstance(func.value, ast.Name):
                    calls.append(f"{func.value.id}.{func.attr}")
    features["calls"] = sorted(calls)

    # Raises
    raises = []
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Raise) and n.exc:
            if isinstance(n.exc, ast.Call) and isinstance(n.exc.func, ast.Name):
                raises.append(n.exc.func.id)
    features["raises"] = raises

    # Except handlers
    handlers = []
    for n in ast.walk(fn_node):
        if isinstance(n, ast.ExceptHandler) and n.type and isinstance(n.type, ast.Name):
            handlers.append(n.type.id)
    features["except_handlers"] = handlers

    return features


def get_function(code, name):
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------

fn_v1 = get_function(code_v1, "process_order")
fn_v2 = get_function(code_v2, "process_order")

feat_v1 = extract_features(fn_v1)
feat_v2 = extract_features(fn_v2)

print("=" * 65)
print("COMPARING process_order() — v1 vs v2")
print("=" * 65)

print("\n--- Feature-by-Feature Comparison ---\n")

total_score = 0
reasons = []
critical = False

# 1. Signature
print("[Signature]")
print(f"  v1 params:   {feat_v1['params']}")
print(f"  v2 params:   {feat_v2['params']}")
print(f"  v1 defaults: {feat_v1['defaults']}")
print(f"  v2 defaults: {feat_v2['defaults']}")

if feat_v1["params"] != feat_v2["params"] or feat_v1["defaults"] != feat_v2["defaults"]:
    print("  >> CHANGED: public signature changed → +5 pts (CRITICAL)")
    total_score += 5
    reasons.append("public signature changed")
    critical = True
else:
    print("  >> No change.")

# 2. Control flow
print(f"\n[Control Flow]")
print(f"  v1: {feat_v1['if_count']} ifs, {feat_v1['for_count']} fors, {feat_v1['return_count']} returns")
print(f"  v2: {feat_v2['if_count']} ifs, {feat_v2['for_count']} fors, {feat_v2['return_count']} returns")

if feat_v1["if_count"] != feat_v2["if_count"]:
    diff = feat_v2["if_count"] - feat_v1["if_count"]
    print(f"  >> CHANGED: {diff:+d} if-branches → +8 pts (core control path, CRITICAL)")
    total_score += 8
    reasons.append("core control path added/removed")
    critical = True
else:
    print("  >> No change.")

# 3. Conditions
print(f"\n[Conditions]")
print(f"  v1 comparison ops: {feat_v1['comparison_ops']}")
print(f"  v2 comparison ops: {feat_v2['comparison_ops']}")

if feat_v1["comparison_ops"] != feat_v2["comparison_ops"]:
    print("  >> CHANGED: condition expression changed → +3 pts")
    total_score += 3
    reasons.append("branch condition changed")
else:
    print("  >> No change.")

# 4. Calls
print(f"\n[Calls]")
print(f"  v1 calls: {feat_v1['calls']}")
print(f"  v2 calls: {feat_v2['calls']}")

v1_calls = set(feat_v1["calls"])
v2_calls = set(feat_v2["calls"])
new_calls = v2_calls - v1_calls
removed_calls = v1_calls - v2_calls

if new_calls or removed_calls:
    if new_calls:
        print(f"  >> NEW calls:     {new_calls}")
    if removed_calls:
        print(f"  >> REMOVED calls: {removed_calls}")

    # Check for side-effect changes
    SIDE_EFFECT_KEYWORDS = {"db", "billing", "charge", "send", "email", "payment"}
    new_side_effects = [c for c in new_calls if any(k in c.lower() for k in SIDE_EFFECT_KEYWORDS)]
    if new_side_effects:
        print(f"  >> Side-effect calls added: {new_side_effects} → +6 pts (CRITICAL)")
        total_score += 6
        reasons.append("side-effect behavior changed")
        critical = True
else:
    print("  >> No change.")

# 5. Exceptions
print(f"\n[Exceptions]")
print(f"  v1 raises:   {feat_v1['raises']},  handlers: {feat_v1['except_handlers']}")
print(f"  v2 raises:   {feat_v2['raises']},  handlers: {feat_v2['except_handlers']}")

if feat_v1["raises"] != feat_v2["raises"] or feat_v1["except_handlers"] != feat_v2["except_handlers"]:
    print("  >> CHANGED: exception behavior changed → +8 pts (CRITICAL)")
    total_score += 8
    reasons.append("exception behavior changed")
    critical = True
else:
    print("  >> No change.")


# ---------------------------------------------------------------------------
# Final scoring summary
# ---------------------------------------------------------------------------

print(f"\n{'=' * 65}")
print("SCORING SUMMARY")
print(f"{'=' * 65}")
print(f"  Total score:  {total_score}")
print(f"  Critical:     {critical}")
print(f"  Reasons:      {reasons}")
print(f"  Substantial:  {total_score >= 4 or critical}  (threshold = 4)")
print()

if total_score >= 4 or critical:
    print("  VERDICT: Documentation mapped to this code should be reviewed!")
else:
    print("  VERDICT: Changes are minor — no doc review needed.")

print(f"\n{'=' * 65}")
print("Try editing code_v1 / code_v2 above and re-running to see how")
print("different kinds of changes affect the score.")
print(f"{'=' * 65}")
