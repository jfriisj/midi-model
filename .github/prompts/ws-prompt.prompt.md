---
agent: agent
---

Context
- Project: Symbolic music generator with Gradio UI (PyTorch and ONNX paths), tokenizers, and FluidSynth-based audio rendering.
- Files of interest: app.py, app_onnx.py, midi_model.py, midi_tokenizer.py, outputs.
- Environment: OS=Windows, shell=bash.exe, Python with Torch ≥2.0; ONNX optional. Gradio used for UI.
- Constraints: Minimal, single-task change. Keep UI intact. Prefer reuse of app.py/app_onnx.py capabilities. Fail fast if models/deps missing. Keep protocol simple: request a MIDI → return base64 MIDI.
- Policies: Follow repo “Hard Constraints” in copilot-instructions.md and prompt guide.

Task
- Goal: Add a simple WebSocket server that accepts a generation request and returns a generated MIDI as base64, using Torch or ONNX engines the project already supports.
- Requirements:
  - Create `ws_server.py` exposing a WebSocket endpoint at `ws://0.0.0.0:8765`.
  - Message protocol:
    - Request JSON: `{"action":"generate-midi","engine":"torch"|"onnx","params":{...}}`; `engine` optional, default `"onnx"` if ONNX models present, else `"torch"`.
    - Response JSON on success: `{"status":"ok","filename":"outputN.mid","midi_b64":"<base64>"}`; on error: `{"status":"error","error":"<message>"}`.
  - Reuse existing generation path:
    - Prefer calling/refactoring a minimal, shared “generate_one” function extracted non-invasively from app.py/app_onnx.py; if no clean hook exists, add a tiny wrapper that loads the same model/tokenizer config paths and calls the same generation logic as the UIs.
  - Output a `.mid` in outputs and the base64 of its contents.
  - Add dependency with minimal surface area (e.g., `websockets>=12`), update requirements.txt accordingly.
  - Log concise server start and per-request summaries; no verbose prints.
  - Fail fast with explicit remediation if models are missing or incompatible.
- Non-goals:
  - No changes to Gradio UI or JS protocol.
  - No authentication, scaling, or streaming; one-shot request/response only.
  - No complex routing; single action `"generate-midi"`.
- Success criteria:
  - Running the server and sending a sample request returns a valid base64-encoded MIDI that decodes to a playable `.mid` and is saved under outputs.

Output
- Format: 
  - One `apply_patch` adding `ws_server.py`.
  - One `apply_patch` updating requirements.txt to include `websockets>=12`.
  - Optional tiny refactor patch to expose a minimal “generate_one” function if cleanly achievable without breaking UIs.
- Style: Concise code, minimal changes, keep repo style. Clear error messages.
- Deliverables:
  - `ws_server.py` with server code and inline docstring for protocol.
  - requirements.txt update.
  - Example client snippet and run commands in the response.
  - Brief explanation of how generation is reused.

Process
- Start with a 3–4 bullet TODO plan using the TODO tool; track progress.
- Before each tool call, add a 1-sentence preamble describing the action.
- Use `apply_patch` for file edits; avoid unrelated refactors.
- If extraction from app.py/app_onnx.py is not feasible without churn, implement a small wrapper that loads the same config/model files (`models/default/*`) and calls their generation routines as-is.
- Prefer ONNX engine by default when model_base.onnx and `model_token.onnx` are present; otherwise use Torch path.

Verification
- Acceptance checks:
  - Install deps and run server:
    ```bash
    pip install -r requirements.txt
    python ws_server.py --host 0.0.0.0 --port 8765
    ```
  - Run a quick client test (from another shell):
    ```bash
    python - << 'PY'
    import asyncio, json, base64, websockets
    async def main():
        async with websockets.connect("ws://127.0.0.1:8765") as ws:
            req = {"action":"generate-midi","engine":"onnx","params":{"seed":42}}
            await ws.send(json.dumps(req))
            resp = json.loads(await ws.recv())
            assert resp.get("status") == "ok", resp
            data = base64.b64decode(resp["midi_b64"])
            with open("outputs/test_ws.mid","wb") as f: f.write(data)
            print("Wrote outputs/test_ws.mid (bytes:", len(data), ")")
    asyncio.run(main())
    PY
    ```
  - Confirm `outputs/test_ws.mid` exists and is a valid MIDI file.
  - Lint/format:
    ```bash
    ruff check .
    ruff format .
    ```
- Self-review:
  - Fail-fast error messages include next steps (e.g., “Missing ONNX models; run export.py or use engine=torch”).
  - No changes to UI/JS; minimal diffs; public APIs untouched.

References (if any)
- ONNX models default path: `models/default/{model_base.onnx, model_token.onnx}` and `config.json`.
- Torch path: app.py generation flow; ONNX path: app_onnx.py generation flow.
- NN/g careful prompting: https://www.nngroup.com/articles/careful-prompts/

Optional protocol details
- Request `params` minimal shape (defaults if omitted):
  - `{"seed": <int>, "max_events": <int>, "temperature": <float>, "top_p": <float>, "top_k": <int>}`
  - Defaults: seed=42, max_events=256, temperature=1.0, top_p=0.95, top_k=50.
- Error examples:
  - Missing models: `{"status":"error","error":"ONNX models not found. Next steps: run export.py ... or set engine=torch."}`
  - Invalid action: `{"status":"error","error":"Unsupported action. Use 'generate-midi'."}`
