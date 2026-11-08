"""Run the real browser against an isolated synthetic server on the development port."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

with socket.socket() as probe:
    if probe.connect_ex(("127.0.0.1", 8765)) == 0:
        sys.exit("Port 8765 is in use. Stop the development server before browser tests.")
with tempfile.TemporaryDirectory(prefix="parents-browser-") as temp:
    directory = Path(temp)
    config = directory / "config.toml"
    config.write_text("data_dir = " + repr(str(directory)).replace("'", '"') + "\n")
    server = subprocess.Popen(
        [sys.executable, "-m", "parents_companion.cli", "--config", str(config), "serve"]
    )
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen("http://127.0.0.1:8765/", timeout=1).close()
                break
            except OSError:
                if server.poll() is not None:
                    raise RuntimeError("Test server failed to start")
                time.sleep(0.1)
        else:
            raise RuntimeError("Test server did not become ready")
        subprocess.run(
            ["node", "tests/browser.cjs"], check=True, env={**os.environ, "PARENTS_TEST_DATA": temp}
        )
    finally:
        server.terminate()
        server.wait(timeout=10)
