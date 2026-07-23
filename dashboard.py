"""
DASHBOARD  (live web UI for the CDN)
------------------------------------
A single Flask server that:
  - Serves a web page at http://localhost:8080
  - The page shows every edge server, its live cache contents, hit ratio,
    and how loaded the origin is — all refreshing automatically.
  - Has a "Send traffic" button that fires simulated user requests so you can
    watch caches fill up and hit ratios climb in real time.

Run everything with:  python start_all.py   (it now starts this too)
Then open:            http://localhost:8080
"""

import math
import random
import requests
from flask import Flask, jsonify, Response

app = Flask(__name__)

# Same edge list + users as run_demo.py — the dashboard IS the traffic source.
EDGES = [
    {"name": "Mumbai",  "lat": 19.0, "lon": 72.8,  "url": "http://localhost:9101"},
    {"name": "London",  "lat": 51.5, "lon": -0.1,  "url": "http://localhost:9102"},
    {"name": "NewYork", "lat": 40.7, "lon": -74.0, "url": "http://localhost:9103"},
]
USERS = {
    "Delhi user":     (28.6, 77.2),
    "Paris user":     (48.9, 2.3),
    "Boston user":    (42.4, -71.1),
    "Bangalore user": (13.0, 77.6),
}
CONTENT_POOL = ["home.html", "logo.png", "video1.mp4", "style.css", "app.js"]


