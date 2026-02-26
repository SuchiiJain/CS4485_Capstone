from dataclasses import dataclass
from enum import Enum
from typing import Optional


# --- Enums ---

# Severity levels for flagged issues
class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Reasons why a documentation flag was raised
class FlagReason(Enum):
    SIGNATURE_CHANGED = "signature_changed"
    PARAMETER_ADDED = "parameter_added"
    PARAMETER_REMOVED = "parameter_removed"
    PARAMETER_RENAMED = "parameter_renamed"
    RETURN_TYPE_CHANGED = "return_type_changed"
    SYMBOL_REMOVED = "symbol_removed"
    DOCSTRING_MISSING = "docstring_missing"
    DOCSTRING_STALE = "docstring_stale"
    MARKDOWN_REF_BROKEN = "markdown_ref_broken"


# --- Dataclasses ---

# Represents a code element (function/class) extracted from the codebase
@dataclass
class CodeElement:
    name: str               # Name of the function or class
    file_path: str          # Path to the file containing this element
    signature: str          # Full function signature string
    hash: str               # Hash of the element used to detect changes
    params: list[str]       # List of parameter names
    return_type: Optional[str]   # Return type if available
    docstring: Optional[str]     # Docstring if present


# Represents a reference to a code symbol found in documentation
@dataclass
class DocReference:
    file_path: str              # Path to the documentation file
    referenced_symbol: str      # The symbol name referenced in the doc
    last_verified_hash: str     # Hash of the code element when doc was last verified
    snippet: Optional[str]      # Short text snippet from the doc referencing the symbol


# Represents a single documentation flag raised by the detector
@dataclass
class Flag:
    reason: FlagReason              # Why the flag was raised
    severity: Severity              # How severe the issue is
    code_element: CodeElement       # The code element involved
    doc_reference: Optional[DocReference]  # The related doc reference if applicable
    message: str                    # Human-readable description of the issue
    suggestion: Optional[str] = None  # Optional suggestion for how to fix it


# --- Constants ---

# Number of parameter changes required to escalate severity to HIGH
PARAM_CHANGE_HIGH_THRESHOLD = 3

# Default severity level for each flag reason
SEVERITY_MAP: dict[FlagReason, Severity] = {
    FlagReason.SIGNATURE_CHANGED: Severity.HIGH,
    FlagReason.PARAMETER_ADDED: Severity.MEDIUM,
    FlagReason.PARAMETER_REMOVED: Severity.MEDIUM,
    FlagReason.PARAMETER_RENAMED: Severity.LOW,
    FlagReason.RETURN_TYPE_CHANGED: Severity.MEDIUM,
    FlagReason.SYMBOL_REMOVED: Severity.HIGH,
    FlagReason.DOCSTRING_MISSING: Severity.LOW,
    FlagReason.DOCSTRING_STALE: Severity.MEDIUM,
    FlagReason.MARKDOWN_REF_BROKEN: Severity.HIGH,
}


# --- Helper ---

# Builds a standardized human-readable message for a flag
def _make_message(
    reason: FlagReason,
    element: CodeElement,
    doc: Optional[DocReference],
    extra: str = "",
) -> str:
    doc_info = f" (referenced in '{doc.file_path}')" if doc else ""
    base = f"[{reason.value}] '{element.name}' in '{element.file_path}'{doc_info}"
    return f"{base}. {extra}".strip()


# --- Check Functions ---

# Checks if a code element's signature hash changed between old and new versions
def check_signature_change(
    old: CodeElement, new: CodeElement, doc: Optional[DocReference]
) -> Optional[Flag]:
    if old.hash != new.hash:
        extra = f"Signature changed from '{old.signature}' to '{new.signature}'."
        return Flag(
            reason=FlagReason.SIGNATURE_CHANGED,
            severity=SEVERITY_MAP[FlagReason.SIGNATURE_CHANGED],
            code_element=new,
            doc_reference=doc,
            message=_make_message(FlagReason.SIGNATURE_CHANGED, new, doc, extra),
            suggestion=f"Update documentation for '{new.name}' to reflect the new signature.",
        )
    return None


# Checks if parameters were added or removed between old and new versions
# Escalates severity to HIGH if 3 or more parameters changed at once
def check_parameter_changes(
    old: CodeElement, new: CodeElement, doc: Optional[DocReference]
) -> list[Flag]:
    flags: list[Flag] = []
    old_params = set(old.params)
    new_params = set(new.params)
    added = new_params - old_params
    removed = old_params - new_params

    # Escalate to HIGH if total param changes meet or exceed threshold
    escalate = (len(added) + len(removed)) >= PARAM_CHANGE_HIGH_THRESHOLD

    for p in added:
        reason = FlagReason.PARAMETER_ADDED
        sev = Severity.HIGH if escalate else SEVERITY_MAP[reason]
        flags.append(
            Flag(
                reason=reason,
                severity=sev,
                code_element=new,
                doc_reference=doc,
                message=_make_message(
                    reason, new, doc, f"New parameter '{p}' not documented."
                ),
                suggestion=f"Add documentation for the new parameter '{p}'.",
            )
        )

    for p in removed:
        reason = FlagReason.PARAMETER_REMOVED
        sev = Severity.HIGH if escalate else SEVERITY_MAP[reason]
        flags.append(
            Flag(
                reason=reason,
                severity=sev,
                code_element=new,
                doc_reference=doc,
                message=_make_message(
                    reason,
                    new,
                    doc,
                    f"Parameter '{p}' removed but may still be referenced in docs.",
                ),
                suggestion=f"Remove references to parameter '{p}' from documentation.",
            )
        )

    return flags


