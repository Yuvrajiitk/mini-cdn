"""
ONE-COMMAND LAUNCHER
--------------------
Starts the origin server, all three edge servers, waits for them to be ready,
then runs the demo. This is the easy way to see everything work at once.

Run:   python start_all.py

(You can also run each server in its own terminal manually — see README.)
"""

import subprocess
import sys
import time
import requests

PROCS = []


def start(cmd):
    # start a server as a background process
    p = subprocess.Popen([sys.executable] + cmd,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    PROCS.append(p)
    return p


def wait_until_up(url, timeout=15):
    start_t = time.time()
    while time.time() - start_t < timeout:
        try:
            requests.get(url, timeout=1)
            return True
        except requests.RequestException:
            time.sleep(0.3)
    return False


def main():
    print("Starting origin server...")
    start(["origin_server.py"])

    print("Starting edge servers (Mumbai, London, NewYork)...")
    start(["edge_server.py", "--name", "Mumbai",  "--port", "9101"])
    start(["edge_server.py", "--name", "London",  "--port", "9102"])
    start(["edge_server.py", "--name", "NewYork", "--port", "9103"])

    print("Starting dashboard...")
    start(["dashboard.py"])

    # Wait for all of them to be reachable.
    print("Waiting for servers to come online...")
    endpoints = [
        "http://localhost:9000/",
        "http://localhost:9101/",
        "http://localhost:9102/",
        "http://localhost:9103/",
        "http://localhost:8080/",
    ]
    for ep in endpoints:
        if not wait_until_up(ep):
            print(f"ERROR: {ep} did not start.")
            cleanup()
            return
    print("All servers are up.\n")

    print("=" * 60)
    print("  OPEN YOUR BROWSER AT:  http://localhost:8080")
    print("=" * 60)
    print("\nClick 'Send 10 requests' or 'Start auto traffic' and watch")
    print("the caches fill and hit ratios climb live.\n")
    print("Press Ctrl+C here to stop everything.\n")

    # Keep running so the dashboard stays alive until you Ctrl+C.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    cleanup()


def cleanup():
    print("\nShutting down all servers...")
    for p in PROCS:
        p.terminate()
    for p in PROCS:
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cleanup()
