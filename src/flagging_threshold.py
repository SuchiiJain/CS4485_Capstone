from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


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


@dataclass
class CodeElement:
    name: str
    file_path: str
    signature: str
    hash: str
    params: list[str]
    return_type: Optional[str]
    docstring: Optional[str]


@dataclass
class DocReference:
    file_path: str
    referenced_symbol: str
    last_verified_hash: str
    snippet: Optional[str]


@dataclass
class Flag:
    reason: FlagReason
    severity: Severity
    code_element: CodeElement
    doc_reference: Optional[DocReference]
    message: str
    suggestion: Optional[str] = None


PARAM_CHANGE_HIGH_THRESHOLD = 3

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


def _make_message(
    reason: FlagReason,
    element: CodeElement,
    doc: Optional[DocReference],
    extra: str = "",
) -> str:
    doc_info = f" (referenced in '{doc.file_path}')" if doc else ""
    base = f"[{reason.value}] '{element.name}' in '{element.file_path}'{doc_info}"
    return f"{base}. {extra}".strip()


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


def check_parameter_changes(
    old: CodeElement, new: CodeElement, doc: Optional[DocReference]
) -> list[Flag]:
    flags: list[Flag] = []
    old_params = set(old.params)
    new_params = set(new.params)
    added = new_params - old_params
    removed = old_params - new_params
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


def check_docstring_missing(element: CodeElement) -> Optional[Flag]:
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


def check_broken_markdown_ref(
    symbol_name: str, all_current_symbols: set[str], doc: DocReference
) -> Optional[Flag]:
    if symbol_name not in all_current_symbols:
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


def run_flagging(
    old_elements: dict[str, CodeElement],
    new_elements: dict[str, CodeElement],
    doc_references: list[DocReference],
) -> list[Flag]:
    flags: list[Flag] = []
    current_symbols = set(new_elements.keys())
    doc_lookup: dict[str, DocReference] = {
        ref.referenced_symbol: ref for ref in doc_references
    }

    for name, old_elem in old_elements.items():
        doc = doc_lookup.get(name)
        if name not in new_elements:
            flags.append(check_symbol_removed(old_elem, doc))
            continue

        new_elem = new_elements[name]

        sig_flag = check_signature_change(old_elem, new_elem, doc)
        if sig_flag:
            flags.append(sig_flag)

        flags.extend(check_parameter_changes(old_elem, new_elem, doc))

        ret_flag = check_return_type_change(old_elem, new_elem, doc)
        if ret_flag:
            flags.append(ret_flag)

        if doc:
            stale_flag = check_stale_doc(new_elem, doc)
            if stale_flag:
                flags.append(stale_flag)

    for name, new_elem in new_elements.items():
        if name not in old_elements:
            missing_flag = check_docstring_missing(new_elem)
            if missing_flag:
                flags.append(missing_flag)

    for doc in doc_references:
        broken_flag = check_broken_markdown_ref(
            doc.referenced_symbol, current_symbols, doc
        )
        if broken_flag:
            flags.append(broken_flag)

    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    flags.sort(key=lambda f: order[f.severity])
    return flags
    