# Checks if the return type changed between old and new versions
def check_return_type_change(
    old: CodeElement, new: CodeElement, doc: Optional[DocReference]
) -> Optional[Flag]:
    if old.return_type != new.return_type:
        extra = f"Return type changed from '{old.return_type}' to '{new.return_type}'."
        return Flag(
            reason=FlagReason.RETURN_TYPE_CHANGED,
            severity=SEVERITY_MAP[FlagReason.RETURN_TYPE_CHANGED],
            code_element=new,
            doc_reference=doc,
            message=_make_message(FlagReason.RETURN_TYPE_CHANGED, new, doc, extra),
            suggestion="Update the return type description in documentation.",
        )
    return None


# Flags a code element that no longer exists in the codebase
def check_symbol_removed(
    element: CodeElement, doc: Optional[DocReference]
) -> Flag:
    return Flag(
        reason=FlagReason.SYMBOL_REMOVED,
        severity=SEVERITY_MAP[FlagReason.SYMBOL_REMOVED],
        code_element=element,
        doc_reference=doc,
        message=_make_message(
            FlagReason.SYMBOL_REMOVED,
            element,
            doc,
            "This symbol no longer exists in the codebase.",
        ),
        suggestion=f"Remove or update documentation references to '{element.name}'.",
    )


# Flags a public function that is missing a docstring
def check_docstring_missing(element: CodeElement) -> Optional[Flag]:
    # Only flags public functions (ignores private ones starting with _)
    if not element.name.startswith("_") and not element.docstring:
        return Flag(
            reason=FlagReason.DOCSTRING_MISSING,
            severity=SEVERITY_MAP[FlagReason.DOCSTRING_MISSING],
            code_element=element,
            doc_reference=None,
            message=_make_message(
                FlagReason.DOCSTRING_MISSING,
                element,
                None,
                "Public function has no docstring.",
            ),
            suggestion=f"Add a docstring to '{element.name}'.",
        )
    return None


# Checks if the code element changed since the documentation was last verified
def check_stale_doc(element: CodeElement, doc: DocReference) -> Optional[Flag]:
    if element.hash != doc.last_verified_hash:
        return Flag(
            reason=FlagReason.DOCSTRING_STALE,
            severity=SEVERITY_MAP[FlagReason.DOCSTRING_STALE],
            code_element=element,
            doc_reference=doc,
            message=_make_message(
                FlagReason.DOCSTRING_STALE,
                element,
                doc,
                "Code was updated but documentation hash was not refreshed.",
            ),
            suggestion="Review and verify that the documentation still matches the updated code.",
        )
    return None


# Checks if a symbol referenced in markdown docs no longer exists in the codebase
def check_broken_markdown_ref(
    symbol_name: str, all_current_symbols: set[str], doc: DocReference
) -> Optional[Flag]:
    if symbol_name not in all_current_symbols:
        # Create a placeholder element to represent the deleted symbol
        ghost_element = CodeElement(
            name=symbol_name,
            file_path="<deleted>",
            signature="",
            hash="",
            params=[],
            return_type=None,
            docstring=None,
        )
        return Flag(
            reason=FlagReason.MARKDOWN_REF_BROKEN,
            severity=SEVERITY_MAP[FlagReason.MARKDOWN_REF_BROKEN],
            code_element=ghost_element,
            doc_reference=doc,
            message=_make_message(
                FlagReason.MARKDOWN_REF_BROKEN,
                ghost_element,
                doc,
                f"Symbol '{symbol_name}' referenced in docs no longer exists in codebase.",
            ),
            suggestion=f"Remove or replace the reference to '{symbol_name}' in '{doc.file_path}'.",
        )
    return None


# --- Main Flagging Pipeline ---

# Runs all checks across old and new code elements and returns a sorted list of flags
def run_flagging(
    old_elements: dict[str, CodeElement],
    new_elements: dict[str, CodeElement],
    doc_references: list[DocReference],
) -> list[Flag]:
    flags: list[Flag] = []
    current_symbols = set(new_elements.keys())

    # Build a lookup table from symbol name to its doc reference
    doc_lookup: dict[str, DocReference] = {
        ref.referenced_symbol: ref for ref in doc_references
    }

    # Check all elements that existed before for changes or removal
    for name, old_elem in old_elements.items():
        doc = doc_lookup.get(name)

        if name not in new_elements:
            # Symbol was removed entirely
            flags.append(check_symbol_removed(old_elem, doc))
            continue

        new_elem = new_elements[name]

        # Check for signature, parameter, and return type changes
        sig_flag = check_signature_change(old_elem, new_elem, doc)
        if sig_flag:
            flags.append(sig_flag)

        flags.extend(check_parameter_changes(old_elem, new_elem, doc))

        ret_flag = check_return_type_change(old_elem, new_elem, doc)
        if ret_flag:
            flags.append(ret_flag)

        # Check if linked doc is stale
        if doc:
            stale_flag = check_stale_doc(new_elem, doc)
            if stale_flag:
                flags.append(stale_flag)

    # Check newly added elements for missing docstrings
    for name, new_elem in new_elements.items():
        if name not in old_elements:
            missing_flag = check_docstring_missing(new_elem)
            if missing_flag:
                flags.append(missing_flag)

    # Check all doc references for broken markdown links
    for doc in doc_references:
        broken_flag = check_broken_markdown_ref(
            doc.referenced_symbol, current_symbols, doc
        )
        if broken_flag:
            flags.append(broken_flag)

    # Sort flags by severity: HIGH first, then MEDIUM, then LOW
    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    flags.sort(key=lambda f: order[f.severity])
    return flags 