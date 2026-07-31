"""
visitor-service
===============
Responsible for tracking page visits.

Endpoints:
  POST /visit   — increment visitor counter, record timestamp
  GET  /health  — liveness + Redis connectivity check

Redis keys owned:
  stats:visitor_count  (INCR)
  stats:last_visit     (SET)
"""

import os
import datetime
import redis
from flask import Flask, jsonify

app = Flask(__name__)

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))


def get_redis_client():
    """Return a connected Redis client, or None on failure."""
    try:
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        client.ping()
        return client
    except redis.exceptions.ConnectionError:
        return None


def get_current_time():
    """Return current UTC time as a readable string."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/visit", methods=["POST"])
def visit():
    """
    Record a visit.
    - INCR stats:visitor_count
    - SET  stats:last_visit <timestamp>
    Returns the updated counter and timestamp.
    """
    r = get_redis_client()

    if not r:
        return jsonify({"error": "Redis unavailable"}), 503

    current_time = get_current_time()
    visitor_count = r.incr("stats:visitor_count")
    r.set("stats:last_visit", current_time)

    return jsonify({
        "visitor_count": visitor_count,
        "last_visit": current_time,
    }), 200


@app.route("/health")
def health():
    """Liveness check — also reports Redis connectivity."""
    r = get_redis_client()
    return jsonify({
        "status": "ok",
        "service": "visitor-service",
        "redis": "connected" if r else "disconnected",
    })


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
