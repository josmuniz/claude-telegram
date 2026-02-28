#!/usr/bin/env python3
"""
Mining Forensic — Telegram Command Bot Daemon (Claude-powered)
Polls Telegram every 5s. Fixed commands run instantly; natural language goes to Claude API.

Fixed commands (fast, no API cost):
  /help    - List available commands
  /status  - git status + branch + last commit
  /git     - git log --oneline -15
  /branch  - Current branch + divergence
  /tests   - Run pytest tests/
  /diff    - git diff --stat HEAD

Everything else → Claude claude-haiku-4-5-20251001 with project context + tools
"""

import http.client
import json
import os
import ssl
import sys
import subprocess
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID        = str(os.environ.get("TELEGRAM_CHAT_ID", ""))
ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
PROJECT_DIR    = "/Users/josemuniz/mining_forensic"
OFFSET_FILE    = Path(__file__).parent / ".telegram_bot_offset"
POLL_INTERVAL  = 5
MAX_MSG_LEN    = 4000
CLAUDE_MODEL   = "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOK = 1024


# ── Telegram API ──────────────────────────────────────────────────────────────
def tg_call(method: str, payload: dict, retries: int = 3) -> dict:
    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read())
        except Exception as e:
            print(f"[TG error] {method} intento {attempt+1}/{retries}: {e}", file=sys.stderr, flush=True)
            if attempt < retries - 1:
                time.sleep(2)
    return {}


def send(text: str) -> None:
    if len(text) > MAX_MSG_LEN:
        text = text[:MAX_MSG_LEN - 50] + "\n\n… (truncado)"
    tg_call("sendMessage", {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})


def send_code(output: str, title: str = "") -> None:
    header = f"<b>{title}</b>\n\n" if title else ""
    room   = MAX_MSG_LEN - len(header) - 20
    body   = output if len(output) <= room else output[:room - 30] + "\n… (truncado)"
    send(f"{header}<pre>{body}</pre>")


# ── Offset ────────────────────────────────────────────────────────────────────
def load_offset() -> int:
    try:
        return int(OFFSET_FILE.read_text().strip())
    except Exception:
        return 0


def save_offset(offset: int) -> None:
    OFFSET_FILE.write_text(str(offset))


# ── Shell runner ──────────────────────────────────────────────────────────────
def run(cmd: list, timeout: int = 60, cwd: str = PROJECT_DIR) -> str:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        out = r.stdout.strip()
        err = r.stderr.strip()
        if r.returncode != 0 and err:
            return f"{out}\nSTDERR:\n{err}".strip()
        return out or "(sin output)"
    except subprocess.TimeoutExpired:
        return f"Timeout después de {timeout}s"
    except Exception as e:
        return f"Error: {e}"


# ── Fixed commands ────────────────────────────────────────────────────────────
HELP_TEXT = """\
<b>Mining Forensic Bot</b> — Comandos rápidos:

/status  — git status + rama + último commit
/git     — últimos 15 commits
/branch  — rama + divergencia con origin
/diff    — git diff --stat HEAD
/tests   — correr pytest tests/
/help    — este mensaje

<i>También puedes escribir en lenguaje natural y Claude te responderá.</i>"""


def cmd_status() -> str:
    branch = run(["git", "branch", "--show-current"])
    status = run(["git", "status", "--short"])
    last   = run(["git", "log", "--oneline", "-1"])
    return f"Rama: {branch}\nÚltimo commit: {last}\n\n{status or '(working tree limpio)'}"

def cmd_git()    -> str: return run(["git", "log", "--oneline", "-15"])
def cmd_diff()   -> str: return run(["git", "diff", "--stat", "HEAD"]) or "(sin cambios)"
def cmd_tests()  -> str: return run(["python", "-m", "pytest", "tests/", "-v", "--tb=short", "--no-header"], timeout=120)

def cmd_branch() -> str:
    branch  = run(["git", "branch", "--show-current"])
    diverge = run(["git", "rev-list", "--left-right", "--count", f"origin/{branch}...HEAD"])
    return f"Rama: {branch}\nDivergencia (behind/ahead): {diverge}"


FIXED = {
    "/status": (cmd_status, "Git Status"),
    "/git":    (cmd_git,    "Git Log"),
    "/branch": (cmd_branch, "Branch Info"),
    "/diff":   (cmd_diff,   "Git Diff"),
    "/tests":  (cmd_tests,  "Pytest"),
}


# ── Claude API with tools ─────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    f"Asistente Mining Forensic ({PROJECT_DIR}). "
    "Stack: Python/PyQt6/FastAPI/PostgreSQL/Redis/Next.js. "
    "Forense: TruFor,CATNet,ELA,OCR,Qwen2-VL. "
    "Responde en español conciso basándote en el CONTEXTO DEL PROYECTO provisto. "
    "Formato Telegram HTML: <b>,<i>,<code>,<pre>. Max 3500 chars."
)


