"""
student-service — REST JSON API
================================
Owns all student registration and listing logic.

Endpoints:
  POST /students        Register a new student
  GET  /students        List all registered students
  GET  /health          Health check

Redis keys owned:
  students:names        List  — LPUSH / LRANGE
  stats:last_student    String — SET
  stats:student_count   String — INCR
"""

import os
import redis
from flask import Flask, request, jsonify

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
    return jsonify({"status": "ok", "service": "student-service"}), 200


@app.route("/students", methods=["POST"])
def register_student():
    """
    Register a new student.

    Request body (JSON):
        { "name": "Ada Lovelace" }

    Response (200):
        { "success": true, "message": "'Ada Lovelace' has been registered successfully!" }

    Response (400/503):
        { "success": false, "error": "..." }

    Redis operations:
        LPUSH students:names <name>
        SET   stats:last_student <name>
        INCR  stats:student_count
    """
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"success": False, "error": "Please enter a name."}), 400

    r = get_redis_client()
    if not r:
        return jsonify({"success": False, "error": "Cannot register: Redis is not available."}), 503

    r.lpush("students:names", name)
    r.set("stats:last_student", name)
    r.incr("stats:student_count")

    return jsonify({
        "success": True,
        "message": f"'{name}' has been registered successfully!"
    }), 200


@app.route("/students", methods=["GET"])
def list_students():
    """
    Return all registered students.

    Response (200):
        { "students": ["Ada Lovelace", ...], "redis_connected": true }

    Redis operations:
        LRANGE students:names 0 -1
    """
    r = get_redis_client()

    if not r:
        return jsonify({"students": [], "redis_connected": False}), 200

    student_list = r.lrange("students:names", 0, -1)
    return jsonify({"students": student_list, "redis_connected": True}), 200


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
