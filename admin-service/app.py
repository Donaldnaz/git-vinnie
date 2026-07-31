"""
admin-service
=============
Standalone service for destructive reset operations.
Kept isolated so access controls can be applied independently
without touching any other service.

Endpoints:
  POST /reset  — flush all Redis data (FLUSHALL)
  GET  /health — liveness + Redis connectivity check

Redis operations:
  FLUSHALL — removes every key across all Redis databases
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

@app.route("/reset", methods=["POST"])
def reset():
    """
    Flush all data from Redis.
    Runs FLUSHALL — removes every key in every Redis database.
    Returns 200 on success, 503 if Redis is unavailable.
    """
    r = get_redis_client()

    if not r:
        return jsonify({"error": "Redis unavailable. Cannot reset."}), 503

    r.flushall()
    return jsonify({"message": "All data has been cleared from Redis."}), 200


@app.route("/health")
def health():
    """Liveness check — also reports Redis connectivity."""
    r = get_redis_client()
    return jsonify({
        "status": "ok",
        "service": "admin-service",
        "redis": "connected" if r else "disconnected",
    })


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
