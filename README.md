# Mini CDN — A Working Content Delivery Network

A small but **real** Content Delivery Network built with Python and Flask.
Unlike a single-file simulation, this runs **actual separate server processes
that communicate over HTTP** — a genuine distributed system.

## What it demonstrates

- **Geographic routing** — each user request is sent to the *nearest* edge
  server, chosen with the Haversine distance formula (the same idea real CDNs
  implement via DNS/anycast).
- **Caching** — edge servers keep local copies of content. A request the edge
  already has is a **cache HIT** (instant). One it doesn't is a **cache MISS**,
  which fetches from the origin over HTTP and stores a copy.
- **LRU eviction** — each edge cache is small, so when it fills up, the
  Least-Recently-Used item is dropped. You can watch this happen in the logs.
- **Measurable benefit** — the demo reports cache hit ratio, per-edge stats,
  average latency, and how much load the origin was spared.

## Architecture

```
                         ┌────────────────────┐
                         │   ORIGIN SERVER     │   source of truth
                         │   localhost:9000    │   (slow: 300ms)
                         └─────────┬──────────┘
                    fetch on MISS  │  (HTTP)
          ┌──────────────┬─────────┴──────────┬──────────────┐
          │              │                    │              │
   ┌──────┴─────┐  ┌─────┴──────┐      ┌──────┴─────┐
   │ EDGE Mumbai│  │ EDGE London│      │EDGE NewYork│   each has its
   │  :9101     │  │  :9102     │      │  :9103     │   own LRU cache
   └──────┬─────┘  └─────┬──────┘      └──────┬─────┘
          │              │                    │
     nearest-edge routing (Haversine distance) over HTTP
          │              │                    │
     ┌────┴───┐     ┌────┴────┐          ┌────┴────┐
     │ Users  │     │ Users   │          │ Users   │
     │ (India)│     │(Europe) │          │  (US)   │
     └────────┘     └─────────┘          └─────────┘
```

## Files

| File | Role |
|------|------|
| `origin_server.py` | The origin — holds all content, slow to reach |
| `edge_server.py`   | An edge cache node (run several on different ports) |
| `run_demo.py`      | Router + simulated users; routes to nearest edge (terminal demo) |
| `dashboard.py`     | Live web dashboard — watch caches fill and hit ratios climb |
| `start_all.py`     | Starts everything with one command |

## How to run

Install dependencies:

```bash
pip install -r requirements.txt
```

### Easy way — the live dashboard (recommended)

```bash
python start_all.py
```

Then open **http://localhost:8080** in your browser. Click **"Send 10 requests"**
or **"Start auto traffic"** and watch, in real time:
- each edge's cache filling with content chips
- hit ratios climbing as content gets cached
- the origin's hit counter staying low (the CDN doing its job)
- a live request log showing HIT/MISS and evictions

Press `Ctrl+C` in the terminal to stop everything.

### Manual way (see it as a real distributed system)

Open **five terminals**:

```bash
# Terminal 1 — origin
python origin_server.py

# Terminal 2, 3, 4 — edge servers
python edge_server.py --name Mumbai  --port 9101
python edge_server.py --name London  --port 9102
python edge_server.py --name NewYork --port 9103

# Terminal 5 — run the users/demo
python run_demo.py
```

You can also hit servers directly in a browser or with curl:

```bash
curl http://localhost:9101/get/logo.png   # request content from the Mumbai edge
curl http://localhost:9101/stats          # see that edge's cache + hit ratio
curl http://localhost:9000/stats          # see how loaded the origin is
```

## What the results mean

- **HIT at ~0 ms vs MISS at ~300 ms** — proves caching's value: a hit never
  touches the origin.
- **Hit ratio** — the fraction of requests served locally. Higher is better.
- **Origin load** — how many requests the origin was spared. The whole point
  of a CDN is to keep this number low.

## How this maps to a real CDN

| This project | Real CDN (Cloudflare / Akamai / CloudFront) |
|--------------|---------------------------------------------|
| Nearest-edge via Haversine | DNS / anycast routing |
| Flask edge servers | Points of Presence (PoPs) worldwide |
| LRU cache | LRU + TTL + tiered caching |
| Manual origin fetch | Origin pull, with cache invalidation |

## Ideas to extend (great interview follow-ups)

- Add **TTL / cache expiry** so stale content refreshes.
- Add **cache invalidation** (origin pushes "content changed" to edges).
- Use **Zipf-distributed** request popularity for realistic hit ratios.
- Add a **web dashboard** showing live per-edge load and hit ratios.
- Add **health checks** so traffic reroutes if an edge goes down.
```