def distance_km(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def nearest_edge(lat, lon):
    return min(EDGES, key=lambda e: distance_km(lat, lon, e["lat"], e["lon"]))


@app.route("/api/send-traffic")
def send_traffic():
    """Fire one random user request and report what happened."""
    user, (lat, lon) = random.choice(list(USERS.items()))
    content = random.choice(CONTENT_POOL)
    edge = nearest_edge(lat, lon)
    try:
        info = requests.get(f"{edge['url']}/get/{content}", timeout=10).json()
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({
        "user": user, "content": content,
        "edge": edge["name"], "result": info["result"],
        "latency_ms": info["latency_ms"], "evicted": info.get("evicted"),
    })


@app.route("/api/state")
def state():
    """Gather live stats from every edge + the origin for the dashboard."""
    edges = []
    for e in EDGES:
        try:
            s = requests.get(f"{e['url']}/stats", timeout=3).json()
            edges.append({
                "name": e["name"], "hits": s["hits"], "misses": s["misses"],
                "hit_ratio": s["hit_ratio"], "cached": s["cached_now"], "up": True,
            })
        except requests.RequestException:
            edges.append({"name": e["name"], "up": False})
    try:
        o = requests.get("http://localhost:9000/stats", timeout=3).json()
        origin_hits = o["requests_served"]
    except requests.RequestException:
        origin_hits = None
    return jsonify({"edges": edges, "origin_requests": origin_hits})


@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")


# --- The web page (HTML + CSS + JS in one string) --------------------------
PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mini CDN — Live Dashboard</title>
<style>
  :root {
    --ink: #0f1b2d;
    --paper: #f5f3ee;
    --edge: #1d6a73;
    --edge-soft: #e0efef;
    --origin: #b6452c;
    --hit: #2f7d55;
    --miss: #b6452c;
    --line: #d8d3c7;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--paper); color: var(--ink);
    font-family: "Segoe UI", system-ui, sans-serif; padding: 28px;
  }
  h1 { font-size: 26px; margin: 0 0 4px; letter-spacing: -0.02em; }
  .sub { color: #5c6470; margin: 0 0 22px; font-size: 14px; }
  .controls { display: flex; gap: 10px; align-items: center; margin-bottom: 24px; flex-wrap: wrap; }
  button {
    background: var(--ink); color: #fff; border: 0; padding: 10px 16px;
    border-radius: 8px; font-size: 14px; cursor: pointer; font-weight: 600;
  }
  button.ghost { background: #fff; color: var(--ink); border: 1px solid var(--line); }
  button:hover { opacity: .9; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }
  .card {
    background: #fff; border: 1px solid var(--line); border-radius: 12px;
    padding: 16px 18px;
  }
  .card.origin { border-color: var(--origin); background: #fdf6f3; }
  .card h2 { margin: 0 0 2px; font-size: 17px; }
  .role { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: #8a8f98; }
  .ratio { font-size: 34px; font-weight: 700; margin: 10px 0 2px; }
  .bar { height: 8px; background: #eee; border-radius: 99px; overflow: hidden; margin: 8px 0; }
  .bar > i { display: block; height: 100%; background: var(--edge); width: 0; transition: width .4s; }
  .hm { font-size: 13px; color: #5c6470; }
  .cache-title { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: #8a8f98; margin: 14px 0 6px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; min-height: 26px; }
  .chip { background: var(--edge-soft); color: var(--edge); border-radius: 6px; padding: 3px 8px; font-size: 12px; font-family: ui-monospace, monospace; }
  .empty { color: #b3b7bd; font-size: 12px; font-style: italic; }
  .originbig { font-size: 34px; font-weight: 700; margin: 10px 0 2px; color: var(--origin); }
  .log {
    margin-top: 26px; background: #0f1b2d; color: #d7e2ea; border-radius: 12px;
    padding: 14px 16px; font-family: ui-monospace, monospace; font-size: 13px;
    height: 200px; overflow-y: auto;
  }
  .log div { padding: 2px 0; border-bottom: 1px solid rgba(255,255,255,.05); }
  .tag-HIT { color: #7fe0a6; font-weight: 700; }
  .tag-MISS { color: #f0a58c; font-weight: 700; }
  .down { color: var(--miss); font-weight: 600; }
</style>
</head>
<body>
  <h1>Mini CDN — Live Dashboard</h1>
  <p class="sub">Each user request is routed to its nearest edge. Watch caches fill and hit ratios climb.</p>

  <div class="controls">
    <button onclick="burst(1)">Send 1 request</button>
    <button onclick="burst(10)">Send 10 requests</button>
    <button class="ghost" id="autoBtn" onclick="toggleAuto()">Start auto traffic</button>
  </div>

  <div class="grid" id="cards"></div>

  <div class="cache-title">Request log</div>
  <div class="log" id="log"></div>

<script>
let auto = null;

async function refresh() {
  const res = await fetch('/api/state');
  const s = await res.json();
  const cards = document.getElementById('cards');
  let html = '';
  for (const e of s.edges) {
    if (!e.up) {
      html += `<div class="card"><span class="role">Edge</span><h2>${e.name}</h2>
               <p class="down">offline</p></div>`;
      continue;
    }
    const chips = e.cached.length
      ? e.cached.map(c => `<span class="chip">${c}</span>`).join('')
      : `<span class="empty">empty — no content cached yet</span>`;
    html += `
      <div class="card">
        <span class="role">Edge server</span>
        <h2>${e.name}</h2>
        <div class="ratio">${e.hit_ratio}%</div>
        <div class="bar"><i style="width:${e.hit_ratio}%"></i></div>
        <div class="hm">${e.hits} hits &middot; ${e.misses} misses</div>
        <div class="cache-title">Cache contents</div>
        <div class="chips">${chips}</div>
      </div>`;
  }
  const origin = s.origin_requests === null ? 'offline' : s.origin_requests;
  html += `
    <div class="card origin">
      <span class="role">Origin server</span>
      <h2>Origin</h2>
      <div class="originbig">${origin}</div>
      <div class="hm">times the origin was hit (lower is better — the CDN is doing its job)</div>
    </div>`;
  cards.innerHTML = html;
}

function log(line, cls) {
  const el = document.getElementById('log');
  const div = document.createElement('div');
  div.innerHTML = line;
  el.prepend(div);
}

async function sendOne() {
  const res = await fetch('/api/send-traffic');
  const r = await res.json();
  if (r.error) { log(`<span class="down">error: ${r.error}</span>`); return; }
  const tag = `<span class="tag-${r.result}">${r.result}</span>`;
  const ev = r.evicted ? ` (evicted ${r.evicted})` : '';
  log(`${r.user} wants ${r.content} → ${r.edge} ${tag} ${r.latency_ms}ms${ev}`);
  refresh();
}

async function burst(n) {
  for (let i = 0; i < n; i++) { await sendOne(); }
}

function toggleAuto() {
  const btn = document.getElementById('autoBtn');
  if (auto) {
    clearInterval(auto); auto = null; btn.textContent = 'Start auto traffic';
  } else {
    auto = setInterval(sendOne, 700); btn.textContent = 'Stop auto traffic';
  }
}

refresh();
setInterval(refresh, 2000);
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("DASHBOARD running on http://localhost:8080")
    app.run(port=8080, debug=False)
