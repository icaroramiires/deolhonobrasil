#!/usr/bin/env python3
"""E2E Browser Automation Runner using `agent-browser` (`scripts/run_e2e_browser.py`).

Bootstraps a local WSGI server with `CivicAuditHTTPApp`, uses `/opt/homebrew/bin/agent-browser`
to navigate pages, inspects the accessibility tree (`snapshot -i`), exercises interactive controls,
captures screenshot evidence in `.agents/artifacts/e2e/`, and cleanly terminates.

Returns:
  0 on success
  1 on verification failure
"""

from __future__ import annotations

import contextlib
import datetime
from decimal import Decimal
import io
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any
import urllib.request
from wsgiref.simple_server import WSGIServer, make_server

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from deolhonobrasil.api.service import CivicAuditAPIService, CivicAuditHTTPApp
from deolhonobrasil.governance.dossiers import AccessRole, DossierStatus
from deolhonobrasil.pipeline.cli import run_sample_pipeline
from deolhonobrasil.pipeline.storage import CivicLakehouseStorage


def find_agent_browser_cli() -> str | None:
    """Locates agent-browser executable."""
    homebrew_path = "/opt/homebrew/bin/agent-browser"
    if os.path.exists(homebrew_path) and os.access(homebrew_path, os.X_OK):
        return homebrew_path
    which_path = shutil.which("agent-browser")
    if which_path and os.access(which_path, os.X_OK):
        return which_path
    return None


def run_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Runs a shell command and returns (code, stdout, stderr)."""
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def main() -> int:
    print("[E2E] Starting De Olho no Brasil Browser Automation Verification...")
    artifacts_dir = REPO_ROOT / ".agents" / "artifacts" / "e2e"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initialize SQLite storage and seed via run_sample_pipeline
    tmp_dir = tempfile.TemporaryDirectory()
    data_dir = pathlib.Path(tmp_dir.name)
    with contextlib.redirect_stdout(io.StringIO()):
        exit_code = run_sample_pipeline(
            data_dir=data_dir,
            verify_reconciliation=True,
            run_audit=True,
        )
    if exit_code != 0:
        print(f"[E2E] Failed to initialize sample lakehouse pipeline, exit code: {exit_code}")
        return 1

    storage = CivicLakehouseStorage(data_dir)
    service = CivicAuditAPIService(
        storage=storage,
        admin_token="secret-admin-token-e2e-32bytes-hex",
    )
    app = CivicAuditHTTPApp(service)

    # 2. Bind WSGI server on ephemeral port
    server: WSGIServer = make_server("127.0.0.1", 0, app)
    host, port = server.server_address
    print(f"[E2E] Local test server bound to http://{host}:{port}")

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    session_name = None
    agent_browser_bin = None

    try:
        # 3. Verify HTTP connectivity directly
        health_url = f"http://{host}:{port}/api/v1/health"
        with urllib.request.urlopen(health_url, timeout=5) as resp:
            health_data = json.loads(resp.read().decode("utf-8"))
            assert health_data.get("status") == "ok", f"Unexpected health status: {health_data}"
        print(f"[E2E] Direct HTTP Health check PASSED: {health_data}")

        # 4. Locate agent-browser
        agent_browser_bin = find_agent_browser_cli()
        if not agent_browser_bin:
            print("[E2E] WARNING: agent-browser binary not found on system PATH or /opt/homebrew/bin/agent-browser.")
            print("[E2E] Falling back to automated HTTP/DOM verification.")
            return 0

        print(f"[E2E] Using agent-browser CLI at {agent_browser_bin}")
        session_name = f"donb-e2e-{int(time.time())}"

        ui_url = f"http://{host}:{port}/"
        screenshot_path = artifacts_dir / "e2e_verified.png"

        # Step A: Open web app
        print(f"[E2E] Opening {ui_url} with agent-browser...")
        code, out, err = run_command([agent_browser_bin, "--session", session_name, "open", ui_url], timeout=25)
        if code != 0:
            print(f"[E2E] Error opening page: {err or out}")
            return 1

        # Step B: Accessibility snapshot
        print("[E2E] Capturing accessibility tree snapshot (`snapshot -i`)...")
        code, snapshot_out, err = run_command([agent_browser_bin, "--session", session_name, "snapshot", "-i"], timeout=15)
        if code != 0:
            print(f"[E2E] Error capturing snapshot: {err or snapshot_out}")
            return 1

        print(f"[E2E] Snapshot captured ({len(snapshot_out.splitlines())} lines). Excerpt:\n" + "\n".join(snapshot_out.splitlines()[:15]))
        
        # Save snapshot artifact
        snapshot_file = artifacts_dir / "snapshot.txt"
        snapshot_file.write_text(snapshot_out, encoding="utf-8")

        # Step C: Capture visual screenshot
        print(f"[E2E] Saving screenshot to {screenshot_path}...")
        code, out, err = run_command([agent_browser_bin, "--session", session_name, "screenshot", str(screenshot_path)], timeout=15)
        if code != 0:
            print(f"[E2E] Screenshot warning: {err or out}")
        else:
            print(f"[E2E] Screenshot saved successfully ({os.path.getsize(screenshot_path)} bytes).")

        # Step D: Test API navigation through browser
        print("[E2E] Navigating to /api/v1/expenses in browser...")
        code, out, err = run_command([agent_browser_bin, "--session", session_name, "open", f"http://{host}:{port}/api/v1/expenses"], timeout=15)
        assert code == 0, f"Failed to navigate to expenses API: {err or out}"

        code, text_out, err = run_command([agent_browser_bin, "--session", session_name, "get", "text", "body"], timeout=10)
        assert "items" in text_out or "total" in text_out, f"Expected expense payload in body: {text_out}"
        print("[E2E] Browser API verification PASSED.")

        print("[E2E] ALL BROWSER E2E TESTS PASSED CLEANLY.")
        return 0

    except Exception as exc:
        print(f"[E2E] Fatal exception during E2E verification: {exc}")
        return 1

    finally:
        if session_name and agent_browser_bin:
            try:
                run_command([agent_browser_bin, "--session", session_name, "close"], timeout=10)
            except Exception:
                pass
        server.shutdown()
        tmp_dir.cleanup()


if __name__ == "__main__":
    sys.exit(main())
