"""
AI Suggestions — Optional LLM-powered documentation fix suggestions.

When enabled via .docrot-config.json, this module takes the flagged
documentation files and change events produced by the core pipeline
and asks an LLM to generate *specific* edits the user should make
to bring each doc file back in sync with the code.

AI features are strictly opt-in:
  - The user must add an "ai" block to .docrot-config.json.
  - The referenced API-key environment variable must be set.
  - If either condition is unmet, all public functions here are no-ops.

No autonomous changes are ever made — only human-readable suggestions.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.models import AISuggestion, ChangeEvent, DocAlert


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a documentation maintenance assistant. Given a list of code "
    "changes and the current content of a documentation file, you produce "
    "specific, actionable edits that should be made to the documentation "
    "so that it accurately reflects the code.\n\n"
    "Rules:\n"
    "- Only suggest changes that are necessary based on the code changes.\n"
    "- Be specific: quote the existing sentence/section, then write the "
    "corrected version.\n"
    "- If no changes are needed, say so.\n"
    "- Keep your response concise.\n"
)

# Maximum characters of documentation content to send to the LLM.
# Keeps token usage predictable; configurable per-repo in a future iteration.
MAX_DOC_CHARS = 12_000


def _build_user_prompt(
    doc_path: str,
    doc_content: str,
    change_descriptions: List[str],
) -> str:
    """Build the user-turn prompt for a single flagged doc file."""
    truncated = doc_content[:MAX_DOC_CHARS]
    if len(doc_content) > MAX_DOC_CHARS:
        truncated += "\n... (truncated)"

    changes_block = "\n".join(f"- {desc}" for desc in change_descriptions)

    return (
        f"## Documentation file: {doc_path}\n\n"
        f"### Code changes that affect this file:\n{changes_block}\n\n"
        f"### Current documentation content:\n```\n{truncated}\n```\n\n"
        "List the specific sections or sentences that need to be updated, "
        "and for each one provide the corrected text."
    )


# ---------------------------------------------------------------------------
# Provider abstraction
# ---------------------------------------------------------------------------

class LLMClient(ABC):
    """Minimal interface for calling an LLM with a system + user prompt."""

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return the assistant's text response."""


class AnthropicClient(LLMClient):
    """Anthropic Messages API client (requires `anthropic` package)."""

    def __init__(self, api_key: str, model: str):
        try:
            import anthropic  # noqa: F811
        except ImportError:
            raise ImportError(
                "The 'anthropic' package is required for Anthropic AI suggestions. "
                "Install it with: pip install anthropic"
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text


class OpenAIClient(LLMClient):
    """OpenAI Chat Completions client (requires `openai` package)."""

    def __init__(self, api_key: str, model: str):
        try:
            import openai  # noqa: F811
        except ImportError:
            raise ImportError(
                "The 'openai' package is required for OpenAI AI suggestions. "
                "Install it with: pip install openai"
            )
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


class GroqClient(LLMClient):
    """Groq inference client (requires `groq` package).

    Groq hosts open-source models (Llama 3, Mixtral, etc.) on custom LPU
    hardware.  The API mirrors the OpenAI chat-completions format.
    """

    def __init__(self, api_key: str, model: str):
        try:
            import groq  # noqa: F811
        except ImportError:
            raise ImportError(
                "The 'groq' package is required for Groq AI suggestions. "
                "Install it with: pip install groq"
            )
        self._client = groq.Groq(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


def _create_client(ai_config: Dict[str, str]) -> LLMClient:
    """Instantiate the correct LLMClient based on the provider name."""
    provider = ai_config["provider"]
    if provider == "anthropic":
        return AnthropicClient(api_key=ai_config["api_key"], model=ai_config["model"])
    elif provider == "openai":
        return OpenAIClient(api_key=ai_config["api_key"], model=ai_config["model"])
    elif provider == "groq":
        return GroqClient(api_key=ai_config["api_key"], model=ai_config["model"])
    else:
        raise ValueError(f"Unsupported AI provider: {provider}")


# ---------------------------------------------------------------------------
# Change description helpers
# ---------------------------------------------------------------------------

def _describe_change_event(event: ChangeEvent) -> str:
    """Turn a ChangeEvent into a human-readable one-liner for the prompt."""
    reasons = ", ".join(event.reasons) if event.reasons else "changed"
    critical_tag = " [CRITICAL]" if event.critical else ""
    return (
        f"{event.function_id} ({event.code_path}): "
        f"{reasons} (score {event.score}){critical_tag}"
    )


def _describe_doc_alert(alert: DocAlert) -> str:
    """Turn a DocAlert into a human-readable one-liner for the prompt."""
    funcs = ", ".join(alert.functions) if alert.functions else "multiple functions"
    return (
        f"Flagged due to changes in {funcs} — "
        f"{', '.join(alert.reasons)} (cumulative score {alert.cumulative_score})"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_ai_suggestions(
    ai_config: Optional[Dict[str, str]],
    doc_alerts: List[DocAlert],
    all_events: List[ChangeEvent],
    repo_path: str,
) -> List[AISuggestion]:
    """
    Generate LLM-powered suggestions for each flagged documentation file.

    Args:
        ai_config:  Validated AI config dict from get_ai_config(), or None.
        doc_alerts: List of DocAlert objects from the pipeline.
        all_events: All ChangeEvent objects from the current scan.
        repo_path:  Absolute path to the repository root.

    Returns:
        List of AISuggestion objects. Empty list if AI is disabled or
        if no doc_alerts exist.
    """
    if ai_config is None or not doc_alerts:
        return []

    try:
        client = _create_client(ai_config)
    except (ImportError, ValueError) as e:
        print(f"[docrot] AI suggestions disabled: {e}")
        return []

    model_name = ai_config["model"]
    suggestions: List[AISuggestion] = []

    for alert in doc_alerts:
        # Read the actual documentation file content
        doc_abs_path = os.path.join(repo_path, alert.doc_path)
        try:
            with open(doc_abs_path, "r", encoding="utf-8") as f:
                doc_content = f.read()
        except OSError:
            doc_content = "(could not read documentation file)"

        # Collect change descriptions relevant to this doc
        change_descriptions: List[str] = [_describe_doc_alert(alert)]
        for event in all_events:
            if event.function_id in alert.functions:
                change_descriptions.append(_describe_change_event(event))

        # Build prompt and call LLM
        user_prompt = _build_user_prompt(
            alert.doc_path, doc_content, change_descriptions,
        )

        try:
            suggestion_text = client.complete(_SYSTEM_PROMPT, user_prompt)
        except Exception as e:
            print(f"[docrot] AI suggestion failed for '{alert.doc_path}': {e}")
            suggestion_text = f"(AI suggestion unavailable: {e})"

        suggestions.append(AISuggestion(
            doc_path=alert.doc_path,
            triggered_by=list(alert.functions),
            suggestion_text=suggestion_text,
            model_used=model_name,
        ))

    return suggestions
