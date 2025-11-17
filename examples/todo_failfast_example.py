"""
Example demonstrating the repository's fail-fast TODO pattern.
This module is not imported by the application; it's here for reference.
"""

from typing import Any


def TODO_placeholder(*args: Any, **kwargs: Any) -> None:
    """
    Always raise a detailed RuntimeError to prevent silent placeholders.

    Example usage:
        TODO_placeholder(
            reason="Need to implement MIDI augmentation V3",
            expected_inputs={"midi_seq": "List[List[int]]"},
            next_step="See midi_tokenizer.py: MIDITokenizerV2.augment() and repo .github/copilot-instructions.md",
        )
    """
    reason = kwargs.get("reason", "unspecified")
    expected_inputs = kwargs.get("expected_inputs", {})
    next_step = kwargs.get(
        "next_step",
        "Read .github/copilot-instructions.md Hard Constraints and related module docs.",
    )
    raise RuntimeError(
        f"TODO: implement placeholder; "
        f"reason: {reason}; "
        f"expected inputs: {expected_inputs}; "
        f"next step: {next_step}"
    )
