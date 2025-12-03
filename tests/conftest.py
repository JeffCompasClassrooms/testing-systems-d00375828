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


def _server_responds(timeout: float = 0.5) -> bool:
    """
    Return True if something is already listening on BASE_URL.

    We treat *any* HTTP response from /squirrels as "server is up",
    even if it's 500 or some unexpected status.
    """
    try:
        r = requests.get(f"{BASE_URL}/squirrels", timeout=timeout)
        # If we got *any* response, the socket is open and a server is running.
        return True
    except requests.RequestException:
        return False


def _wait_for_server(timeout: float = 5.0) -> bool:
    """
    After we start our own server process, poll until it begins responding.
    """
    start = time.time()
    while time.time() - start < timeout:
        if _server_responds(timeout=0.5):
            return True
        time.sleep(0.1)
    return False


@pytest.fixture(scope="session", autouse=True)
def server_process():
    """
    Ensure there is a SquirrelServer listening on BASE_URL for the entire
    test session.

    If a server is already running (e.g., the instructor started it),
    reuse that and DO NOT start/stop our own process.

    If not, start our own squirrel_server.py and tear it down at the end.
    """
    # Case 1: something is already serving on BASE_URL – just use it.
    if _server_responds(timeout=0.5):
        # Yield a dummy value; we are not responsible for stopping this server.
        yield None
        return

    # Case 2: no server yet; start our own process.
    proc = subprocess.Popen(
        [sys.executable, "-u", str(ROOT / "squirrel_server.py")],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if not _wait_for_server(timeout=6.0):
        # If startup fails, dump a bit of output to aid debugging
        try:
            time.sleep(0.3)
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(
                f"Server failed to start on {SERVER_HOST}:{SERVER_PORT}\n{out}"
            )
        finally:
            proc.kill()

    # Tests run with our managed process
    yield proc

    # Tear down only if we actually started it and it's still alive
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(autouse=True)
def reset_db():
    """
    Before each test, reset the runtime DB to the pristine template
    to ensure isolation.
    """
    assert DB_TEMPLATE.exists(), f"Missing template DB: {DB_TEMPLATE}"
    shutil.copyfile(DB_TEMPLATE, DB_FILE)
    yield
    # Optionally keep DB_FILE for post-test inspection


@pytest.fixture(scope="session")
def base_url():
    """Base URL for all API calls."""
    return BASE_URL
