import argparse
import asyncio
import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import websockets


def ensure_outputs_dir() -> Path:
    p = Path("outputs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def fail(reason: str):
    raise RuntimeError(
        f"Client failed: {reason}. Next steps: verify ws_server is running, URL is reachable, and config schema matches."
    )


async def run_client(url: str, config_path: str, out_path: Optional[str]):
    cfg_file = Path(config_path)
    print(f"[CLIENT] Reading config from {cfg_file}")
    if not cfg_file.exists():
        fail(f"missing config file at {cfg_file}")
    try:
        req = json.loads(cfg_file.read_text(encoding="utf-8"))
        print(f"[CLIENT] Loaded config: {json.dumps(req, indent=2)[:200]}...")
    except Exception as e:
        fail(f"invalid JSON in config file: {e}")
    if not isinstance(req, dict) or req.get("action") != "generate-midi":
        fail("config must be a JSON object with action=='generate-midi'")

    print(f"[CLIENT] Connecting to {url}...")
    async with websockets.connect(url) as ws:
        print(f"[CLIENT] Connected, sending request...")
        await ws.send(json.dumps(req))
        print(f"[CLIENT] Request sent, waiting for response...")
        raw = await ws.recv()
        print(f"[CLIENT] Received {len(raw)} bytes")
        print(f"[CLIENT] Raw response (first 300 chars): {raw[:300]}")
        try:
            resp = json.loads(raw)
            print(f"[CLIENT] Parsed response: status={resp.get('status')}, keys={list(resp.keys())}")
        except Exception as e:
            print(f"[CLIENT ERROR] Failed to parse JSON: {e}")
            fail(f"server returned non-JSON response: {e}")
        if resp.get("status") != "ok":
            fail(resp.get("error", "unknown error"))
        b64 = resp.get("midi_b64")
        if not b64:
            fail("response missing 'midi_b64'")
        print(f"[CLIENT] Decoding base64 ({len(b64)} chars)...")
        data = base64.b64decode(b64)
        print(f"[CLIENT] Decoded {len(data)} bytes of MIDI data")
        ensure_outputs_dir()
        if out_path:
            out_file = Path(out_path)
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fn = resp.get("filename") or f"client_output_{ts}.mid"
            out_file = Path("outputs") / fn
        with open(out_file, "wb") as f:
            f.write(data)
        print(str(out_file))


def main():
    parser = argparse.ArgumentParser(description="WebSocket client demo: send config, save base64 MIDI to outputs")
    parser.add_argument("--url", type=str, default="ws://127.0.0.1:8765")
    parser.add_argument("--config", type=str, default=str(Path("examples") / "ws_client_config.json"))
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()
    try:
        asyncio.run(run_client(args.url, args.config, args.out))
    except Exception as e:
        print(str(e))
        os._exit(1)


if __name__ == "__main__":
    main()
