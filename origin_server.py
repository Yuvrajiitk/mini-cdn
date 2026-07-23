"""
ORIGIN SERVER  (the single source of truth)
-------------------------------------------
This is a REAL web server. It holds every piece of content.
Edge servers call it over HTTP only when they don't have something cached.

In a real CDN this would be your main data center. It's the slow, expensive
server we try to avoid hitting too often.

Run it:   python origin_server.py
It listens on http://localhost:9000
"""

from flask import Flask, jsonify
import time

app = Flask(__name__)

# The "content library" — the real files the origin owns.
# In real life these would be videos/images/html; here each is some text.
CONTENT = {
    "home.html":   "<h1>Welcome to my site</h1>",
    "logo.png":    "[binary image data for logo]",
    "video1.mp4":  "[binary video data ~50MB]",
    "style.css":   "body { font-family: sans-serif; }",
    "app.js":      "console.log('hello from origin');",
}

# Count how many times edges had to bother the origin.
stats = {"requests_served": 0}


@app.route("/content/<path:content_id>")
def get_content(content_id):
    """An edge server calls this when it doesn't have the content cached."""
    if content_id not in CONTENT:
        return jsonify({"error": "not found"}), 404

    stats["requests_served"] += 1

    # Simulate the origin being SLOW (it's far away / under load).
    time.sleep(0.3)  # 300 ms — this is the pain a cache saves us from.

    return jsonify({
        "content_id": content_id,
        "data": CONTENT[content_id],
        "served_by": "ORIGIN",
    })


@app.route("/stats")
def get_stats():
    return jsonify(stats)


@app.route("/")
def home():
    return jsonify({
        "server": "ORIGIN",
        "content_available": list(CONTENT.keys()),
        "requests_served": stats["requests_served"],
    })


if __name__ == "__main__":
    print("ORIGIN SERVER running on http://localhost:9000")
    print("Holds content:", list(CONTENT.keys()))
    app.run(port=9000, debug=False)
