"""
EDGE SERVER  (a cache node close to users)
------------------------------------------
This is a REAL web server too. Users request content from it.
  - If it HAS the content cached  -> return it instantly (CACHE HIT).
  - If it DOESN'T                 -> fetch from the ORIGIN over HTTP,
                                     store a copy, then return it (CACHE MISS).

We run SEVERAL of these on different ports to represent edge servers in
different cities. Each keeps its OWN cache.

The cache uses LRU (Least Recently Used) eviction: when it's full, the item
that hasn't been used in the longest time gets dropped. This is what real
CDNs do.

Run it (example — a Mumbai edge on port 9101):
    python edge_server.py --name Mumbai --port 9101
"""

import argparse
import time
from collections import OrderedDict

import requests
from flask import Flask, jsonify

ORIGIN_URL = "http://localhost:9000"
CACHE_CAPACITY = 3   # deliberately small so you can SEE eviction happen


class LRUCache:
    """Least-Recently-Used cache. Oldest-untouched item is evicted first."""

    def __init__(self, capacity):
        self.capacity = capacity
        self.store = OrderedDict()   # content_id -> data

    def get(self, key):
        if key not in self.store:
            return None
        self.store.move_to_end(key)  # touching it makes it "recently used"
        return self.store[key]

    def put(self, key, value):
        self.store[key] = value
        self.store.move_to_end(key)
        if len(self.store) > self.capacity:
            evicted, _ = self.store.popitem(last=False)  # drop the oldest
            return evicted
        return None

    def keys(self):
        return list(self.store.keys())


def create_edge(name, port):
    app = Flask(__name__)
    cache = LRUCache(CACHE_CAPACITY)
    stats = {"hits": 0, "misses": 0, "name": name}

    # Allow the browser dashboard (a different origin) to read our stats.
    @app.after_request
    def add_cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    @app.route("/get/<path:content_id>")
    def get(content_id):
        """A user requests content from this edge server."""
        start = time.time()

        cached = cache.get(content_id)
        if cached is not None:
            # ---- CACHE HIT: we already have it, return instantly ----
            stats["hits"] += 1
            elapsed = (time.time() - start) * 1000
            return jsonify({
                "content_id": content_id,
                "data": cached,
                "result": "HIT",
                "served_by": name,
                "latency_ms": round(elapsed, 1),
            })

        # ---- CACHE MISS: go fetch it from the origin over HTTP ----
        stats["misses"] += 1
        try:
            resp = requests.get(f"{ORIGIN_URL}/content/{content_id}", timeout=5)
        except requests.RequestException as e:
            return jsonify({"error": f"origin unreachable: {e}"}), 502

        if resp.status_code != 200:
            return jsonify({"error": "content not found at origin"}), 404

        data = resp.json()["data"]
        evicted = cache.put(content_id, data)   # store our own copy
        elapsed = (time.time() - start) * 1000

        return jsonify({
            "content_id": content_id,
            "data": data,
            "result": "MISS",
            "served_by": name,
            "fetched_from": "ORIGIN",
            "evicted": evicted,        # what we dropped to make room (if any)
            "latency_ms": round(elapsed, 1),
        })

    @app.route("/stats")
    def get_stats():
        total = stats["hits"] + stats["misses"]
        ratio = (stats["hits"] / total * 100) if total else 0
        return jsonify({
            **stats,
            "hit_ratio": round(ratio, 1),
            "cached_now": cache.keys(),
        })

    @app.route("/")
    def home():
        return jsonify({"server": f"EDGE-{name}", "port": port})

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="edge name, e.g. Mumbai")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    print(f"EDGE SERVER '{args.name}' running on http://localhost:{args.port}")
    print(f"Cache capacity: {CACHE_CAPACITY} items (LRU eviction)")
    app = create_edge(args.name, args.port)
    app.run(port=args.port, debug=False)
