# - Start the real squirrel_server.py once per session (subprocess) *if needed*.
# - If another server is already running on our port, use it instead of starting a new one.
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


def _server_responds(url: str, timeout: float = 0.5) -> bool:
    """
    Quick check to see if *any* HTTP server is already listening on BASE_URL.

    We hit the real API index (/squirrels), since the assignment guarantees
    that route exists for a running SquirrelServer. Any HTTP response
    (200/404/etc.) means a server is up and handling requests.
    """
    try:
        requests.get(url + "/squirrels", timeout=timeout)
        return True
    except requests.RequestException:
        return False


def _wait_for_server(url: str, timeout: float = 5.0) -> bool:
    """
    Poll the server until an HTTP response is received, proving the socket is open.
    We reuse the same /squirrels endpoint here.
    """
    start = time.time()
    while time.time() - start < timeout:
        if _server_responds(url, timeout=0.5):
            return True
        time.sleep(0.1)
    return False


@pytest.fixture(scope="session", autouse=True)
def server_process():
    """
    Ensure a SquirrelServer is available for the entire test session.

    - If another server is already running on BASE_URL, reuse it and do NOT
      start/stop our own subprocess. This makes our tests play nicely with an
      instructor's already-running server.
    - Otherwise, launch squirrel_server.py as a subprocess and tear it down
      at the end of the session.
    """
    # First, check if someone else already has a server running (e.g., instructor).
    if _server_responds(BASE_URL, timeout=0.5):
        # Reuse the existing server; don't start or stop anything.
        # Yield a sentinel (None) just so tests that depend on this fixture
        # still run in the correct order.
        yield None
        return

    # No server responded; start our own subprocess.
    proc = subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "squirrel_server.py")],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Wait for it to become responsive.
    if not _wait_for_server(BASE_URL, timeout=6.0):
        try:
            time.sleep(0.3)
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(
                f"Server failed to start on {SERVER_HOST}:{SERVER_PORT}\n{out}"
            )
        finally:
            proc.kill()

    # Tests run while this server subprocess is alive.
    yield proc

    # Teardown: only stop the server we started (not any instructor server).
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(autouse=True)
def reset_db():
    """
    Before each test, reset the runtime DB to the pristine template to ensure isolation.

    This is a black-box system test fixture: the server code reads squirrel_db.db,
    and we ensure that file is in a known-empty state at the start of every test.
    """
    assert DB_TEMPLATE.exists(), f"Missing template DB: {DB_TEMPLATE}"
    shutil.copyfile(DB_TEMPLATE, DB_FILE)
    yield
    # Optionally keep DB_FILE for post-test inspection


@pytest.fixture(scope="session")
def base_url():
    """Base URL for all API calls."""
    return BASE_URL
