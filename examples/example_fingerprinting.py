"""
Example 2: Fingerprinting — How Docrot Extracts Semantic Features
==================================================================

This example shows how to walk a function's AST and pull out the
features that form a "semantic fingerprint." You'll see the exact
node types that map to each scoring category.

Usage:
    python examples/example_fingerprinting.py
"""

import ast
from typing import List


# ---------------------------------------------------------------------------
# Sample function to fingerprint
# ---------------------------------------------------------------------------

sample_code = '''
import requests

def create_user(username, email, is_admin=False):
    """Create a new user in the database."""
    if not username or not email:
        raise ValueError("username and email are required")

    if is_admin:
        if not check_permission("admin_create"):
            raise PermissionError("Not authorized")

    user = db.insert("users", {"name": username, "email": email, "admin": is_admin})

    try:
        send_welcome_email(email)
    except EmailError as e:
        log.warning(f"Welcome email failed: {e}")

    return user
'''


# ---------------------------------------------------------------------------
# Helper: resolve a Call node to a readable name string
# ---------------------------------------------------------------------------

def get_call_name(node: ast.Call) -> str:
    """Turn a Call node into a human-readable name like 'db.insert'."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id                                    # e.g. send_welcome_email
    elif isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"         # e.g. db.insert
        return f"?.{func.attr}"
    return "<unknown>"


# ---------------------------------------------------------------------------
# Parse + find the function
# ---------------------------------------------------------------------------

tree = ast.parse(sample_code)
fn_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "create_user":
        fn_node = node
        break

assert fn_node is not None, "Function not found"


# ---------------------------------------------------------------------------
# 1. Signature features
# ---------------------------------------------------------------------------

print("=" * 60)
print("FINGERPRINT: create_user()")
print("=" * 60)

params = [a.arg for a in fn_node.args.args]
defaults = [ast.dump(d) for d in fn_node.args.defaults]
ret_annotation = ast.dump(fn_node.returns) if fn_node.returns else None

print(f"\n[Signature]")
print(f"  Name:       {fn_node.name}")
print(f"  Params:     {params}")
print(f"  Defaults:   {defaults}")
print(f"  Return ann: {ret_annotation}")
print(f"  Is public:  {not fn_node.name.startswith('_')}")


# ---------------------------------------------------------------------------
# 2. Control-flow features
# ---------------------------------------------------------------------------

if_count = 0
for_count = 0
while_count = 0
return_count = 0

for child in ast.walk(fn_node):
    if isinstance(child, ast.If):
        if_count += 1
    elif isinstance(child, ast.For):
        for_count += 1
    elif isinstance(child, ast.While):
        while_count += 1
    elif isinstance(child, ast.Return):
        return_count += 1

print(f"\n[Control Flow]")
print(f"  if statements:  {if_count}")
print(f"  for loops:      {for_count}")
print(f"  while loops:    {while_count}")
print(f"  return stmts:   {return_count}")


# ---------------------------------------------------------------------------
# 3. Condition features (comparison + boolean operators)
# ---------------------------------------------------------------------------

comparison_ops = []
boolean_ops = []

for child in ast.walk(fn_node):
    if isinstance(child, ast.Compare):
        for op in child.ops:
            comparison_ops.append(type(op).__name__)
    elif isinstance(child, ast.BoolOp):
        boolean_ops.append(type(child.op).__name__)

print(f"\n[Conditions]")
print(f"  Comparison ops: {comparison_ops}")
print(f"  Boolean ops:    {boolean_ops}")


# ---------------------------------------------------------------------------
# 4. Call features
# ---------------------------------------------------------------------------

call_names = []
for child in ast.walk(fn_node):
    if isinstance(child, ast.Call):
        call_names.append(get_call_name(child))

print(f"\n[Calls]")
print(f"  All calls: {call_names}")


# ---------------------------------------------------------------------------
# 5. Side-effect classification (simple keyword approach)
# ---------------------------------------------------------------------------

DB_KEYWORDS = {"db", "cursor", "session", "query", "insert", "execute", "commit"}
FILE_KEYWORDS = {"open", "write", "read_file", "save"}
NETWORK_KEYWORDS = {"requests", "http", "fetch", "send_email", "send_welcome_email"}
AUTH_KEYWORDS = {"check_permission", "auth", "login", "verify_token"}

db_calls = [c for c in call_names if any(k in c.lower() for k in DB_KEYWORDS)]
file_calls = [c for c in call_names if any(k in c.lower() for k in FILE_KEYWORDS)]
net_calls = [c for c in call_names if any(k in c.lower() for k in NETWORK_KEYWORDS)]
auth_calls = [c for c in call_names if any(k in c.lower() for k in AUTH_KEYWORDS)]

print(f"\n[Side Effects]")
print(f"  DB calls:      {db_calls}")
print(f"  File calls:    {file_calls}")
print(f"  Network calls: {net_calls}")
print(f"  Auth calls:    {auth_calls}")


# ---------------------------------------------------------------------------
# 6. Exception features
# ---------------------------------------------------------------------------

raises = []
except_handlers = []
has_bare_except = False

for child in ast.walk(fn_node):
    if isinstance(child, ast.Raise) and child.exc:
        if isinstance(child.exc, ast.Call) and isinstance(child.exc.func, ast.Name):
            raises.append(child.exc.func.id)
        elif isinstance(child.exc, ast.Name):
            raises.append(child.exc.id)
    elif isinstance(child, ast.ExceptHandler):
        if child.type is None:
            has_bare_except = True
        elif isinstance(child.type, ast.Name):
            except_handlers.append(child.type.id)

print(f"\n[Exceptions]")
print(f"  Raises:          {raises}")
print(f"  Except handlers: {except_handlers}")
print(f"  Bare except:     {has_bare_except}")


# ---------------------------------------------------------------------------
# 7. Return features
# ---------------------------------------------------------------------------

return_nodes = [n for n in ast.walk(fn_node) if isinstance(n, ast.Return)]
returns_none = any(r.value is None for r in return_nodes)

print(f"\n[Returns]")
print(f"  Return count:  {len(return_nodes)}")
print(f"  Returns None:  {returns_none}")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print(f"\n{'=' * 60}")
print("This is the full fingerprint Docrot would store for create_user().")
print("If ANY of these features change between commits, Docrot computes")
print("a weighted score to decide if documentation needs review.")
print(f"{'=' * 60}")
