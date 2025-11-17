# Copilot Instructions for this Repository

This repo implements a symbolic music generator using an event-token Transformer with a Gradio UI and optional ONNX runtime. These notes orient AI coding agents to the project’s architecture, conventions, and day‑to‑day workflows.

## Architecture Overview
- Tokenization:
  - `midi_tokenizer.py` provides two tokenizers: `MIDITokenizerV1` and `MIDITokenizerV2` (preferred). Both define an event schema, parameter vocabularies, `pad/bos/eos`, and `max_token_seq`.
  - V2 adds `time_signature` and `key_signature` events, and uses offsets for parameters (e.g., `sf` stored as `sf+7`). `optimise_midi` toggles preprocessing defaults (remap tracks/channels, add default instruments, drop empty channels).
  - Channel 9 is drums and is treated specially in remapping/augmentation.
- Core model:
  - `midi_model.py` defines `MIDIModelConfig` and `MIDIModel` (two Llama backbones):
    - `net` processes per‑MIDI‑event inputs (merging each token sequence via embedding sum) → hidden state per event.
    - `net_token` autoregresses within the event’s parameter token sequence; `lm_head` predicts next token.
    - Generation uses `DynamicCache` and top‑p/top‑k sampling with strict masks derived from tokenizer event schemas.
- UI / Inference:
  - `app.py` (PyTorch): Gradio Blocks app with live visualizer (`javascript/app.js`) and audio synthesis (`midi_synthesizer.py` via FluidSynth). Writes outputs to `outputs/outputN.mid` and optionally renders audio.
  - `app_onnx.py` (ONNX): Same UI flow using `onnxruntime` split models (`model_base.onnx`, `model_token.onnx`), auto‑downloading defaults if missing.
- Training:
  - `train.py` uses PyTorch Lightning. `MidiDataset` tokenizes MIDI files from `--data`, with optional quality filtering (`tokenizer.check_quality`). Supports full fine‑tune and LoRA via PEFT.

## Common Workflows (bash)
- Run UI (PyTorch):
  ```bash
  python app.py --device cuda --batch 4 --share
  ```
- Run UI (ONNX, CPU/GPU auto):
  ```bash
  python app_onnx.py --batch 8 --share
  ```
- Train a model:
  ```bash
  python train.py --data data --config tv2o-medium \
    --batch-size-train 2 --devices -1 --accelerator gpu --precision bf16-true
  ```
- Export ONNX from checkpoint:
  ```bash
  python export.py --ckpt path/to/model.ckpt --config tv2o-medium \
    --model-base-out models/default/model_base.onnx \
    --model-token-out models/default/model_token.onnx
  ```
- Push to Hugging Face Hub:
  ```bash
  python push_to_hub.py --ckpt path/to/model.safetensors --config auto \
    --repo-id your-username/midi-model --private
  ```
- Docker/Compose:
  ```bash
  docker-compose up midi-model-app
  docker-compose --profile onnx up midi-model-onnx
  docker-compose --profile training up midi-model-trainer
  ```

## Project Conventions & Patterns
- Event masking drives generation: only valid parameters for the current event position are allowed; `disable_patch_change` / `disable_control_change` and channel filtering are supported in UI.
- Sequence limits: context window effectively 4096 events; each event has up to `max_token_seq` tokens (varies by tokenizer). Pad with `pad_id` where needed.
- V2 meta events rules:
  - `time_signature`, `key_signature`, `set_tempo` are normalized and typically assigned to track 0 after remapping.
  - `key_signature.sf` is stored as `sf+7`; utilities convert to/from musical keys. Drum‑only tracks get `sf=0`.
- Track/channel remapping prioritizes non‑empty note tracks; channel 9 remains 9. Default instruments are injected for channels lacking `patch_change` when `add_default_instr` is enabled.
- Data filtering: `MIDITokenizer*.check_quality` enforces alignment, tonality, density, bandwidth, and piano‑dominance thresholds; use `--quality` during training to filter datasets.
- Audio synthesis: `MidiSynthesizer` renders stereo int16 at 44.1kHz using FluidSynth and a GM soundfont (`soundfont.sf2`, downloaded if absent).
- Frontend:
  - `javascript/app.js` defines a custom `<midi-visualizer>` and UI bridges. The constant `MIDI_OUTPUT_BATCH_SIZE` is replaced at runtime by `app.py`/`app_onnx.py`—do not hardcode a different value.
  - Messages from Python to JS use a simple `{name,data}` JSON protocol (`visualizer_clear`, `visualizer_append`, `visualizer_end`, `progress`).

## Key Files & Directories
- UI/Inference: `app.py`, `app_onnx.py`, `javascript/app.js`, `midi_synthesizer.py`
- Model/Tokenization: `midi_model.py`, `midi_tokenizer.py`, `MIDI.py`
- Training/Export: `train.py`, `export.py`, `push_to_hub.py`
- Models: `models/default/{config.json, model_base.onnx, model_token.onnx}`
- Outputs/Logs: `outputs/`, `sample/`, `lightning_logs/`
- Containers: `Dockerfile`, `Dockerfile.onnx`, `docker-compose.yml`, `docker/README.md`

## Integration Notes
- Dependencies: see `requirements.txt` (Torch ≥2.0, Transformers ≥4.36, Lightning 2.4.0, PEFT ≥0.13, Gradio 4.19, FluidSynth). For ONNX path, `onnxruntime`/`onnxruntime-gpu` are used.
- Model loading accepts `.safetensors`, `.bin`, `.ckpt`. LoRA adapters can be merged for inference (`app.py` supports selecting an adapter dir).
- Environment variables commonly used: `GRADIO_SERVER_NAME`, `GRADIO_SERVER_PORT`, `CUDA_VISIBLE_DEVICES`, and HF tokens (`HF_TOKEN`, `HUGGINGFACE_TOKEN`) in Compose.

## Hard Constraints (Do Not Violate)
- Fail-fast TODOs: placeholders/fallbacks/stubs must raise a clear exception with remediation details; never leave silent TODOs.
  - Example (Python): `raise RuntimeError("TODO: implement <function>; reason: <why>; expected inputs: <...>; next step: <cmd/file>")`
- Single-task scope: keep each change focused on one task; avoid drive-by refactors or mixed concerns.
- Minimal changes: implement the smallest viable change consistent with existing patterns and file locations.
- Unsupported ops: if an action can’t proceed (missing model/deps/config), raise an explicit error with next steps.
- Post-task hygiene: after completing a task, lint/format and self-review before handing off.
  - Ruff preferred (if available):
    ```bash
    pip install ruff
    ruff check .
    ruff format .
    ```
  - If Ruff unavailable, use alternatives you have locally (e.g., `flake8 .`, `black .`).

## Tips for Agents
- Prefer V2 tokenizer for new work and align with its event schema and offsets.
- When adding generation features, uphold the mask logic and channel 9 rules.
- Keep UI/js messages compatible with existing `{name,data}` protocol.
- For training VRAM limits, use `--sample-seq` and adjust `--max-len`, batch sizes, and precision.
- Do not modify public APIs or file locations without updating Docker and ONNX paths accordingly.
