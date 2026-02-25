"""
Example 1: Basic AST Parsing — A Hands-On Introduction
=======================================================

Run this file to see how Python's `ast` module turns source code
into a tree of nodes. This is the foundation of everything Docrot does.

Usage:
    python examples/example_basic_ast.py
"""

import ast


# ---------------------------------------------------------------------------
# 1. Parsing source code into an AST
# ---------------------------------------------------------------------------

sample_code = '''
def greet(name, excited=False):
    """Say hello to someone."""
    if excited:
        return f"HELLO {name}!!!"
    return f"Hello, {name}."
'''

print("=" * 60)
print("1) PARSING SOURCE CODE INTO AN AST")
print("=" * 60)

tree = ast.parse(sample_code)

# ast.dump() gives you the full tree as a string.
# indent=2 makes it human-readable (Python 3.9+).
print("\nFull AST dump:\n")
print(ast.dump(tree, indent=2))


# ---------------------------------------------------------------------------
# 2. Walking the tree to find specific node types
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("2) FINDING FUNCTION DEFINITIONS")
print("=" * 60)

for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        print(f"\n  Found function: {node.name}")
        print(f"  Parameters: {[arg.arg for arg in node.args.args]}")
        print(f"  Has defaults: {len(node.args.defaults)} default value(s)")
        print(f"  Body has {len(node.body)} statement(s)")


# ---------------------------------------------------------------------------
# 3. Inspecting control flow
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("3) INSPECTING CONTROL FLOW INSIDE A FUNCTION")
print("=" * 60)

for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                print(f"\n  Found 'if' statement at line {child.lineno}")
                print(f"  Test expression type: {type(child.test).__name__}")
            elif isinstance(child, ast.Return):
                val_type = type(child.value).__name__ if child.value else "None"
                print(f"  Found 'return' at line {child.lineno}, value type: {val_type}")


# ---------------------------------------------------------------------------
# 4. Seeing what AST ignores (whitespace, comments)
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("4) AST IGNORES WHITESPACE & COMMENTS")
print("=" * 60)

version_a = "def add(a, b):\n    return a + b"
version_b = "def add(a,b):\n    # this adds two numbers\n    return a+b"

tree_a = ast.parse(version_a)
tree_b = ast.parse(version_b)

dump_a = ast.dump(tree_a)
dump_b = ast.dump(tree_b)

print(f"\n  Version A: {version_a!r}")
print(f"  Version B: {version_b!r}")
print(f"\n  AST dumps are identical: {dump_a == dump_b}")
print("  (Comments and whitespace differences are invisible in the AST!)")


# ---------------------------------------------------------------------------
# 5. Seeing what AST DOES catch (operator changes)
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("5) AST CATCHES SEMANTIC CHANGES")
print("=" * 60)

code_gt  = "def check(x):\n    if x > 10:\n        return True"
code_gte = "def check(x):\n    if x >= 10:\n        return True"

tree_gt  = ast.parse(code_gt)
tree_gte = ast.parse(code_gte)

# Find the comparison operator in each version
for label, t in [("x > 10 ", tree_gt), ("x >= 10", tree_gte)]:
    for node in ast.walk(t):
        if isinstance(node, ast.Compare):
            op_name = type(node.ops[0]).__name__
            print(f"  '{label}' → Compare operator: {op_name}")

print("\n  Even though only one character changed (> vs >=),")
print("  the AST sees it as a different operator node (Gt vs GtE).")
print("  This is exactly the kind of change Docrot flags!")


# ---------------------------------------------------------------------------
# 6. Detecting function signature changes
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("6) DETECTING SIGNATURE CHANGES")
print("=" * 60)

sig_v1 = "def fetch(user_id):\n    pass"
sig_v2 = "def fetch(user_id, include_deleted=False):\n    pass"

for label, code in [("v1", sig_v1), ("v2", sig_v2)]:
    t = ast.parse(code)
    for node in ast.walk(t):
        if isinstance(node, ast.FunctionDef):
            params = [a.arg for a in node.args.args]
            defaults = [ast.dump(d) for d in node.args.defaults]
            print(f"  {label}: {node.name}({', '.join(params)})  defaults={defaults}")

print("\n  Docrot scores this as +5 (public signature change) — critical trigger!")


print("\n" + "=" * 60)
print("Done! Play around by editing the sample_code strings above.")
print("=" * 60)
