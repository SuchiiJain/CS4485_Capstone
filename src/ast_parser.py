"""
AST Parser — Core module for parsing Python source into AST
and extracting function/method nodes.

Uses Python's built-in `ast` module. This is the foundation of the
change-detection pipeline: source code → AST tree → function nodes.
"""

import ast
from typing import Dict, List, Optional, Tuple

from src.models import FunctionFingerprint
from src.fingerprint import build_fingerprint


def parse_source(source_code: str) -> Optional[ast.Module]:
    """
    Parse a Python source string into an AST tree.

    Args:
        source_code: Raw Python source code as a string.

    Returns:
        The parsed ast.Module node, or None if parsing fails.
    """
    try:
        return ast.parse(source_code)
    except SyntaxError as e:
        print(f"[docrot] Syntax error while parsing source: {e}")
        return None


def find_function_nodes(tree: ast.Module) -> List[ast.FunctionDef]:
    """
    Walk the AST and collect all FunctionDef and AsyncFunctionDef nodes.

    This includes:
      - Top-level functions
      - Methods inside classes

    Args:
        tree: Parsed AST module.

    Returns:
        List of function/method AST nodes.
    """
    function_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_nodes.append(node)
    return function_nodes


def _annotate_parents(tree: ast.Module) -> Dict[int, ast.AST]:
    """
    Walk the AST once and build a mapping of child node id → parent node.

    This allows efficient parent lookups without re-walking.
    """
    parent_map: Dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent_map[id(child)] = node
    return parent_map


def get_parent_class(tree: ast.Module, fn_node: ast.FunctionDef,
                     parent_map: Optional[Dict[int, ast.AST]] = None) -> Optional[str]:
    """
    Determine the enclosing class name for a method node, if any.

    Args:
        tree: The full AST module (needed to build parent map if not provided).
        fn_node: A FunctionDef node that may be inside a ClassDef.
        parent_map: Pre-built parent map (optional; built on demand).

    Returns:
        The class name string, or None if the function is top-level.
    """
    if parent_map is None:
        parent_map = _annotate_parents(tree)

    parent = parent_map.get(id(fn_node))
    if parent is not None and isinstance(parent, ast.ClassDef):
        return parent.name
    return None


def make_stable_function_id(file_path: str, fn_node: ast.FunctionDef,
                            class_name: Optional[str] = None) -> str:
    """
    Create a stable, unique identifier for a function/method.

    Format:
      - Top-level function: "path/to/file.py::my_function"
      - Class method:       "path/to/file.py::MyClass.my_method"

    Args:
        file_path:  Relative path to the source file.
        fn_node:    The FunctionDef AST node.
        class_name: Enclosing class name, or None.

    Returns:
        A stable ID string.
    """
    # Normalize path separators
    normalized_path = file_path.replace("\\", "/")
    if class_name:
        return f"{normalized_path}::{class_name}.{fn_node.name}"
    return f"{normalized_path}::{fn_node.name}"


def strip_docstring(body: List[ast.stmt]) -> List[ast.stmt]:
    """
    Remove leading docstring node from a function body so that
    docstring-only edits don't affect the fingerprint.

    In Python's AST, a docstring is represented as the first statement
    if it is an `Expr` node containing a `Constant` (str).

    Args:
        body: The list of statements in a function body.

    Returns:
        The body with the leading docstring removed (if present).
    """
    if (body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        return body[1:]
    return body


def is_public_function(fn_node: ast.FunctionDef) -> bool:
    """
    Determine whether a function/method is public (does not start with '_').

    Args:
        fn_node: A FunctionDef AST node.

    Returns:
        True if the function name does NOT start with underscore.
    """
    return not fn_node.name.startswith("_")


def extract_function_fingerprints(source_code: str, file_path: str) -> Dict[str, FunctionFingerprint]:
    """
    High-level entry point: parse source code and return a dict of
    {stable_id: FunctionFingerprint} for every function/method in the file.

    This orchestrates:
      1. parse_source()
      2. find_function_nodes()
      3. For each node → build fingerprint via fingerprint.build_fingerprint()

    Args:
        source_code: Raw Python source.
        file_path:   Relative path to the file (used in stable IDs).

    Returns:
        Dict mapping stable_id → FunctionFingerprint (from models.py).
    """
    if source_code is None:
        return {}

    tree = parse_source(source_code)
    if tree is None:
        return {}

    function_nodes = find_function_nodes(tree)
    parent_map = _annotate_parents(tree)
    result: Dict[str, FunctionFingerprint] = {}

    for fn_node in function_nodes:
        class_name = get_parent_class(tree, fn_node, parent_map)
        stable_id = make_stable_function_id(file_path, fn_node, class_name)
        public = is_public_function(fn_node)
        fingerprint = build_fingerprint(fn_node, file_path, stable_id, public)
        result[stable_id] = fingerprint

    return result
