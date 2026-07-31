"""
reset-service — REST JSON API
==============================
Isolates the destructive FLUSHALL operation behind a dedicated service.
Intended for classroom use — wipes all Redis data in one call.

Endpoints:
  POST /reset     Execute FLUSHALL on Redis
  GET  /health    Health check

Redis operations:
  FLUSHALL — deletes every key in every Redis database
"""

import os
import redis
from flask import Flask, jsonify

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))


# ---------------------------------------------------------------------------
# Redis Connection
# ---------------------------------------------------------------------------
def get_redis_client():
    """
    Create and return a Redis client.
    Returns the client if successful, or None if the connection fails.
    """
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
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "reset-service"}), 200


@app.route("/reset", methods=["POST"])
def reset():
    """
    Wipe all data from Redis using FLUSHALL.

    Response (200):
        { "success": true, "message": "All data has been cleared from Redis." }

    Response (503):
        { "success": false, "error": "Cannot reset: Redis is not available." }

    Redis operations:
        FLUSHALL — removes ALL keys from ALL Redis databases
    """
    r = get_redis_client()

    if not r:
        return jsonify({
            "success": False,
            "error": "Cannot reset: Redis is not available."
        }), 503

    r.flushall()

    return jsonify({
        "success": True,
        "message": "All data has been cleared from Redis."
    }), 200


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5003))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
