# - Start the real squirrel_server.py once per session (subprocess).
# - Reset the DB file to a clean template before each test.
# - Expose base_url for HTTP tests.
# - Make project root importable so tests can import mydb.py, etc.

import sys
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest
import requests

# Ensure project root (where mydb.py, squirrel_server.py live) is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# File paths / config
DB_TEMPLATE = ROOT / "empty_squirrel_db.db"   # clean template provided by the course
DB_FILE = ROOT / "squirrel_db.db"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

def _wait_for_server(url: str, timeout=5.0):
    """Poll the server until a request gets a response (404 is fine), proving the socket is open."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(url + "/__healthcheck__")
            return True
        except Exception:
            time.sleep(0.1)
    return False

@pytest.fixture(scope="session", autouse=True)
def server_process():
    """Launch the real HTTP server for the whole test session; tear down at the end."""
    proc = subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "squirrel_server.py")],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if not _wait_for_server(BASE_URL, timeout=6.0):
        # If startup fails, dump a bit of output to aid debugging
        try:
            time.sleep(0.3)
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"Server failed to start on {SERVER_HOST}:{SERVER_PORT}\n{out}")
        finally:
            proc.kill()
    yield proc
    # Graceful shutdown
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        proc.kill()

@pytest.fixture(autouse=True)
def reset_db():
    """Before each test, reset the runtime DB to the pristine template to ensure isolation."""
    assert DB_TEMPLATE.exists(), f"Missing template DB: {DB_TEMPLATE}"
    shutil.copyfile(DB_TEMPLATE, DB_FILE)
    yield
    # Optionally keep DB_FILE for post-test inspection

@pytest.fixture(scope="session")
def base_url():
    """Base URL for all API calls."""
    return BASE_URL
