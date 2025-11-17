import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import onnxruntime as rt
import websockets

import MIDI
import app_onnx  # reuse tokenizer + generation utilities


def ensure_outputs_dir() -> None:
    Path("outputs").mkdir(parents=True, exist_ok=True)


def next_output_path(prefix: str = "outputs/output_ws", ext: str = ".mid") -> str:
    ensure_outputs_dir()
    i = 1
    while True:
        p = f"{prefix}{i}{ext}"
        if not os.path.exists(p):
            return p
        i += 1


def build_initial_prompt(
    tokenizer,
    bpm: int = 0,
    time_sig: str = "auto",
    key_sig: str = "auto",
    instruments: Optional[List[str]] = None,
    drum_kit: str = "None",
) -> np.ndarray:
    mid = [[tokenizer.bos_id] + [tokenizer.pad_id] * (tokenizer.max_token_seq - 1)]
    if tokenizer.version == "v2":
        time_sig_nn = 4
        time_sig_dd = 2
        if time_sig and time_sig != "auto":
            nn, dd = time_sig.split("/")
            time_sig_nn = int(nn)
            time_sig_dd = {2: 1, 4: 2, 8: 3}[int(dd)]
            mid.append(tokenizer.event2tokens(["time_signature", 0, 0, 0, time_sig_nn - 1, time_sig_dd - 1]))
        # key signature handling intentionally minimal here
    if bpm and int(bpm) != 0:
        mid.append(tokenizer.event2tokens(["set_tempo", 0, 0, 0, int(bpm)]))

    # Optional instrument/drum kit setup mirrors app logic
    number2drum_kits = {-1: "None", 0: "Standard", 8: "Room", 16: "Power", 24: "Electric", 25: "TR-808", 32: "Jazz",
                        40: "Blush", 48: "Orchestra"}
    patch2number = {v: k for k, v in MIDI.Number2patch.items()}
    drum_kits2number = {v: k for k, v in number2drum_kits.items()}

    patches = {}
    if instruments:
        i = 0
        for instr in instruments:
            if instr not in patch2number:
                # skip unknown instrument names silently to keep minimal surface
                continue
            patches[i] = patch2number[instr]
            i = (i + 1) if i != 8 else 10  # skip channel 9 (drums)
    if drum_kit and drum_kit != "None" and drum_kit in drum_kits2number:
        patches[9] = drum_kits2number[drum_kit]
    for idx, (c, p) in enumerate(patches.items()):
        mid.append(tokenizer.event2tokens(["patch_change", 0, 0, idx + 1, c, p]))

    return np.asarray([mid], dtype=np.int64)


class OnnxEngine:
    def __init__(self, config_path: str, base_path: str, token_path: str):
        rt.set_default_logger_severity(3)
        self.tokenizer = app_onnx.get_tokenizer(config_path)
        available = rt.get_available_providers()
        if "CUDAExecutionProvider" in available:
            self.providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            app_onnx.device = "cuda"
        else:
            self.providers = ["CPUExecutionProvider"]
            app_onnx.device = "cpu"
        try:
            self.model_base = rt.InferenceSession(base_path, providers=self.providers)
            self.model_token = rt.InferenceSession(token_path, providers=self.providers)
        except Exception as e:
            raise RuntimeError(
                "Failed to load ONNX models. Next steps: verify models/default/{model_base.onnx, model_token.onnx} "
                "exist or run export.py, or use the Gradio app to download." ) from e

    def generate_midi(self,
                      seed: int = 42,
                      gen_events: int = 256,
                      temp: float = 1.0,
                      top_p: float = 0.95,
                      top_k: int = 50,
                      bpm: int = 0,
                      time_sig: str = "auto",
                      instruments: Optional[List[str]] = None,
                      drum_kit: str = "None",
                      allow_cc: bool = True,
                      ) -> Tuple[str, bytes]:
        prompt = build_initial_prompt(self.tokenizer, bpm=bpm, time_sig=time_sig,
                                      instruments=instruments, drum_kit=drum_kit)
        max_len = gen_events + prompt.shape[1]
        generator = np.random.RandomState(int(seed))
        model_tuple = (self.model_base, self.model_token, self.tokenizer)
        mid_seq = prompt.tolist()[0]  # Extract the first (and only) sequence from batch

        # If instruments are pinned, mirror app behavior: disable further patch_change and restrict channels
        disable_patch_change = bool(instruments)
        disable_channels = None
        if instruments:
            number2drum_kits = {-1: "None", 0: "Standard", 8: "Room", 16: "Power", 24: "Electric", 25: "TR-808", 32: "Jazz",
                                40: "Blush", 48: "Orchestra"}
            drum_kits2number = {v: k for k, v in number2drum_kits.items()}
            # replicate channel selection used earlier
            used_channels = set()
            i = 0
            for _ in instruments:
                used_channels.add(i)
                i = (i + 1) if i != 8 else 10
            if drum_kit and drum_kit != "None" and drum_kit in drum_kits2number:
                used_channels.add(9)
            disable_channels = [i for i in range(16) if i not in used_channels]
        for token_seq in app_onnx.generate(model_tuple,
                                           prompt,
                                           batch_size=1,
                                           max_len=max_len,
                                           temp=float(temp),
                                           top_p=float(top_p),
                                           top_k=int(top_k),
                                           disable_patch_change=disable_patch_change,
                                           disable_control_change=not allow_cc,
                                           disable_channels=disable_channels,
                                           generator=generator):
            mid_seq.append(token_seq.tolist()[0])
        # Detokenize and serialize
        mid_score = self.tokenizer.detokenize(mid_seq)
        midi_bytes = MIDI.score2midi(mid_score)
        out_path = next_output_path()
        with open(out_path, "wb") as f:
            f.write(midi_bytes)
        return out_path, midi_bytes


