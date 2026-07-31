"""
student-service
===============
Responsible for student registration and listing.

Endpoints:
  POST /students  — register a new student
  GET  /students  — retrieve all registered students
  GET  /health    — liveness + Redis connectivity check

Redis keys owned:
  students:names      (LPUSH / LRANGE)
  stats:last_student  (SET)
  stats:student_count (INCR)
"""

import os
import redis
from flask import Flask, jsonify, request

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

@app.route("/students", methods=["POST"])
def register_student():
    """
    Register a new student.
    Expects JSON: { "name": "..." }
    - LPUSH students:names <name>
    - SET   stats:last_student <name>
    - INCR  stats:student_count
    Returns 201 on success, 400 on bad input, 503 if Redis is down.
    """
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Name is required and cannot be empty."}), 400

    r = get_redis_client()
    if not r:
        return jsonify({"error": "Redis unavailable"}), 503

    r.lpush("students:names", name)
    r.set("stats:last_student", name)
    r.incr("stats:student_count")

    return jsonify({"message": f"'{name}' registered successfully."}), 201


@app.route("/students", methods=["GET"])
def list_students():
    """
    Return all registered students.
    - LRANGE students:names 0 -1
    Returns { "students": [...] }
    """
    r = get_redis_client()
    if not r:
        return jsonify({"error": "Redis unavailable", "students": []}), 503

    students = r.lrange("students:names", 0, -1)
    return jsonify({"students": students}), 200


@app.route("/health")
def health():
    """Liveness check — also reports Redis connectivity."""
    r = get_redis_client()
    return jsonify({
        "status": "ok",
        "service": "student-service",
        "redis": "connected" if r else "disconnected",
    })


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
