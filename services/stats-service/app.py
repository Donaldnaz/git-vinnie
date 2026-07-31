"""
stats-service — REST JSON API
==============================
Owns visitor tracking and statistics aggregation.

Endpoints:
  POST /stats/visit     Record a page visit (INCR + SET)
  GET  /stats           Return all aggregated statistics
  GET  /health          Health check

Redis keys owned (write):
  stats:visitor_count   String — INCR
  stats:last_visit      String — SET

Redis keys read (written by student-service):
  stats:student_count   String — GET
  stats:last_student    String — GET
"""

import os
import datetime
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
# Helpers
# ---------------------------------------------------------------------------
def get_current_time():
    """Return the current UTC time as a readable string."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "stats-service"}), 200


@app.route("/stats/visit", methods=["POST"])
def record_visit():
    """
    Record a page visit: increment visitor counter and store timestamp.

    Response (200):
        { "visitor_count": 42, "last_visit": "2024-01-01 12:00:00 UTC", "redis_connected": true }

    Response (503):
        { "visitor_count": 0, "last_visit": "N/A", "redis_connected": false }

    Redis operations:
        INCR stats:visitor_count
        SET  stats:last_visit <timestamp>
    """
    r = get_redis_client()

    if not r:
        return jsonify({
            "visitor_count": 0,
            "last_visit": "N/A",
            "redis_connected": False
        }), 503

    visitor_count = r.incr("stats:visitor_count")
    current_time = get_current_time()
    r.set("stats:last_visit", current_time)

    return jsonify({
        "visitor_count": visitor_count,
        "last_visit": current_time,
        "redis_connected": True
    }), 200


@app.route("/stats", methods=["GET"])
def get_stats():
    """
    Return all aggregated statistics.

    Response (200):
        {
            "visitor_count": "42",
            "student_count": "7",
            "last_student": "Ada Lovelace",
            "last_visit": "2024-01-01 12:00:00 UTC",
            "redis_connected": true
        }

    Redis operations:
        GET stats:visitor_count
        GET stats:student_count
        GET stats:last_student
        GET stats:last_visit
    """
    r = get_redis_client()

    if not r:
        return jsonify({
            "visitor_count": "N/A",
            "student_count": "N/A",
            "last_student": "None yet",
            "last_visit": "N/A",
            "redis_connected": False
        }), 200

    return jsonify({
        "visitor_count": r.get("stats:visitor_count") or "0",
        "student_count": r.get("stats:student_count") or "0",
        "last_student": r.get("stats:last_student") or "None yet",
        "last_visit": r.get("stats:last_visit") or "N/A",
        "redis_connected": True
    }), 200


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5002))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
