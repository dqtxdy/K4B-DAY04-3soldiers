from __future__ import annotations

import argparse
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from chat import run_model_tool_loop, safe_slug
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
load_lab_env(ROOT)

PAGE = """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Northstar IT Helpdesk</title>
  <style>
    body { font: 16px system-ui, sans-serif; max-width: 980px; margin: 32px auto; padding: 0 16px; color: #172033; }
    header, form, article { border: 1px solid #ccd3df; border-radius: 10px; padding: 16px; margin-bottom: 14px; }
    header { background: #f4f7fb; } #meta { color: #526079; font-size: 14px; }
    textarea { box-sizing: border-box; width: 100%; min-height: 82px; padding: 10px; }
    button { margin-top: 8px; padding: 9px 16px; cursor: pointer; }
    .user { border-left: 5px solid #3267d6; } .agent { border-left: 5px solid #18865b; }
    .error { border-left: 5px solid #c43d3d; color: #8d2222; }
    details { margin-top: 10px; } pre { overflow: auto; background: #f6f7f9; padding: 10px; white-space: pre-wrap; }
  </style>
</head>
<body>
  <header><h1>Northstar IT Helpdesk</h1><div id="meta">Đang tải phiên bản…</div></header>
  <main id="chat"></main>
  <form id="form">
    <label for="message">Yêu cầu</label>
    <textarea id="message" required placeholder="Ví dụ: Kiểm tra VPN production."></textarea>
    <br><button type="submit">Gửi</button>
  </form>
<script>
const chat = document.querySelector('#chat');
const form = document.querySelector('#form');
const input = document.querySelector('#message');
const history = [];
const sessionId = crypto.randomUUID();

function block(css, title, body, trace) {
  const el = document.createElement('article'); el.className = css;
  const heading = document.createElement('strong'); heading.textContent = title; el.appendChild(heading);
  const text = document.createElement('p'); text.textContent = body || '(không có text)'; el.appendChild(text);
  if (trace) {
    const details = document.createElement('details'); const summary = document.createElement('summary');
    summary.textContent = 'Tool trace: name / input / result / error'; details.appendChild(summary);
    const pre = document.createElement('pre'); pre.textContent = JSON.stringify(trace, null, 2); details.appendChild(pre); el.appendChild(details);
  }
  chat.appendChild(el);
}

fetch('/api/meta').then(r => r.json()).then(meta => {
  document.querySelector('#meta').textContent = `${meta.artifact_version} · ${meta.provider} · ${meta.model}`;
});

form.addEventListener('submit', async event => {
  event.preventDefault(); const message = input.value.trim(); if (!message) return;
  block('user', 'Bạn', message); input.value = ''; form.querySelector('button').disabled = true;
  try {
    const response = await fetch('/api/chat', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({session_id: sessionId, message, history})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
    block('agent', 'Agent', data.assistant_text, data.rounds);
    history.push({role: 'user', content: message}, {role: 'assistant', content: data.assistant_text});
  } catch (error) { block('error', 'Lỗi', String(error)); }
  finally { form.querySelector('button').disabled = false; input.focus(); }
});
</script>
</body>
</html>"""


class HelpdeskWebApp:
    def __init__(self, *, provider_name: str, model: str, version: str) -> None:
        self.provider_name = provider_name
        self.model = model
        self.provider = make_provider(provider_name)
        self.system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
        self.tools_path = ARTIFACTS_DIR / "tools.yaml"
        self.system_prompt = self.system_prompt_path.read_text(encoding="utf-8")
        self.tools = to_openai_tools(load_tool_declarations(self.tools_path))
        self.artifact = build_artifact_version(version, self.system_prompt_path, self.tools_path)

    def meta(self) -> dict[str, Any]:
        return {
            **artifact_version_dict(self.artifact),
            "provider": self.provider_name,
            "model": self.model,
        }

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = payload.get("message")
        history = payload.get("history", [])
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must be a non-empty string")
        if not isinstance(history, list) or len(history) > 12:
            raise ValueError("history must contain at most 12 messages")

        safe_history: list[dict[str, str]] = []
        for item in history:
            if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
                raise ValueError("invalid history item")
            content = item.get("content")
            if not isinstance(content, str) or len(content) > 4000:
                raise ValueError("invalid history content")
            safe_history.append({"role": item["role"], "content": content})

        result = run_model_tool_loop(
            provider=self.provider,
            messages=[{"role": "system", "content": self.system_prompt}, *safe_history, {"role": "user", "content": message.strip()}],
            tools=self.tools,
            model=self.model,
            max_tool_rounds=4,
        )
        self.save_transcript(payload.get("session_id", "ui"), message.strip(), result)
        return {**self.meta(), **result}

    def save_transcript(self, session_id: Any, message: str, result: dict[str, Any]) -> None:
        transcript_id = "ui_" + safe_slug(str(session_id))[:80]
        path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
        if path.exists():
            transcript = json.loads(path.read_text(encoding="utf-8"))
        else:
            transcript = {"transcript_id": transcript_id, **self.meta(), "created_at": datetime.now().isoformat(timespec="seconds"), "turns": []}
        transcript["turns"].append({"user": message, **result})
        transcript["updated_at"] = datetime.now().isoformat(timespec="seconds")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @property
    def app(self) -> HelpdeskWebApp:
        return self.server.app  # type: ignore[attr-defined, no-any-return]

    def do_GET(self) -> None:
        if self.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/meta":
            self.send_json(200, self.app.meta())
        else:
            self.send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_json(404, {"error": "not_found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 100_000:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(size))
            self.send_json(200, self.app.chat(payload))
        except Exception as exc:
            self.send_json(400, {"error": f"{type(exc).__name__}: {exc}"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal browser UI for the IT Helpdesk agent.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--provider", choices=["openai", "openrouter", "anthropic", "gemini"], default="openai")
    parser.add_argument("--model", default="gpt-4.1-mini-2025-04-14")
    parser.add_argument("--version", default="v3_bonus")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.app = HelpdeskWebApp(provider_name=args.provider, model=args.model, version=args.version)  # type: ignore[attr-defined]
    print(f"UI: http://{args.host}:{args.port} ({server.app.artifact.artifact_version})")  # type: ignore[attr-defined]
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