def _gather_context() -> str:
    """Contexto compacto del proyecto (< 300 chars para no superar límite TCP)."""
    branch = run(["git", "branch", "--show-current"], cwd=PROJECT_DIR)
    last   = run(["git", "log", "--oneline", "-1"],   cwd=PROJECT_DIR)
    py_cnt = run(["bash", "-c", f"find {PROJECT_DIR} -name '*.py' | wc -l"]).strip()
    dirty  = run(["git", "status", "--porcelain"],    cwd=PROJECT_DIR)
    n_mod  = len([l for l in dirty.splitlines() if l and not l.startswith("??")])
    n_new  = len([l for l in dirty.splitlines() if l.startswith("??")])
    ctx = (
        f"rama:{branch} commit:{last[:55]} "
        f"py:{py_cnt} mod:{n_mod} new:{n_new}"
    )
    return ctx[:280]


def _claude_api_single(user_with_ctx: str) -> str:
    """Una sola llamada a Claude sin tools. Retorna texto de respuesta."""
    import tempfile
    body = json.dumps({
        "model":      CLAUDE_MODEL,
        "max_tokens": CLAUDE_MAX_TOK,
        "system":     SYSTEM_PROMPT,
        "messages":   [{"role": "user", "content": user_with_ctx}],
    })

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    tmp.write(body)
    tmp.close()

    curl_env = {"HOME": os.environ.get("HOME", "/Users/josemuniz"), "PATH": "/usr/bin:/bin"}

    try:
        result = subprocess.run(
            [
                "/usr/bin/curl", "-s", "-S", "--http1.1", "--max-time", "90",
                "-X", "POST", "https://api.anthropic.com/v1/messages",
                "-H", f"x-api-key: {ANTHROPIC_KEY}",
                "-H", "anthropic-version: 2023-06-01",
                "-H", "content-type: application/json",
                "--data-binary", f"@{tmp.name}",
            ],
            capture_output=True, text=True, timeout=95,
            env=curl_env,
        )
    finally:
        os.unlink(tmp.name)

    if result.returncode != 0:
        raise RuntimeError(f"curl error ({result.returncode}): {result.stderr.strip()}")

    data = json.loads(result.stdout)

    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"API error {err.get('type')}: {err.get('message')}")

    parts = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    return "\n".join(parts) or "(sin respuesta)"


def ask_claude(user_message: str) -> str:
    if not ANTHROPIC_KEY:
        return "ANTHROPIC_API_KEY no configurada."
    try:
        ctx     = _gather_context()
        payload = f"{ctx}\nPregunta: {user_message}"
        return _claude_api_single(payload)
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"[Claude HTTPError {e.code}] {err}", file=sys.stderr, flush=True)
        return f"Error API {e.code}: {err[:200]}"
    except Exception as e:
        import traceback
        print(f"[Claude error] {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return f"Error: {type(e).__name__}: {e}"


# ── Message handler ───────────────────────────────────────────────────────────
def handle(text: str) -> None:
    cmd = text.strip().lower().split()[0] if text.strip() else ""

    if cmd == "/help":
        send(HELP_TEXT)
        return

    if cmd in FIXED:
        fn, title = FIXED[cmd]
        send(f"⏳ <b>{title}</b>…")
        send_code(fn(), title)
        return

    # Natural language → Claude
    send("🤔 Consultando a Claude…")
    try:
        reply = ask_claude(text)
        send(reply)
    except Exception as e:
        print(f"[handle error] {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        send(f"❌ Error procesando mensaje: {type(e).__name__}: {e}")


# ── Main loop ─────────────────────────────────────────────────────────────────
def wait_for_network(max_wait: int = 60) -> bool:
    """Espera hasta que la red esté disponible (útil al arrancar con launchd)."""
    import socket
    for i in range(max_wait):
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except Exception:
            print(f"[bot] Esperando red... ({i+1}/{max_wait}s)", flush=True)
            time.sleep(1)
    return False


def main() -> None:
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID son requeridos", file=sys.stderr)
        sys.exit(1)

    print(f"[bot] Iniciado con Claude {CLAUDE_MODEL}. Proyecto: {PROJECT_DIR}", flush=True)

    if not wait_for_network():
        print("[bot] Red no disponible después de 60s, abortando.", file=sys.stderr, flush=True)
        sys.exit(1)

    print("[bot] Red disponible.", flush=True)

    send(f"🟢 <b>Mining Forensic Bot</b> (Claude-powered) iniciado.\nUsa /help o escribe en lenguaje natural.")

    offset = load_offset()

    while True:
        try:
            resp    = tg_call("getUpdates", {"offset": offset, "timeout": 5})
            updates = resp.get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                save_offset(offset)

                msg     = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text    = msg.get("text", "")

                if chat_id != CHAT_ID:
                    print(f"[bot] Ignorado chat no autorizado: {chat_id}", flush=True)
                    continue

                if text:
                    print(f"[bot] Mensaje: {text!r}", flush=True)
                    handle(text)

        except KeyboardInterrupt:
            send("🔴 Bot detenido.")
            print("[bot] Detenido.", flush=True)
            break
        except Exception as e:
            print(f"[bot] Error en loop: {e}", file=sys.stderr, flush=True)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
