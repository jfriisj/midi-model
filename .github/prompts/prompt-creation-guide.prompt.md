agent: agent

# Prompt Creation Guide (NN/g‑Aligned)

Create prompts that consistently yield high‑quality, actionable outputs. This guide is informed by Nielsen Norman Group’s guidance on careful prompting and adapted to this repository’s workflows.

## Quick‑Start Checklist
- Goal & audience: Clear objective, scope, and who benefits.
- Context & constraints: Relevant files, environment, versions, policies, limits.
- Output format: Exact structure, sections, length, tone, and any code paths or commands.
- Examples & edge cases: Provide a few small I/O examples and tricky cases.
- Process: Ask for a concise plan, tool preambles, and verification steps.
- Guardrails: Require factuality checks, cite sources when applicable, and refuse harmful content.

## Five Core Principles (NN/g)
1) Be specific about the goal: Define success criteria and non‑goals to avoid scope creep.
2) Supply context and constraints: Name files, APIs, versions, environment, policies, and time/budget limits.
3) Specify the output: Structure, formatting, sections, code style, error handling, and test expectations.
4) Show examples: Include a couple of representative inputs and desired outputs, plus edge cases.
5) Iterate and verify: Ask for a brief plan first, then updates; include checks, tests, and self‑review.

## Prompt Template
Copy, then replace placeholders. Keep sections concise and concrete.

```
---
agent: agent
---

Context
- Project: <brief project/app description relevant to the task>
- Files of interest: <file paths> (only these unless needed)
- Environment: OS=<...>, shell=<...>, Python/Node versions=<...>
- Constraints: <time/complexity limits, policies, dependencies, model limits>

Task
- Goal: <single, clear objective>
- Requirements: <bulleted, testable requirements>
- Non‑goals: <explicitly exclude to prevent scope creep>
- Success criteria: <measurable acceptance tests or outcomes>

Output
- Format: <sections, headings, bullets, code blocks, file paths>
- Style: <tone, brevity, citation rules, terminology>
- Deliverables: <code patches, commands, README updates, tests>

Process
- Start with a 2–4 bullet plan using the TODO tool; track progress.
- Before tool calls, add a 1‑sentence preamble describing the action.
- For code edits, use `apply_patch`; minimal, single‑task changes only.
- If tests exist, run targeted tests; otherwise include light validation.

Verification
- Acceptance checks: <what to run/read to confirm>
- Self‑review: <lint/format expectations, e.g., ruff check/format>
- Ambiguity: Ask clarifying questions only where essential; otherwise proceed with safe defaults.

References (if any)
- Sources: <links to internal docs/specs/PRDs or public references>
```

## Repository‑Specific Add‑Ons (Use When Working Here)
- Hard constraints:
	- Fail‑fast TODOs in code; no silent placeholders.
	- Single‑task scope; avoid drive‑by refactors.
	- Minimal changes; keep style and public APIs intact.
	- If blocked (missing model/deps/config), raise explicit error with next steps.
	- Post‑task hygiene: prefer `ruff check .` and `ruff format .` when available.
- Tokenization & model:
	- Prefer `MIDITokenizerV2`; uphold event masks and channel‑9 rules.
	- Context window ~4096 events; respect `max_token_seq` and `pad/bos/eos`.
- UI/JS:
	- Keep `{name,data}` message protocol; don’t hardcode `MIDI_OUTPUT_BATCH_SIZE`.
- Audio:
	- `MidiSynthesizer` uses FluidSynth and `soundfont.sf2` (auto‑download if absent).

## Examples

Example 1 — Bug fix (vague → better → best)
- Vague: “Fix the mask bug in generation.”
- Better: “In `midi_tokenizer.py`, notes on channel 9 get invalid masks during generation; ensure drum channel masks never include pitched instruments.”
- Best prompt:
	- Context: `midi_tokenizer.py` V2 masks, channel 9 is drums.
	- Task: Fix mask so channel 9 prohibits pitched instrument parameters during generation; add a minimal test.
	- Output: One `apply_patch` to the tokenizer; a small test snippet and instructions to run it; brief explanation of the mask change.
	- Verification: Generation on a short drum‑only sequence yields no pitched parameters; lints pass.

Example 2 — UI feature
- Best prompt skeleton: “Add a toggle in `app.py` to disable `control_change` events during generation; plumb it through to mask logic without altering defaults. Output: `apply_patch` for `app.py` and any touched file, plus an example launch command.”

Example 3 — Docs update
- Best prompt skeleton: “Update `README.md` with ONNX export steps using `export.py`, including Windows bash commands and common errors with next steps. Keep changes scoped to a new ‘Export ONNX’ section.”

## Anti‑Patterns to Avoid
- Vague goals: Missing acceptance criteria, scope, or affected files.
- Mixed concerns: Multiple unrelated tasks in a single prompt.
- Unspecified output: No structure/format or missing file paths.
- Ignoring constraints: No mention of repo policies, environment, or tests.

## Reference
- Nielsen Norman Group: Careful Prompting for Better Outputs — https://www.nngroup.com/articles/careful-prompts/
