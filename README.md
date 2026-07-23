# Mini CDN

I wanted to understand how CDNs actually work, so I built a small one.

It's three edge servers and one origin server, all running as separate Flask processes that talk to each other over HTTP. Requests get routed to whichever edge is geographically closest, and each edge caches what it fetches so it doesn't have to keep asking the origin for the same thing.

There's a dashboard at localhost:8080 where you can watch the caches fill up and the hit ratio climb.

## Running it

You need Python 3.8 or newer.

```
pip install -r requirements.txt
python start_all.py
```

Open http://localhost:8080, hit "Send 10 requests" a few times, and watch what happens. Ctrl+C in the terminal stops everything.

If you want to see it as actually separate processes, run each one in its own terminal:

```
python origin_server.py
python edge_server.py --name Mumbai  --port 9101
python edge_server.py --name London  --port 9102
python edge_server.py --name NewYork --port 9103
python run_demo.py
```

You can also poke at the servers directly:

```
curl http://localhost:9101/get/logo.png
curl http://localhost:9101/stats
curl http://localhost:9000/stats
```

Run that first one twice. First time takes about 300ms because it has to go fetch from the origin. Second time is instant. That gap is basically the entire reason CDNs exist.

## How it works

A user request comes in with a lat/long. The router calculates Haversine distance to each edge and picks the nearest one. Real CDNs do this with DNS and anycast, but the underlying idea is the same — send people to the server closest to them.

That edge checks its cache. If the content is there, it returns it immediately (hit). If not, it makes an HTTP call to the origin, waits, stores a copy, and then returns it (miss). The origin has a deliberate 300ms sleep in it so the difference is obvious.

The thing that took me a while to get straight: the cache belongs to the **edge**, not the user. So if someone in Bangalore requests a file and it gets cached in Mumbai, the next person in Delhi also gets a hit — they never requested it before, but their nearest edge already has it. But someone in Paris hits London, which has its own separate cache, so it's still a miss there until London fetches it too.

Cache size is set to 3 items per edge, which is unrealistically small on purpose — it makes LRU eviction actually visible in the logs instead of never happening.

## Files

- `origin_server.py` — the origin, holds everything, slow
- `edge_server.py` — one edge cache node, run several on different ports
- `run_demo.py` — the router, plus fake users sending traffic
- `dashboard.py` — the web UI
- `start_all.py` — starts all of the above at once

## Stuff I'd still like to add

Cache expiry is the obvious gap. Right now content sits in the cache forever, which is fine for a demo but wrong — real caches use TTLs, and there needs to be some way for the origin to say "this file changed, drop your copy."

The traffic pattern is also unrealistic. Requests are uniformly random across five files, but real traffic is nothing like that — a handful of files get most of the requests. Using a Zipf distribution would push the hit ratio up to something closer to what actual CDNs see.

Also, if an edge goes down right now the request just fails. Health checks and falling back to the next-nearest edge would fix that.

Eventually I want to dockerize it and get it running somewhere real instead of localhost.

## Built with

Python, Flask, and a lot of curl.