async def handler(websocket):
    try:
        msg = await websocket.recv()
        print(f"[SERVER] Received message: {msg[:200]}...")
        data = json.loads(msg)
        print(f"[SERVER] Parsed JSON: action={data.get('action')}, params keys={list(data.get('params', {}).keys())}")
        if not isinstance(data, dict):
            raise ValueError("Expected JSON object")
        action = data.get("action")
        if action != "generate-midi":
            await websocket.send(json.dumps({"status": "error", "error": "Unsupported action. Use 'generate-midi'."}))
            return
        params = data.get("params", {})
        seed = int(params.get("seed", 42))
        gen_events = int(params.get("gen_events", params.get("max_events", 256)))
        temp = float(params.get("temperature", params.get("temp", 1.0)))
        top_p = float(params.get("top_p", 0.95))
        top_k = int(params.get("top_k", 50))
        bpm = int(params.get("bpm", 0))
        time_sig = params.get("time_sig", "auto")
        instruments = params.get("instruments") or []
        drum_kit = params.get("drum_kit", "None")
        allow_cc = bool(params.get("allow_cc", True))
        print(f"[SERVER] Parsed params: seed={seed}, events={gen_events}, instruments={instruments}, drum_kit={drum_kit}, allow_cc={allow_cc}")

        print(f"[SERVER] Calling generate_midi...")
        out_path, midi_bytes = ENGINE.generate_midi(
            seed=seed, gen_events=gen_events, temp=temp, top_p=top_p, top_k=top_k,
            bpm=bpm, time_sig=time_sig, instruments=instruments, drum_kit=drum_kit, allow_cc=allow_cc
        )
        print(f"[SERVER] Generated MIDI: {len(midi_bytes)} bytes at {out_path}")
        midi_b64 = base64.b64encode(midi_bytes).decode("ascii")
        print(f"[SERVER] Encoded to base64: {len(midi_b64)} chars")
        response = {
            "status": "ok",
            "filename": os.path.basename(out_path),
            "path": out_path,
            "midi_b64": midi_b64,
        }
        print(f"[SERVER] Sending response...")
        await websocket.send(json.dumps(response))
        print(f"[SERVER] Response sent successfully")
    except Exception as e:
        import traceback
        print(f"[SERVER ERROR] {e}")
        traceback.print_exc()
        await websocket.send(json.dumps({"status": "error", "error": str(e)}))


def main():
    parser = argparse.ArgumentParser(description="Minimal WebSocket server for MIDI generation (ONNX)")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model-config", type=str, default="models/default/config.json")
    parser.add_argument("--model-base", type=str, default="models/default/model_base.onnx")
    parser.add_argument("--model-token", type=str, default="models/default/model_token.onnx")
    args = parser.parse_args()

    global ENGINE
    ENGINE = OnnxEngine(args.model_config, args.model_base, args.model_token)

    start_server = websockets.serve(handler, args.host, args.port)
    print(f"WebSocket server listening on ws://{args.host}:{args.port}")
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
