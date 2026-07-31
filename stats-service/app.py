"""
stats-service
=============
Read-only aggregation service. Reads all stats:* keys from Redis
and returns them as a single JSON payload.

Endpoints:
  GET /stats   — return aggregated statistics
  GET /health  — liveness + Redis connectivity check

Redis keys read (never written):
  stats:visitor_count
  stats:student_count
  stats:last_student
  stats:last_visit
"""

import os
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/stats", methods=["GET"])
def stats():
    """
    Return aggregated statistics from Redis.
    All four keys are read with GET; sensible defaults are provided
    when keys don't exist or Redis is unavailable — never returns 500.
    """
    r = get_redis_client()

    if not r:
        # Degrade gracefully: return defaults rather than an error
        return jsonify({
            "visitor_count": "0",
            "student_count": "0",
            "last_student": "None yet",
            "last_visit": "N/A",
            "redis_connected": False,
        }), 200

    return jsonify({
        "visitor_count": r.get("stats:visitor_count") or "0",
        "student_count": r.get("stats:student_count") or "0",
        "last_student":  r.get("stats:last_student")  or "None yet",
        "last_visit":    r.get("stats:last_visit")    or "N/A",
        "redis_connected": True,
    }), 200


@app.route("/health")
def health():
    """Liveness check — also reports Redis connectivity."""
    r = get_redis_client()
    return jsonify({
        "status": "ok",
        "service": "stats-service",
        "redis": "connected" if r else "disconnected",
    })


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
