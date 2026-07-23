"""
CLIENT + ROUTER  (simulates users hitting the CDN)
--------------------------------------------------
This program:
  1. Knows where each edge server is (city + lat/lon + its URL).
  2. For each user request, finds the NEAREST edge (real distance math).
  3. Sends a REAL HTTP request to that edge to fetch content.
  4. Collects and prints stats.

This is the piece that decides "take data from the nearest server".
In a real CDN this routing is done by DNS / anycast — here we do it explicitly
so it's easy to see and explain.

Run it AFTER starting the origin and all edge servers:
    python run_demo.py
"""

import math
import random
import requests

# --- Where each edge server lives (city, coordinates, and its URL) ----------
EDGES = [
    {"name": "Mumbai",   "lat": 19.0, "lon": 72.8,  "url": "http://localhost:9101"},
    {"name": "London",   "lat": 51.5, "lon": -0.1,  "url": "http://localhost:9102"},
    {"name": "NewYork",  "lat": 40.7, "lon": -74.0, "url": "http://localhost:9103"},
]

# --- Where our users are ----------------------------------------------------
USERS = {
    "Delhi user":     (28.6, 77.2),
    "Paris user":     (48.9, 2.3),
    "Boston user":    (42.4, -71.1),
    "Bangalore user": (13.0, 77.6),
}

CONTENT_POOL = ["home.html", "logo.png", "video1.mp4", "style.css", "app.js"]


def distance_km(lat1, lon1, lat2, lon2):
    """Haversine distance — used to find the nearest edge."""
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def nearest_edge(user_lat, user_lon):
    """Pick the geographically closest edge server."""
    return min(EDGES, key=lambda e: distance_km(user_lat, user_lon, e["lat"], e["lon"]))


def run(num_requests=20):
    print("=" * 64)
    print("CDN DEMO — routing each user to their nearest edge server")
    print("=" * 64)

    total_latency = 0.0

    for i in range(num_requests):
        user, (u_lat, u_lon) = random.choice(list(USERS.items()))
        content = random.choice(CONTENT_POOL)

        # 1) ROUTE: find the nearest edge to this user.
        edge = nearest_edge(u_lat, u_lon)

        # 2) FETCH: send a real HTTP request to that edge.
        try:
            resp = requests.get(f"{edge['url']}/get/{content}", timeout=10)
            info = resp.json()
        except requests.RequestException as e:
            print(f"[{i+1:2}] ERROR reaching {edge['name']}: {e}")
            print("     (Did you start the edge servers? See instructions.)")
            return

        result = info["result"]
        latency = info["latency_ms"]
        total_latency += latency

        note = ""
        if info.get("evicted"):
            note = f"  (evicted '{info['evicted']}' to make room)"

        print(f"[{i+1:2}] {user:15} wants {content:11} "
              f"-> nearest edge: {edge['name']:8} [{result}] "
              f"{latency:7.1f} ms{note}")

    # --- Gather final stats from each edge + the origin --------------------
    print("=" * 64)
    print("RESULTS")
    print("=" * 64)
    print(f"Average latency across all requests: {total_latency/num_requests:.1f} ms\n")

    print("Per edge-server cache performance:")
    total_hits = 0
    for e in EDGES:
        try:
            s = requests.get(f"{e['url']}/stats", timeout=5).json()
            total_hits += s["hits"]
            print(f"  {e['name']:8}  hit ratio {s['hit_ratio']:5.1f}%  "
                  f"(hits={s['hits']}, misses={s['misses']})  "
                  f"currently cached: {s['cached_now']}")
        except requests.RequestException:
            print(f"  {e['name']:8}  (could not reach for stats)")

    try:
        o = requests.get("http://localhost:9000/stats", timeout=5).json()
        origin_load = o["requests_served"]
        print(f"\nOrigin server was hit {origin_load} times "
              f"out of {num_requests} requests "
              f"({origin_load/num_requests*100:.0f}%).")
        print(f"That means {100 - origin_load/num_requests*100:.0f}% of requests "
              f"were served from cache — the whole point of a CDN.")
    except requests.RequestException:
        print("\n(Could not reach origin for stats.)")

    print("=" * 64)


if __name__ == "__main__":
    random.seed(1)   # repeatable demo; remove for variety
    run(num_requests=20)
